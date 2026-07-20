import { API_BASE_URL } from "./config";

export class ApiRequestError extends Error {
  readonly status: number | null;
  readonly kind: "network" | "http" | "parse";

  constructor(
    message: string,
    options: { status?: number | null; kind: "network" | "http" | "parse" },
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.status = options.status ?? null;
    this.kind = options.kind;
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new ApiRequestError(
      "Cannot reach the Memovi backend. Start it with `task backend`, then retry.",
      { kind: "network" },
    );
  }

  if (!response.ok) {
    throw new ApiRequestError(
      `Backend responded with HTTP ${response.status}.`,
      { status: response.status, kind: "http" },
    );
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
