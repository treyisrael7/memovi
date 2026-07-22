import { API_BASE_URL, WORKSPACE_ID_HEADER } from "./config";

export class ApiRequestError extends Error {
  readonly status: number | null;
  readonly kind: "network" | "http" | "parse";
  readonly detail: string | null;

  constructor(
    message: string,
    options: {
      status?: number | null;
      kind: "network" | "http" | "parse";
      detail?: string | null;
    },
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.status = options.status ?? null;
    this.kind = options.kind;
    this.detail = options.detail ?? null;
  }
}

export interface ApiFetchOptions extends RequestInit {
  workspaceId?: string | null;
}

function buildHeaders(
  init: ApiFetchOptions | undefined,
  defaults: Record<string, string>,
): Headers {
  const headers = new Headers(defaults);
  if (init?.headers) {
    const extra = new Headers(init.headers);
    extra.forEach((value, key) => {
      headers.set(key, value);
    });
  }
  if (init?.workspaceId) {
    headers.set(WORKSPACE_ID_HEADER, init.workspaceId);
  }
  return headers;
}

export async function apiFetch<T>(
  path: string,
  init?: ApiFetchOptions,
): Promise<T> {
  const url = `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const { workspaceId: _workspaceId, ...requestInit } = init ?? {};

  let response: Response;
  try {
    response = await fetch(url, {
      ...requestInit,
      headers: buildHeaders(init, { Accept: "application/json" }),
    });
  } catch {
    throw new ApiRequestError(
      "Cannot reach the Memovi backend. Start it with `task backend`, then retry.",
      { kind: "network" },
    );
  }

  if (!response.ok) {
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

  if (response.status === 204) {
    return undefined as T;
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiRequestError("Backend returned an unexpected response.", {
      status: response.status,
      kind: "parse",
    });
  }
}

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export { buildHeaders };
