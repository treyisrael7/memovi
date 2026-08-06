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
import { Button } from "./ui/Button";
import { ConfirmDialog } from "./ui/ConfirmDialog";
import { EmptyState } from "./ui/EmptyState";
import { LoadingState } from "./ui/LoadingState";

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
  const command = typeof record.command === "string" ? record.command : null;
  const workingDirectory =
    typeof record.working_directory === "string"
      ? record.working_directory
      : null;
  if (command) {
    return workingDirectory
      ? `$ ${command}  (${workingDirectory})`
      : `$ ${command}`;
  }
  const operation =
    typeof record.operation === "string" ? record.operation : null;
  const repository =
    typeof record.repository === "string" ? record.repository : null;
  const branch = typeof record.branch === "string" ? record.branch : null;
  if (execution.capability_id === "git" && operation) {
    const repoLabel = repository ? repository.split(/[/\\]/).pop() : null;
    if (branch && repoLabel) {
      return `${operation}: ${repoLabel} @ ${branch}`;
    }
    if (repoLabel) {
      return `${operation}: ${repoLabel}`;
    }
    return operation;
  }
  if (execution.capability_id === "browser" && operation) {
    const url = typeof record.url === "string" ? record.url : null;
    const query = typeof record.query === "string" ? record.query : null;
    const destination =
      typeof record.destination === "string" ? record.destination : null;
    if (operation === "search_web" && query) {
      return `${operation}: “${query}”`;
    }
    if (operation === "download_file" && url && destination) {
      return `${operation}: ${url} → ${destination}`;
    }
    if (url) {
      return `${operation}: ${url}`;
    }
    return operation;
  }
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

function isTerminalExecution(execution: CapabilityExecution): boolean {
  return execution.capability_id === "terminal";
}

function isGitExecution(execution: CapabilityExecution): boolean {
  return execution.capability_id === "git";
}

function isBrowserExecution(execution: CapabilityExecution): boolean {
  return execution.capability_id === "browser";
}

function gitApprovalCopy(execution: CapabilityExecution): string {
  const summary = execution.metadata?.operation_summary;
  const operation =
    summary &&
    typeof summary === "object" &&
    typeof (summary as { operation?: unknown }).operation === "string"
      ? (summary as { operation: string }).operation
      : null;
  if (
    operation === "commit" ||
    operation === "checkout_branch" ||
    operation === "create_branch" ||
    operation === "stage_files" ||
    operation === "unstage_files"
  ) {
    return "Apply this Git repository change? It will run only after you approve.";
  }
  if (operation === "push" || operation === "pull" || operation === "fetch") {
    return "Allow this Git network operation? It will run only after you approve.";
  }
  return "Run this Git operation? It will execute only after you approve.";
}

function browserApprovalCopy(execution: CapabilityExecution): string {
  const summary = execution.metadata?.operation_summary;
  const operation =
    summary &&
    typeof summary === "object" &&
    typeof (summary as { operation?: unknown }).operation === "string"
      ? (summary as { operation: string }).operation
      : null;
  if (operation === "download_file") {
    return "Download this file to your workspace? It will run only after you approve.";
  }
  if (operation === "search_web") {
    return "Allow this web search? It will run only after you approve.";
  }
  return "Allow this browser action? It will run only after you approve.";
}

type BrowserOutput = {
  operation?: string;
  url?: string;
  final_url?: string;
  title?: string;
  content?: string;
  query?: string;
  results?: Array<{ title?: string; url?: string; snippet?: string }>;
  result_count?: number;
  destination?: string;
  bytes_written?: number;
  sha256?: string;
  progress?: number;
  bytes_received?: number;
  bytes_total?: number | null;
  streaming?: boolean;
  phase?: string;
  success?: boolean;
  redirected?: boolean;
};

function asBrowserOutput(output: unknown): BrowserOutput | null {
  if (!output || typeof output !== "object") {
    return null;
  }
  return output as BrowserOutput;
}

function BrowserResultView({
  output,
  live,
}: {
  output: BrowserOutput;
  live?: boolean;
}) {
  const operation = output.operation ?? "browser";
  const progress =
    typeof output.progress === "number"
      ? Math.max(0, Math.min(1, output.progress))
      : null;

  if (live) {
    return (
      <div className="capability-browser-result">
        <p className="capability-progress" role="status">
          {operation === "download_file" || output.phase === "download"
            ? "Downloading…"
            : "Navigating…"}
          {progress != null && progress > 0
            ? ` ${(progress * 100).toFixed(0)}%`
            : ""}
        </p>
        {typeof output.bytes_received === "number" ? (
          <p className="capability-browser-meta">
            {output.bytes_received.toLocaleString()} bytes
            {typeof output.bytes_total === "number"
              ? ` / ${output.bytes_total.toLocaleString()}`
              : ""}
          </p>
        ) : null}
      </div>
    );
  }

  if (operation === "search_web") {
    return (
      <div className="capability-browser-result">
        <p className="capability-browser-meta">
          {output.result_count ?? output.results?.length ?? 0} result
          {(output.result_count ?? output.results?.length ?? 0) === 1
            ? ""
            : "s"}
          {output.query ? ` for “${output.query}”` : ""}
        </p>
        <ul className="capability-browser-results">
          {(output.results ?? []).map((hit) => (
            <li key={`${hit.url ?? ""}-${hit.title ?? ""}`}>
              <strong>{hit.title ?? "Result"}</strong>
              {hit.url ? <div className="muted">{hit.url}</div> : null}
              {hit.snippet ? <div>{hit.snippet}</div> : null}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  if (operation === "download_file") {
    return (
      <div className="capability-browser-result">
        <p className="capability-browser-meta">
          Saved{" "}
          {typeof output.bytes_written === "number"
            ? `${output.bytes_written.toLocaleString()} bytes`
            : "file"}
          {output.destination ? ` → ${output.destination}` : ""}
        </p>
        {output.sha256 ? (
          <p className="capability-browser-meta">
            SHA-256 <code>{output.sha256.slice(0, 16)}…</code>
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="capability-browser-result">
      <p className="capability-browser-meta">
        {output.title ? output.title : operation}
        {output.redirected ? " · redirected" : ""}
      </p>
      {output.final_url || output.url ? (
        <p className="capability-browser-meta muted">
          {output.final_url ?? output.url}
        </p>
      ) : null}
      {typeof output.content === "string" && output.content.length > 0 ? (
        <pre className="capability-output capability-browser-content">
          {output.content.length > 1200
            ? `${output.content.slice(0, 1200)}…`
            : output.content}
        </pre>
      ) : null}
    </div>
  );
}

type GitOutput = {
  operation?: string;
  repository?: string;
  branch?: string | null;
  current?: string | null;
  clean?: boolean;
  staged?: string[];
  modified?: string[];
  untracked?: string[];
  ignored?: string[];
  local?: Array<{ name?: string; current?: boolean }>;
  remote?: Array<{ name?: string }>;
  commits?: Array<{
    short_sha?: string;
    subject?: string;
    author?: string;
    date?: string;
  }>;
  short_sha?: string;
  message?: string;
  patch?: string;
  summary?: string;
  success?: boolean;
};

function asGitOutput(output: unknown): GitOutput | null {
  if (!output || typeof output !== "object") {
    return null;
  }
  return output as GitOutput;
}

function GitResultView({ output }: { output: GitOutput }) {
  const operation = output.operation ?? "git";
  return (
    <div className="capability-git-result">
      {operation === "status" ? (
        <>
          <p className="capability-git-meta">
            {output.branch ? `Branch ${output.branch}` : "Detached HEAD"}
            {output.clean === true
              ? " · clean"
              : output.clean === false
                ? " · changes"
                : ""}
          </p>
          <GitFileGroup label="Staged" paths={output.staged} />
          <GitFileGroup label="Modified" paths={output.modified} />
          <GitFileGroup label="Untracked" paths={output.untracked} />
        </>
      ) : null}
      {operation === "list_branches" ? (
        <>
          <p className="capability-git-meta">
            Current: {output.current ?? "none"}
          </p>
          <ul className="capability-git-branches">
            {(output.local ?? []).map((branch) => (
              <li
                key={branch.name ?? "local"}
                data-current={branch.current ? "true" : "false"}
              >
                {branch.name}
                {branch.current ? " (current)" : ""}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {operation === "commit_history" ? (
        <ul className="capability-git-history">
          {(output.commits ?? []).map((commit) => (
            <li key={commit.short_sha ?? commit.subject}>
              <code>{commit.short_sha}</code> {commit.subject}
              {commit.author ? (
                <span className="muted"> — {commit.author}</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      {operation === "commit" ? (
        <p className="capability-git-meta">
          Committed {output.short_sha}
          {output.message ? `: ${output.message}` : ""}
        </p>
      ) : null}
      {operation === "diff" && typeof output.patch === "string" ? (
        <pre className="capability-output capability-git-diff">
          {output.patch}
        </pre>
      ) : null}
      {operation !== "status" &&
      operation !== "list_branches" &&
      operation !== "commit_history" &&
      operation !== "commit" &&
      operation !== "diff" ? (
        <pre className="capability-output">
          {JSON.stringify(output, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}

function GitFileGroup({ label, paths }: { label: string; paths?: string[] }) {
  if (!paths || paths.length === 0) {
    return null;
  }
  return (
    <div className="capability-git-files">
      <strong>{label}</strong>
      <ul>
        {paths.map((path) => (
          <li key={`${label}-${path}`}>{path}</li>
        ))}
      </ul>
    </div>
  );
}

function asTerminalOutput(output: unknown): {
  exit_code?: number;
  stdout?: string;
  stderr?: string;
  duration_seconds?: number;
  success?: boolean;
  streaming?: boolean;
} | null {
  if (!output || typeof output !== "object") {
    return null;
  }
  return output as {
    exit_code?: number;
    stdout?: string;
    stderr?: string;
    duration_seconds?: number;
    success?: boolean;
    streaming?: boolean;
  };
}

function TerminalOutputView({
  output,
  live,
}: {
  output: {
    exit_code?: number;
    stdout?: string;
    stderr?: string;
    duration_seconds?: number;
    success?: boolean;
    streaming?: boolean;
  };
  live?: boolean;
}) {
  const hasStdout =
    typeof output.stdout === "string" && output.stdout.length > 0;
  const hasStderr =
    typeof output.stderr === "string" && output.stderr.length > 0;
  return (
    <div className="capability-terminal-result">
      {!live && typeof output.exit_code === "number" ? (
        <p className="capability-terminal-meta">
          Exit {output.exit_code}
          {typeof output.duration_seconds === "number"
            ? ` · ${(output.duration_seconds * 1000).toFixed(0)} ms`
            : ""}
        </p>
      ) : null}
      {live ? (
        <p className="capability-progress" role="status">
          Streaming output…
        </p>
      ) : null}
      {hasStdout ? (
        <pre className="capability-output capability-terminal-stdout">
          {output.stdout}
        </pre>
      ) : null}
      {hasStderr ? (
        <pre className="capability-output capability-terminal-stderr">
          {output.stderr}
        </pre>
      ) : null}
      {!live && !hasStdout && !hasStderr ? (
        <p className="muted">No output captured.</p>
      ) : null}
    </div>
  );
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
  const error = execution.error?.message ?? execution.error_message ?? null;
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
          const terminalOutput = isTerminalExecution(execution)
            ? asTerminalOutput(execution.output)
            : null;
          const gitOutput = isGitExecution(execution)
            ? asGitOutput(execution.output)
            : null;
          const browserOutput = isBrowserExecution(execution)
            ? asBrowserOutput(execution.output)
            : null;
          const hasLiveTerminalOutput =
            terminalOutput != null &&
            ((typeof terminalOutput.stdout === "string" &&
              terminalOutput.stdout.length > 0) ||
              (typeof terminalOutput.stderr === "string" &&
                terminalOutput.stderr.length > 0));
          const hasLiveBrowserProgress =
            browserOutput != null &&
            (browserOutput.streaming === true ||
              typeof browserOutput.progress === "number" ||
              typeof browserOutput.bytes_received === "number");
          return (
            <li key={execution.execution_id} data-status={execution.status}>
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
                    {isTerminalExecution(execution)
                      ? "Run this terminal command? It will execute only after you approve."
                      : isGitExecution(execution)
                        ? gitApprovalCopy(execution)
                        : isBrowserExecution(execution)
                          ? browserApprovalCopy(execution)
                          : "Confirm this capability action? It will run only after you approve."}
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
                <>
                  {!hasLiveBrowserProgress ? (
                    <p className="capability-progress" role="status">
                      Running…
                    </p>
                  ) : null}
                  {hasLiveTerminalOutput && terminalOutput ? (
                    <TerminalOutputView output={terminalOutput} live />
                  ) : null}
                  {hasLiveBrowserProgress && browserOutput ? (
                    <BrowserResultView output={browserOutput} live />
                  ) : null}
                  {isTerminalExecution(execution) ||
                  isBrowserExecution(execution) ? (
                    <div className="capability-actions">
                      <button
                        type="button"
                        className="danger-button"
                        disabled={busyId === execution.execution_id}
                        onClick={() => onCancel(execution.execution_id)}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : null}
                </>
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
                    terminalOutput ? (
                      <TerminalOutputView output={terminalOutput} />
                    ) : gitOutput ? (
                      <GitResultView output={gitOutput} />
                    ) : browserOutput ? (
                      <BrowserResultView output={browserOutput} />
                    ) : (
                      <pre className="capability-output">
                        {typeof execution.output === "string"
                          ? execution.output
                          : JSON.stringify(execution.output, null, 2)}
                      </pre>
                    )
                  ) : null}
                </div>
              ) : null}
              {execution.status === "failed" && !confirmOverwrite ? (
                <div className="capability-result capability-result-failure">
                  <p>
                    {execution.error?.message ??
                      execution.error_message ??
                      "Capability execution failed."}
                  </p>
                  {terminalOutput ? (
                    <TerminalOutputView output={terminalOutput} />
                  ) : null}
                </div>
              ) : null}
              {execution.status === "cancelled" && terminalOutput ? (
                <TerminalOutputView output={terminalOutput} />
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function ChatPage() {
  const { activeWorkspace, activeModel, connection, chatSeed, clearChatSeed } =
    useAppState();
  const workspaceId = activeWorkspace?.id ?? null;

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null);
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
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [isDeletingConversation, setIsDeletingConversation] = useState(false);

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
    if (!chatSeed || !workspaceId || !canUseBackend) {
      return;
    }
    let cancelled = false;
    void listConversations(workspaceId)
      .then((payload) => {
        if (cancelled) return;
        setConversations(payload.conversations);
        setActiveConversationId(chatSeed.conversationId);
        setDraft(chatSeed.draft);
      })
      .finally(() => {
        if (!cancelled) clearChatSeed();
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatSeed, workspaceId, canUseBackend]);

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

  async function handleConfirmDelete() {
    if (!workspaceId || !pendingDeleteId) {
      return;
    }
    const conversationId = pendingDeleteId;
    setIsDeletingConversation(true);
    try {
      await deleteConversation(workspaceId, conversationId);
      setConversations((current) =>
        current.filter((item) => item.conversation_id !== conversationId),
      );
      if (activeConversationId === conversationId) {
        setActiveConversationId(null);
        setMessages([]);
      }
      setPendingDeleteId(null);
    } catch (err) {
      setError(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to delete conversation.",
      );
    } finally {
      setIsDeletingConversation(false);
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
      setError(
        "Cannot replace: original capability arguments are unavailable.",
      );
      return;
    }
    setExecutionBusyId(execution.execution_id);
    try {
      const result = await submitCapabilityExecution(workspaceId, {
        capability_id: execution.capability_id,
        conversation_id: execution.conversation_id,
        arguments: {
          ...(retry as Record<string, unknown>),
          overwrite_policy: "replace",
        },
      });
      setExecutions((current) => [
        ...current.filter(
          (item) => item.execution_id !== execution.execution_id,
        ),
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
          <Button
            onClick={() => void handleNewConversation()}
            disabled={!canUseBackend || isStreaming}
          >
            New Conversation
          </Button>
        </div>

        {isLoadingList ? (
          <LoadingState label="Loading conversations…" />
        ) : conversations.length === 0 ? (
          <EmptyState title="No conversations yet" />
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
                    <button type="button" onClick={() => setRenamingId(null)}>
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
                          setPendingDeleteId(conversation.conversation_id)
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
            <EmptyState
              title="Start a conversation"
              description="Create a conversation to start chatting with Memovi."
            />
          ) : isLoadingMessages ? (
            <LoadingState label="Loading messages…" />
          ) : messages.length === 0 ? (
            <EmptyState
              title="No messages yet"
              description="Ask a question below."
            />
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
                  <strong>{message.role === "user" ? "You" : "Memovi"}</strong>
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
              <Button variant="danger" onClick={stopGeneration}>
                Stop
              </Button>
            ) : (
              <Button type="submit" disabled={!canUseBackend || !draft.trim()}>
                Send
              </Button>
            )}
          </div>
        </form>
      </section>

      {pendingDeleteId ? (
        <ConfirmDialog
          title="Delete this conversation?"
          description="This removes the conversation and its messages. This cannot be undone."
          confirmLabel="Delete"
          tone="danger"
          busy={isDeletingConversation}
          onConfirm={() => void handleConfirmDelete()}
          onCancel={() => setPendingDeleteId(null)}
        />
      ) : null}
    </div>
  );
}
