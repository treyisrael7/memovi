import { API_BASE_URL } from "./config";
import { ApiRequestError } from "./client";
import type { HealthResponse, ReadyComponent, ReadyResponse } from "./types";

export type ConnectionStatus =
  | "checking"
  | "connected"
  | "degraded"
  | "disconnected";

export interface ConnectionSnapshot {
  status: ConnectionStatus;
  healthOk: boolean;
  readyOk: boolean;
  environment: string | null;
  components: ReadyComponent[];
  error: string | null;
  lastCheckedAt: string;
}

function friendlyError(error: unknown): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Something went wrong while checking the backend.";
}

async function fetchJsonAllowingStatuses<T>(
  path: string,
  allowedStatuses: number[],
): Promise<{ status: number; body: T }> {
  const url = `${API_BASE_URL}${path}`;

  let response: Response;
  try {
    response = await fetch(url, { headers: { Accept: "application/json" } });
  } catch {
    throw new ApiRequestError(
      "Cannot reach the Memovi backend. Start it with `task backend`, then retry.",
      { kind: "network" },
    );
  }

  if (!response.ok && !allowedStatuses.includes(response.status)) {
    throw new ApiRequestError(
      `Backend responded with HTTP ${response.status}.`,
      { status: response.status, kind: "http" },
    );
  }

  try {
    return { status: response.status, body: (await response.json()) as T };
  } catch {
    throw new ApiRequestError("Backend returned an unexpected response.", {
      status: response.status,
      kind: "parse",
    });
  }
}

/**
 * Probe liveness (`/health`) then readiness (`/ready`).
 * `/ready` may return 503 when dependencies are down; that is degraded, not offline.
 */
export async function probeBackendConnection(): Promise<ConnectionSnapshot> {
  const lastCheckedAt = new Date().toISOString();

  try {
    const health = await fetchJsonAllowingStatuses<HealthResponse>("/health", []);
    const healthOk = health.body.status === "healthy";

    if (!healthOk) {
      return {
        status: "disconnected",
        healthOk: false,
        readyOk: false,
        environment: null,
        components: [],
        error: "Backend health check did not report healthy.",
        lastCheckedAt,
      };
    }

    const ready = await fetchJsonAllowingStatuses<ReadyResponse>("/ready", [
      503,
    ]);
    const components: ReadyComponent[] = ready.body.components ?? [];
    const environment = ready.body.environment ?? null;
    const readyOk = ready.body.status === "ready" && ready.status === 200;

    if (!readyOk) {
      return {
        status: "degraded",
        healthOk: true,
        readyOk: false,
        environment,
        components,
        error:
          "Backend is reachable but not fully ready. Some platform services may be unavailable.",
        lastCheckedAt,
      };
    }

    return {
      status: "connected",
      healthOk: true,
      readyOk: true,
      environment,
      components,
      error: null,
      lastCheckedAt,
    };
  } catch (error) {
    return {
      status: "disconnected",
      healthOk: false,
      readyOk: false,
      environment: null,
      components: [],
      error: friendlyError(error),
      lastCheckedAt,
    };
  }
}
