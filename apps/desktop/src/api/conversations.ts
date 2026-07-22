import { ApiRequestError, apiFetch, apiUrl, buildHeaders } from "./client";
import type {
  AvailableModelsResponse,
  ConversationListResponse,
  ConversationMessagesResponse,
  ConversationMetadata,
  CreateConversationResponse,
  SendMessageResponse,
} from "./types";

export async function listConversations(
  workspaceId: string,
): Promise<ConversationListResponse> {
  return apiFetch<ConversationListResponse>("/conversations", {
    workspaceId,
  });
}

export async function createConversation(
  workspaceId: string,
): Promise<CreateConversationResponse> {
  return apiFetch<CreateConversationResponse>("/conversations", {
    method: "POST",
    workspaceId,
  });
}

export async function renameConversation(
  workspaceId: string,
  conversationId: string,
  title: string,
): Promise<ConversationMetadata> {
  return apiFetch<ConversationMetadata>(`/conversations/${conversationId}`, {
    method: "PATCH",
    workspaceId,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export async function deleteConversation(
  workspaceId: string,
  conversationId: string,
): Promise<void> {
  await apiFetch<void>(`/conversations/${conversationId}`, {
    method: "DELETE",
    workspaceId,
  });
}

export async function listMessages(
  workspaceId: string,
  conversationId: string,
): Promise<ConversationMessagesResponse> {
  return apiFetch<ConversationMessagesResponse>(
    `/conversations/${conversationId}/messages`,
    { workspaceId },
  );
}

export async function listModels(
  workspaceId?: string | null,
): Promise<AvailableModelsResponse> {
  return apiFetch<AvailableModelsResponse>("/conversations/models", {
    workspaceId,
  });
}

export interface StreamMessageInput {
  workspaceId: string;
  conversationId: string;
  message: string;
  provider?: string | null;
  model?: string | null;
  signal?: AbortSignal;
  onToken: (content: string) => void;
  onDone: (result: SendMessageResponse) => void;
  onError: (error: Error) => void;
}

function parseSseChunk(chunk: string): Array<{ event: string; data: string }> {
  const events: Array<{ event: string; data: string }> = [];
  const blocks = chunk.split("\n\n");
  for (const block of blocks) {
    if (!block.trim()) {
      continue;
    }
    let event = "message";
    const dataLines: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }
    if (dataLines.length > 0) {
      events.push({ event, data: dataLines.join("\n") });
    }
  }
  return events;
}

export async function streamMessage(
  input: StreamMessageInput,
): Promise<void> {
  const url = apiUrl(`/conversations/${input.conversationId}/messages/stream`);
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      signal: input.signal,
      headers: buildHeaders(
        { workspaceId: input.workspaceId },
        {
          Accept: "text/event-stream",
          "Content-Type": "application/json",
        },
      ),
      body: JSON.stringify({
        message: input.message,
        provider: input.provider ?? undefined,
        model: input.model ?? undefined,
      }),
    });
  } catch (error) {
    if (input.signal?.aborted) {
      return;
    }
    throw new ApiRequestError(
      "Cannot reach the Memovi backend. Start it with `task backend`, then retry.",
      { kind: "network" },
    );
  }

  if (!response.ok || !response.body) {
    let detail: string | null = null;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      detail = null;
    }
    throw new ApiRequestError(
      detail ?? `Backend responded with HTTP ${response.status}.`,
      { status: response.status, kind: "http", detail },
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        for (const event of parseSseChunk(part)) {
          if (event.event === "token") {
            const payload = JSON.parse(event.data) as { content?: string };
            if (payload.content) {
              input.onToken(payload.content);
            }
          } else if (event.event === "done") {
            input.onDone(JSON.parse(event.data) as SendMessageResponse);
          } else if (event.event === "error") {
            const payload = JSON.parse(event.data) as {
              detail?: string;
              status?: number;
            };
            input.onError(
              new ApiRequestError(payload.detail ?? "Streaming failed.", {
                kind: "http",
                status: payload.status ?? null,
                detail: payload.detail ?? null,
              }),
            );
            return;
          }
        }
      }
    }
    if (buffer.trim()) {
      for (const event of parseSseChunk(buffer)) {
        if (event.event === "done") {
          input.onDone(JSON.parse(event.data) as SendMessageResponse);
        } else if (event.event === "error") {
          const payload = JSON.parse(event.data) as {
            detail?: string;
            status?: number;
          };
          input.onError(
            new ApiRequestError(payload.detail ?? "Streaming failed.", {
              kind: "http",
              status: payload.status ?? null,
              detail: payload.detail ?? null,
            }),
          );
        }
      }
    }
  } catch (error) {
    if (input.signal?.aborted) {
      return;
    }
    throw error instanceof Error
      ? error
      : new ApiRequestError("Streaming failed.", { kind: "parse" });
  }
}
