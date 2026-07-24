import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  approveCapabilityExecution,
  cancelCapabilityExecution,
  listConversationExecutions,
  listPendingExecutions,
  submitCapabilityExecution,
} from "../api/capabilities";
import { ApiRequestError } from "../api/client";
import {
  createConversation,
  deleteConversation,
  listConversations,
  listMessages,
  renameConversation,
  streamMessage,
} from "../api/conversations";
import type {
  CapabilityExecution,
  Citation,
  ConversationMessage,
  ConversationSummary,
} from "../api/types";
import { useAppState } from "../state/AppStateContext";

interface UiMessage extends ConversationMessage {
  id: string;
  pending?: boolean;
  failed?: boolean;
  error?: string | null;
}

function messageId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

function CodeBlock({
  children,
  className,
}: {
  children?: ReactNode;
  className?: string;
}) {
  const code = String(children ?? "").replace(/\n$/, "");
  const language = className?.replace("language-", "") ?? "";

  return (
    <div className="code-block">
      <div className="code-block-header">
        <span>{language || "code"}</span>
        <button
          type="button"
          onClick={() => void navigator.clipboard.writeText(code)}
        >
          Copy
        </button>
      </div>
      <pre>
        <code className={className}>{code}</code>
      </pre>
    </div>
  );
}

function MarkdownBody({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ className, children, ...props }) {
          const isBlock = Boolean(className) || String(children).includes("\n");
          if (!isBlock) {
            return (
              <code className="inline-code" {...props}>
                {children}
              </code>
            );
          }
          return <CodeBlock className={className}>{children}</CodeBlock>;
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function Citations({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) {
    return null;
  }
  return (
    <ul className="citation-list">
      {citations.map((citation) => (
        <li key={`${citation.document_id}:${citation.chunk_id}`}>
          {citation.document_title ?? citation.document_id}
        </li>
      ))}
    </ul>
  );
}

function operationSummaryText(execution: CapabilityExecution): string | null {
  const summary = execution.metadata?.operation_summary;
  if (!summary || typeof summary !== "object") {
    return null;
  }
  const record = summary as Record<string, unknown>;
  const operation =
    typeof record.operation === "string" ? record.operation : null;
  const target = typeof record.target === "string" ? record.target : null;
  const destination =
    typeof record.destination === "string" ? record.destination : null;
  if (!operation && !target) {
    return null;
  }
  if (operation && target && destination) {
    return `${operation}: ${target} → ${destination}`;
  }
  if (operation && target) {
    return `${operation}: ${target}`;
  }
  return operation ?? target;
}

function undoMessage(execution: CapabilityExecution): string | null {
  const output = execution.output;
  if (!output || typeof output !== "object") {
    return null;
  }
  const metadata = (output as { metadata?: Record<string, unknown> }).metadata;
  if (!metadata || typeof metadata !== "object") {
    return null;
  }
  const message = metadata.undo_message;
  return typeof message === "string" && message.trim() ? message : null;
}

function executionLabel(execution: CapabilityExecution): string {
  const error =
    execution.error?.message ?? execution.error_message ?? null;
  switch (execution.status) {
    case "pending_approval":
      return "Awaiting confirmation";
    case "executing":
      return "In progress…";
    case "completed":
      return "Succeeded";
    case "failed":
      return error ? `Failed: ${error}` : "Failed";
    case "cancelled":
      return "Cancelled";
    default:
      return execution.status;
  }
}

function isOverwriteConfirmation(execution: CapabilityExecution): boolean {
  return (
    execution.status === "failed" &&
    execution.error?.code === "overwrite_confirmation_required"
  );
}

function CapabilityExecutionPanel({
  executions,
  onApprove,
  onCancel,
  onReplace,
  busyId,
}: {
  executions: CapabilityExecution[];
  onApprove: (executionId: string) => void;
  onCancel: (executionId: string) => void;
  onReplace: (execution: CapabilityExecution) => void;
  busyId: string | null;
}) {
  if (executions.length === 0) {
    return null;
  }

  return (
    <section className="capability-panel" aria-label="Capability executions">
      <h2>Capability executions</h2>
      <ul className="capability-execution-list">
        {executions.map((execution) => {
          const summary = operationSummaryText(execution);
          const undo = undoMessage(execution);
          const confirmOverwrite = isOverwriteConfirmation(execution);
          return (
            <li
              key={execution.execution_id}
              data-status={execution.status}
            >
              <div>
                <strong>{execution.capability_id}</strong>
                <span className="capability-status">
                  {executionLabel(execution)}
                </span>
                {execution.duration > 0 ? (
                  <span className="muted">
                    {(execution.duration * 1000).toFixed(0)} ms
                  </span>
                ) : null}
              </div>
              {summary ? (
                <p className="capability-operation-summary">{summary}</p>
              ) : null}
              {execution.status === "pending_approval" ? (
                <div className="capability-confirm">
                  <p className="capability-confirm-copy">
                    Confirm this capability action? It will run only after you
                    approve.
                  </p>
                  <div className="capability-actions">
                    <button
                      type="button"
                      className="primary-button"
                      disabled={busyId === execution.execution_id}
                      onClick={() => onApprove(execution.execution_id)}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="danger-button"
                      disabled={busyId === execution.execution_id}
                      onClick={() => onCancel(execution.execution_id)}
                    >
                      Deny
                    </button>
                  </div>
                </div>
              ) : null}
              {execution.status === "executing" ? (
                <p className="capability-progress" role="status">
                  Running…
                </p>
              ) : null}
              {confirmOverwrite ? (
                <div className="capability-confirm">
                  <p className="capability-confirm-copy">
                    A file already exists at the destination. Replace it?
                  </p>
                  <div className="capability-actions">
                    <button
                      type="button"
                      className="primary-button"
                      disabled={busyId === execution.execution_id}
                      onClick={() => onReplace(execution)}
                    >
                      Replace
                    </button>
                    <button
                      type="button"
                      className="danger-button"
                      disabled={busyId === execution.execution_id}
                      onClick={() => onCancel(execution.execution_id)}
                    >
                      Keep existing
                    </button>
                  </div>
                </div>
              ) : null}
              {execution.status === "completed" ? (
                <div className="capability-result capability-result-success">
                  {undo ? <p className="capability-undo">{undo}</p> : null}
                  {execution.output != null ? (
                    <pre className="capability-output">
                      {typeof execution.output === "string"
                        ? execution.output
                        : JSON.stringify(execution.output, null, 2)}
                    </pre>
                  ) : null}
                </div>
              ) : null}
              {execution.status === "failed" && !confirmOverwrite ? (
                <p className="capability-result capability-result-failure">
                  {execution.error?.message ??
                    execution.error_message ??
                    "Capability execution failed."}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function ChatPage() {
  const { activeWorkspace, activeModel, connection } = useAppState();
  const workspaceId = activeWorkspace?.id ?? null;

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(
    null,
  );
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [executions, setExecutions] = useState<CapabilityExecution[]>([]);
  const [executionBusyId, setExecutionBusyId] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const lastFailedUserMessage = useRef<string | null>(null);

  const canUseBackend =
    connection.status === "connected" || connection.status === "degraded";

  const activeConversation = useMemo(
    () =>
      conversations.find(
        (conversation) => conversation.conversation_id === activeConversationId,
      ) ?? null,
    [conversations, activeConversationId],
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  useEffect(() => {
    if (!workspaceId || !canUseBackend) {
      setExecutions([]);
      return;
    }

    let cancelled = false;

    async function refreshExecutions() {
      try {
        const [pending, conversationScoped] = await Promise.all([
          listPendingExecutions(workspaceId!),
          activeConversationId
            ? listConversationExecutions(workspaceId!, activeConversationId)
            : Promise.resolve({ items: [] as CapabilityExecution[] }),
        ]);
        if (cancelled) return;
        const byId = new Map<string, CapabilityExecution>();
        for (const item of [...pending.items, ...conversationScoped.items]) {
          byId.set(item.execution_id, item);
        }
        setExecutions(
          Array.from(byId.values()).sort((a, b) =>
            a.updated_at.localeCompare(b.updated_at),
          ),
        );
      } catch {
        // Keep chat usable if the capability surface is unavailable.
      }
    }

    void refreshExecutions();
    const timer = window.setInterval(() => {
      void refreshExecutions();
    }, 2500);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [workspaceId, canUseBackend, activeConversationId]);

  useEffect(() => {
    if (!workspaceId || !canUseBackend) {
      setConversations([]);
      setActiveConversationId(null);
      setMessages([]);
      return;
    }

    let cancelled = false;
    setIsLoadingList(true);
    setError(null);

    void listConversations(workspaceId)
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setConversations(payload.conversations);
        setActiveConversationId((current) => {
          if (
            current &&
            payload.conversations.some(
              (item) => item.conversation_id === current,
            )
          ) {
            return current;
          }
          return payload.conversations[0]?.conversation_id ?? null;
        });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Failed to load conversations.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingList(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [workspaceId, canUseBackend]);

  useEffect(() => {
    if (!workspaceId || !activeConversationId || !canUseBackend) {
      setMessages([]);
      return;
    }

    let cancelled = false;
    setIsLoadingMessages(true);
    setError(null);

    void listMessages(workspaceId, activeConversationId)
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setMessages(
          payload.messages.map((message) => ({
            ...message,
            id: messageId(message.role),
          })),
        );
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Failed to load messages.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingMessages(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [workspaceId, activeConversationId, canUseBackend]);

  async function handleNewConversation() {
    if (!workspaceId || !canUseBackend || isStreaming) {
      return;
    }
    try {
      const created = await createConversation(workspaceId);
      setConversations((current) => [
        {
          conversation_id: created.conversation_id,
          title: created.title,
          created_at: created.created_at,
          updated_at: created.created_at,
          message_count: 0,
        },
        ...current,
      ]);
      setActiveConversationId(created.conversation_id);
      setMessages([]);
      setError(null);
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to create conversation.",
      );
    }
  }

  async function handleDelete(conversationId: string) {
    if (!workspaceId || isStreaming) {
      return;
    }
    try {
      await deleteConversation(workspaceId, conversationId);
      setConversations((current) =>
        current.filter((item) => item.conversation_id !== conversationId),
      );
      if (activeConversationId === conversationId) {
        setActiveConversationId(null);
        setMessages([]);
      }
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to delete conversation.",
      );
    }
  }

  async function handleRenameSubmit(conversationId: string) {
    if (!workspaceId || !renameDraft.trim()) {
      setRenamingId(null);
      return;
    }
    try {
      const updated = await renameConversation(
        workspaceId,
        conversationId,
        renameDraft.trim(),
      );
      setConversations((current) =>
        current.map((item) =>
          item.conversation_id === conversationId
            ? { ...item, title: updated.title, updated_at: updated.updated_at }
            : item,
        ),
      );
      setRenamingId(null);
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to rename conversation.",
      );
    }
  }

  function stopGeneration() {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setMessages((current) =>
      current.map((message) =>
        message.pending
          ? {
              ...message,
              pending: false,
              content: message.content || "(generation stopped)",
            }
          : message,
      ),
    );
  }

  async function sendUserMessage(
    rawMessage: string,
    options?: { retry?: boolean },
  ) {
    if (!workspaceId || !canUseBackend || isStreaming) {
      return;
    }
    const retry = options?.retry ?? false;
    const message = rawMessage.trim();
    if (!message) {
      return;
    }

    let conversationId = activeConversationId;
    if (!conversationId) {
      const created = await createConversation(workspaceId);
      conversationId = created.conversation_id;
      setConversations((current) => [
        {
          conversation_id: created.conversation_id,
          title: created.title,
          created_at: created.created_at,
          updated_at: created.created_at,
          message_count: 0,
        },
        ...current,
      ]);
      setActiveConversationId(created.conversation_id);
    }

    if (!retry) {
      setDraft("");
    }
    lastFailedUserMessage.current = message;
    setError(null);

    const userMessage: UiMessage = {
      id: messageId("user"),
      role: "user",
      content: message,
      timestamp: new Date().toISOString(),
      citations: [],
    };
    const assistantId = messageId("assistant");
    const assistantMessage: UiMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
      citations: [],
      pending: true,
    };

    setMessages((current) =>
      retry
        ? [...current.filter((item) => !item.failed), assistantMessage]
        : [...current, userMessage, assistantMessage],
    );
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;
    let assembled = "";

    try {
      await streamMessage({
        workspaceId,
        conversationId,
        message,
        provider: activeModel?.provider,
        model: activeModel?.model,
        signal: controller.signal,
        onToken: (content) => {
          assembled += content;
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantId
                ? { ...item, content: assembled, pending: true }
                : item,
            ),
          );
        },
        onDone: (result) => {
          lastFailedUserMessage.current = null;
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantId
                ? {
                    ...item,
                    content: result.assistant_message,
                    citations: result.citations,
                    pending: false,
                    failed: false,
                    error: null,
                  }
                : item,
            ),
          );
          setConversations((current) =>
            current.map((item) =>
              item.conversation_id === conversationId
                ? {
                    ...item,
                    title: result.title ?? item.title,
                    updated_at: new Date().toISOString(),
                    message_count: item.message_count + 2,
                  }
                : item,
            ),
          );
        },
        onError: (streamError) => {
          lastFailedUserMessage.current = message;
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantId
                ? {
                    ...item,
                    pending: false,
                    failed: true,
                    error: streamError.message,
                    content: item.content || streamError.message,
                  }
                : item,
            ),
          );
          setError(streamError.message);
        },
      });
    } catch (err) {
      if (!controller.signal.aborted) {
        const messageText =
          err instanceof ApiRequestError
            ? err.message
            : "Failed to send message.";
        lastFailedUserMessage.current = message;
        setError(messageText);
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantId
              ? {
                  ...item,
                  pending: false,
                  failed: true,
                  error: messageText,
                  content: item.content || messageText,
                }
              : item,
          ),
        );
      }
    } finally {
      abortRef.current = null;
      setIsStreaming(false);
    }
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendUserMessage(draft);
    }
  }

  async function handleApproveExecution(executionId: string) {
    if (!workspaceId) return;
    setExecutionBusyId(executionId);
    try {
      const result = await approveCapabilityExecution(workspaceId, executionId);
      setExecutions((current) =>
        current.map((item) =>
          item.execution_id === executionId ? result : item,
        ),
      );
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to approve capability execution.",
      );
    } finally {
      setExecutionBusyId(null);
    }
  }

  async function handleReplaceExecution(execution: CapabilityExecution) {
    if (!workspaceId) return;
    const retry = execution.metadata?.retry_arguments;
    if (!retry || typeof retry !== "object") {
      setError("Cannot replace: original capability arguments are unavailable.");
      return;
    }
    setExecutionBusyId(execution.execution_id);
    try {
      const result = await submitCapabilityExecution(workspaceId, {
        capability_id: execution.capability_id,
        conversation_id: execution.conversation_id,
        permission_mode: execution.permission_mode,
        arguments: {
          ...(retry as Record<string, unknown>),
          overwrite_policy: "replace",
        },
      });
      setExecutions((current) => [
        ...current.filter((item) => item.execution_id !== execution.execution_id),
        result,
      ]);
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to replace existing file.",
      );
    } finally {
      setExecutionBusyId(null);
    }
  }

  async function handleCancelExecution(executionId: string) {
    if (!workspaceId) return;
    setExecutionBusyId(executionId);
    try {
      const result = await cancelCapabilityExecution(workspaceId, executionId);
      setExecutions((current) =>
        current.map((item) =>
          item.execution_id === executionId ? result : item,
        ),
      );
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to cancel capability execution.",
      );
    } finally {
      setExecutionBusyId(null);
    }
  }

  return (
    <div className="chat-layout">
      <aside className="chat-sidebar" aria-label="Conversations">
        <div className="chat-sidebar-header">
          <h2>Conversations</h2>
          <button
            type="button"
            className="primary-button"
            onClick={() => void handleNewConversation()}
            disabled={!canUseBackend || isStreaming}
          >
            New Conversation
          </button>
        </div>

        {isLoadingList ? (
          <p className="muted">Loading conversations…</p>
        ) : conversations.length === 0 ? (
          <p className="muted">No conversations yet.</p>
        ) : (
          <ul className="conversation-list">
            {conversations.map((conversation) => (
              <li
                key={conversation.conversation_id}
                data-active={
                  conversation.conversation_id === activeConversationId
                }
              >
                {renamingId === conversation.conversation_id ? (
                  <form
                    className="rename-form"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void handleRenameSubmit(conversation.conversation_id);
                    }}
                  >
                    <input
                      value={renameDraft}
                      onChange={(event) => setRenameDraft(event.target.value)}
                      autoFocus
                    />
                    <button type="submit">Save</button>
                    <button
                      type="button"
                      onClick={() => setRenamingId(null)}
                    >
                      Cancel
                    </button>
                  </form>
                ) : (
                  <>
                    <button
                      type="button"
                      className="conversation-item"
                      onClick={() =>
                        setActiveConversationId(conversation.conversation_id)
                      }
                    >
                      <span className="conversation-title">
                        {conversation.title}
                      </span>
                      <span className="conversation-meta">
                        {conversation.message_count} messages
                      </span>
                    </button>
                    <div className="conversation-actions">
                      <button
                        type="button"
                        onClick={() => {
                          setRenamingId(conversation.conversation_id);
                          setRenameDraft(conversation.title);
                        }}
                        disabled={isStreaming}
                      >
                        Rename
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          void handleDelete(conversation.conversation_id)
                        }
                        disabled={isStreaming}
                      >
                        Delete
                      </button>
                    </div>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </aside>

      <section className="chat-main">
        <div className="chat-main-header">
          <h1>{activeConversation?.title ?? "Conversation"}</h1>
          {error ? (
            <p className="chat-error" role="alert">
              {error}
            </p>
          ) : null}
        </div>

        <div className="message-list" aria-live="polite">
          {!activeConversationId ? (
            <p className="muted">
              Create a conversation to start chatting with Memovi.
            </p>
          ) : isLoadingMessages ? (
            <p className="muted">Loading messages…</p>
          ) : messages.length === 0 ? (
            <p className="muted">No messages yet. Ask a question below.</p>
          ) : (
            messages.map((message) => (
              <article
                key={message.id}
                className="message"
                data-role={message.role}
                data-pending={message.pending ? "true" : "false"}
                data-failed={message.failed ? "true" : "false"}
              >
                <header>
                  <strong>
                    {message.role === "user" ? "You" : "Memovi"}
                  </strong>
                  <div className="message-actions">
                    <button
                      type="button"
                      onClick={() =>
                        void navigator.clipboard.writeText(message.content)
                      }
                    >
                      Copy
                    </button>
                    {message.failed && lastFailedUserMessage.current ? (
                      <button
                        type="button"
                        onClick={() =>
                          void sendUserMessage(
                            lastFailedUserMessage.current ?? "",
                            { retry: true },
                          )
                        }
                      >
                        Retry
                      </button>
                    ) : null}
                  </div>
                </header>
                <div className="message-body">
                  {message.role === "assistant" ? (
                    <MarkdownBody content={message.content || "…"} />
                  ) : (
                    <p>{message.content}</p>
                  )}
                </div>
                <Citations citations={message.citations} />
              </article>
            ))
          )}
          <div ref={bottomRef} />
        </div>

        <CapabilityExecutionPanel
          executions={executions}
          busyId={executionBusyId}
          onApprove={(executionId) => void handleApproveExecution(executionId)}
          onCancel={(executionId) => void handleCancelExecution(executionId)}
          onReplace={(execution) => void handleReplaceExecution(execution)}
        />

        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            void sendUserMessage(draft);
          }}
        >
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onComposerKeyDown}
            placeholder="Ask Memovi… (Enter to send, Shift+Enter for newline)"
            rows={3}
            disabled={!canUseBackend || isStreaming}
          />
          <div className="composer-actions">
            {isStreaming ? (
              <button
                type="button"
                className="danger-button"
                onClick={stopGeneration}
              >
                Stop
              </button>
            ) : (
              <button
                type="submit"
                className="primary-button"
                disabled={!canUseBackend || !draft.trim()}
              >
                Send
              </button>
            )}
          </div>
        </form>
      </section>
    </div>
  );
}
