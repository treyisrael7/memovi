import type { ConnectionStatus } from "../api/health";
import { useAppState } from "../state/AppStateContext";

function toneForStatus(status: ConnectionStatus): "ok" | "warn" | "bad" | "idle" {
  switch (status) {
    case "connected":
      return "ok";
    case "degraded":
      return "warn";
    case "disconnected":
      return "bad";
    default:
      return "idle";
  }
}

function labelForStatus(status: ConnectionStatus): string {
  switch (status) {
    case "connected":
      return "Connected";
    case "degraded":
      return "Degraded";
    case "disconnected":
      return "Disconnected";
    default:
      return "Checking…";
  }
}

export function StatusBar() {
  const {
    connection,
    activeWorkspace,
    activeModelLabel,
    isRefreshing,
    refreshConnection,
  } = useAppState();

  const checkedLabel =
    connection.lastCheckedAt === new Date(0).toISOString()
      ? "—"
      : new Date(connection.lastCheckedAt).toLocaleTimeString();

  return (
    <footer className="status-bar">
      <div className="status-cluster">
        <span className="status-pill">
          <span
            className="status-dot"
            data-tone={toneForStatus(connection.status)}
            aria-hidden="true"
          />
          Backend: {labelForStatus(connection.status)}
        </span>
        <span className="status-pill">
          Workspace: {activeWorkspace?.name ?? "Unavailable"}
        </span>
        <span className="status-pill">Model: {activeModelLabel}</span>
        {connection.environment ? (
          <span className="status-pill">Env: {connection.environment}</span>
        ) : null}
      </div>

      <div className="status-cluster">
        <span className="status-pill">Checked {checkedLabel}</span>
        <button
          type="button"
          className="retry-button"
          onClick={() => void refreshConnection()}
          disabled={isRefreshing}
        >
          {isRefreshing ? "Refreshing…" : "Retry"}
        </button>
      </div>
    </footer>
  );
}
