/**
 * Minimal in-memory Memovi API stub for desktop smoke tests.
 * Covers the critical-path endpoints the shell and product pages call.
 */

import { DEFAULT_WORKSPACE_ID } from "../api/config";

export const SMOKE_USER = {
  id: "user-smoke-1",
  email: "smoke@memovi.test",
  created_at: "2026-01-01T00:00:00.000Z",
};

export const SMOKE_WORKSPACE = {
  id: DEFAULT_WORKSPACE_ID,
  name: "Default Workspace",
  created_at: "2026-01-01T00:00:00.000Z",
};

export const SMOKE_DOCUMENT = {
  id: "doc-smoke-1",
  name: "notes.txt",
  mime_type: "text/plain",
  processing_status: "completed",
  created_at: "2026-01-01T00:00:00.000Z",
  updated_at: "2026-01-01T00:00:00.000Z",
  size_bytes: 12,
  source_type: "upload",
};

type Json =
  Record<string, unknown> | unknown[] | string | number | boolean | null;

interface MockResponse {
  status: number;
  body: Json;
}

interface MockBackend {
  install: () => void;
  uninstall: () => void;
  isAuthenticated: () => boolean;
  calls: () => string[];
}

function jsonResponse(status: number, body: Json): Response {
  if (status === 204) {
    return new Response(null, { status });
  }
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function pathOf(url: string): string {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

export function createMockBackend(): MockBackend {
  let authenticated = false;
  const calls: string[] = [];
  const documents = [SMOKE_DOCUMENT];
  let conversationId = "conv-smoke-1";
  const originalFetch = globalThis.fetch;
  let xhrPatched = false;
  const OriginalXHR = globalThis.XMLHttpRequest;

  function route(
    method: string,
    url: string,
    bodyText: string | null,
  ): MockResponse {
    const path = pathOf(url);
    const key = `${method.toUpperCase()} ${path}`;
    calls.push(key);

    if (path === "/health") {
      return { status: 200, body: { status: "healthy" } };
    }
    if (path === "/ready") {
      return {
        status: 200,
        body: {
          status: "ready",
          environment: "test",
          components: [{ name: "postgres", status: "ok" }],
        },
      };
    }
    if (path === "/auth/me") {
      if (!authenticated) {
        return { status: 401, body: { detail: "Not authenticated" } };
      }
      return { status: 200, body: SMOKE_USER };
    }
    if (path === "/auth/login" && method === "POST") {
      authenticated = true;
      return { status: 200, body: SMOKE_USER };
    }
    if (path === "/auth/register" && method === "POST") {
      authenticated = true;
      return { status: 200, body: SMOKE_USER };
    }
    if (path === "/auth/logout" && method === "POST") {
      authenticated = false;
      return { status: 204, body: null };
    }
    if (path === "/workspaces" && method === "GET") {
      if (!authenticated)
        return { status: 401, body: { detail: "Not authenticated" } };
      return {
        status: 200,
        body: {
          workspaces: [{ ...SMOKE_WORKSPACE, role: "owner" }],
          count: 1,
        },
      };
    }
    if (
      path.match(/^\/workspaces\/[^/]+\/members$/) &&
      method === "GET"
    ) {
      return {
        status: 200,
        body: {
          items: [
            {
              id: "mem-smoke-1",
              workspace_id: DEFAULT_WORKSPACE_ID,
              user_id: SMOKE_USER.id,
              role: "owner",
              created_at: "2026-01-01T00:00:00.000Z",
              email: SMOKE_USER.email,
            },
          ],
          count: 1,
        },
      };
    }
    if (path === "/conversations/models") {
      return {
        status: 200,
        body: {
          models: [
            {
              provider: "fake",
              model: "fake-model",
              label: "Fake Model",
            },
          ],
          default_provider: "fake",
          default_model: "fake-model",
        },
      };
    }
    if (path === "/conversations" && method === "GET") {
      return {
        status: 200,
        body: {
          conversations: [
            {
              conversation_id: conversationId,
              title: "Smoke conversation",
              created_at: "2026-01-01T00:00:00.000Z",
              updated_at: "2026-01-01T00:00:00.000Z",
              message_count: 1,
            },
          ],
        },
      };
    }
    if (path === "/conversations" && method === "POST") {
      conversationId = "conv-smoke-created";
      return {
        status: 200,
        body: {
          conversation_id: conversationId,
          title: "New conversation",
          created_at: "2026-01-01T00:00:00.000Z",
        },
      };
    }
    if (
      path.startsWith("/conversations/") &&
      path.endsWith("/messages") &&
      method === "GET"
    ) {
      return {
        status: 200,
        body: {
          conversation_id: conversationId,
          messages: [
            {
              role: "assistant",
              content: "Hello from smoke stub.",
              timestamp: "2026-01-01T00:00:00.000Z",
              citations: [],
            },
          ],
        },
      };
    }
    if (path === "/documents" && method === "GET") {
      return {
        status: 200,
        body: { items: documents },
      };
    }
    if (path === "/connectors" && method === "GET") {
      return {
        status: 200,
        body: {
          items: [
            {
              connector_id: "filesystem",
              display_name: "Filesystem",
              description: "Local folder sync",
              source_category: "filesystem",
              auth_methods: ["none"],
              supports_incremental_sync: true,
              supports_delete_detection: true,
            },
          ],
          count: 1,
        },
      };
    }
    if (path === "/connectors/filesystem/folders" && method === "GET") {
      return { status: 200, body: { items: [], count: 0 } };
    }
    if (path === "/connectors/filesystem/folders" && method === "POST") {
      return {
        status: 201,
        body: {
          id: "folder-smoke-1",
          workspace_id: DEFAULT_WORKSPACE_ID,
          root_path: "C:\\smoke\\notes",
          display_name: "notes",
          sync_status: "idle",
          last_error: null,
          imported_document_count: 0,
          last_synchronized_at: null,
          created_at: "2026-01-01T00:00:00.000Z",
          updated_at: "2026-01-01T00:00:00.000Z",
        },
      };
    }
    if (path === "/documents" && method === "POST") {
      const uploaded = {
        ...SMOKE_DOCUMENT,
        id: "doc-smoke-uploaded",
        name: "uploaded.txt",
        processing_status: "pending",
      };
      documents.unshift(uploaded);
      return {
        status: 200,
        body: {
          document_id: uploaded.id,
          processing_job_id: "job-1",
          processing_status: "pending",
        },
      };
    }
    if (path === "/memory" || path.startsWith("/memory?")) {
      return {
        status: 200,
        body: {
          items: [
            {
              id: "ki-smoke-1",
              workspace_id: DEFAULT_WORKSPACE_ID,
              document_id: SMOKE_DOCUMENT.id,
              document_version_id: "ver-smoke-1",
              source_type: "upload",
              mime_type: "text/plain",
              created_at: "2026-01-01T00:00:00.000Z",
              updated_at: "2026-01-01T00:00:00.000Z",
              chunk_count: 1,
              summary: "Smoke knowledge",
              confidence: 1,
            },
          ],
          count: 1,
        },
      };
    }
    if (path === "/collections" || path.startsWith("/collections?")) {
      return { status: 200, body: { items: [], count: 0 } };
    }
    if (path.startsWith("/documents/") && method === "GET") {
      const id = path.split("/")[2];
      const doc = documents.find((item) => item.id === id) ?? SMOKE_DOCUMENT;
      return { status: 200, body: doc };
    }
    if (path.startsWith("/search")) {
      return {
        status: 200,
        body: {
          query: "smoke",
          count: 1,
          results: [
            {
              search_document_id: "sd-1",
              knowledge_item_id: "ki-1",
              document_id: SMOKE_DOCUMENT.id,
              score: 0.9,
              text: "Critical path search result",
            },
          ],
        },
      };
    }
    if (path === "/workflows" && method === "GET") {
      return {
        status: 200,
        body: {
          items: [
            {
              workflow_id: "list-directory",
              name: "List Directory",
              description: "List a folder",
              steps: [],
              variables: [
                {
                  name: "source_folder",
                  type: "path",
                  description: "Folder",
                  required: true,
                  default: null,
                },
              ],
              required_capabilities: ["filesystem"],
              expected_outputs: [],
              metadata: {},
            },
          ],
          count: 1,
        },
      };
    }
    if (
      path === "/workflows/history" ||
      path.startsWith("/workflows/history?")
    ) {
      return { status: 200, body: { items: [], count: 0 } };
    }
    if (path.endsWith("/execute") && method === "POST") {
      return {
        status: 200,
        body: {
          instance_id: "wf-instance-1",
          workflow_id: "list-directory",
          workflow_name: "List Directory",
          workspace_id: DEFAULT_WORKSPACE_ID,
          status: "completed",
          completed_steps: ["list"],
          failed_steps: [],
          step_results: [],
          duration: 0.01,
          outputs: { count: 0 },
          errors: [],
          audit_references: [],
          started_at: "2026-01-01T00:00:00.000Z",
          finished_at: "2026-01-01T00:00:01.000Z",
          metadata: {},
        },
      };
    }
    if (path === "/capabilities") {
      return {
        status: 200,
        body: {
          count: 1,
          items: [
            {
              id: "filesystem",
              description: "Filesystem",
              permissions: ["filesystem.read"],
              parameters: [],
              permission_mode: "ask_every_time",
            },
          ],
        },
      };
    }
    if (path.startsWith("/capabilities/executions")) {
      return { status: 200, body: { items: [], count: 0 } };
    }

    // Ignore unused body for unmatched routes.
    void bodyText;
    return { status: 404, body: { detail: `Unhandled mock route ${key}` } };
  }

  function installXhrMock(): void {
    if (xhrPatched) return;
    xhrPatched = true;

    class MockXHR {
      readyState = 0;
      status = 0;
      responseText = "";
      upload = {
        onprogress: null as ((event: ProgressEvent) => void) | null,
      };
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      onabort: (() => void) | null = null;
      private _method = "GET";
      private _url = "";

      open(method: string, url: string): void {
        this._method = method;
        this._url = url;
        this.readyState = 1;
      }

      setRequestHeader(): void {}

      abort(): void {
        this.onabort?.();
      }

      send(): void {
        const result = route(this._method, this._url, null);
        this.status = result.status;
        this.responseText =
          result.status === 204 ? "" : JSON.stringify(result.body);
        this.readyState = 4;
        this.upload.onprogress?.({
          lengthComputable: true,
          loaded: 1,
          total: 1,
        } as ProgressEvent);
        this.onload?.();
      }
    }

    // @ts-expect-error test double
    globalThis.XMLHttpRequest = MockXHR;
  }

  return {
    install() {
      installXhrMock();
      globalThis.fetch = (async (
        input: RequestInfo | URL,
        init?: RequestInit,
      ): Promise<Response> => {
        const url =
          typeof input === "string"
            ? input
            : input instanceof URL
              ? input.toString()
              : input.url;
        const method = (init?.method ?? "GET").toUpperCase();
        const bodyText = typeof init?.body === "string" ? init.body : null;
        const result = route(method, url, bodyText);
        return jsonResponse(result.status, result.body);
      }) as typeof fetch;
    },
    uninstall() {
      globalThis.fetch = originalFetch;
      if (xhrPatched) {
        globalThis.XMLHttpRequest = OriginalXHR;
        xhrPatched = false;
      }
      authenticated = false;
      calls.length = 0;
    },
    isAuthenticated: () => authenticated,
    calls: () => [...calls],
  };
}
