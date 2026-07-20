/** Local API base URL. Desktop never embeds business logic; it calls the platform API. */
export const API_BASE_URL =
  import.meta.env.VITE_MEMOVI_API_BASE?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

/** How often the shell re-probes backend availability. */
export const CONNECTION_POLL_INTERVAL_MS = 5_000;

/** Stable Default Workspace ID seeded by the backend for V1. */
export const DEFAULT_WORKSPACE_ID =
  "00000000-0000-4000-8000-000000000001";

export const WORKSPACE_ID_HEADER = "X-Memovi-Workspace-Id";
