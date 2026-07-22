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

export function TopBar() {
  const {
    connection,
    activeWorkspace,
    workspaces,
    availableModels,
    activeModel,
    setActiveWorkspaceId,
    setActiveModel,
    isRefreshing,
    refreshConnection,
  } = useAppState();

  return (
    <header className="top-bar">
      <div className="top-bar-cluster">
        <label className="top-bar-field">
          <span>Workspace</span>
          <select
            value={activeWorkspace?.id ?? ""}
            disabled={!activeWorkspace || workspaces.length === 0}
            onChange={(event) => setActiveWorkspaceId(event.target.value)}
          >
            {workspaces.length === 0 ? (
              <option value="">Unavailable</option>
            ) : (
              workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))
            )}
          </select>
        </label>

        <label className="top-bar-field">
          <span>Model</span>
          <select
            value={
              activeModel
                ? `${activeModel.provider}::${activeModel.model}`
                : ""
            }
            disabled={availableModels.length === 0}
            onChange={(event) => {
              const [provider, model] = event.target.value.split("::");
              const match = availableModels.find(
                (item) => item.provider === provider && item.model === model,
              );
              if (match) {
                setActiveModel({
                  provider: match.provider,
                  model: match.model,
                  label: match.label,
                });
              }
            }}
          >
            {availableModels.length === 0 ? (
              <option value="">No model selected</option>
            ) : (
              availableModels.map((item) => (
                <option
                  key={`${item.provider}::${item.model}`}
                  value={`${item.provider}::${item.model}`}
                >
                  {item.label}
                </option>
              ))
            )}
          </select>
        </label>
      </div>

      <div className="top-bar-cluster">
        <span className="status-pill">
          <span
            className="status-dot"
            data-tone={toneForStatus(connection.status)}
            aria-hidden="true"
          />
          {labelForStatus(connection.status)}
        </span>
        <button
          type="button"
          className="retry-button"
          onClick={() => void refreshConnection()}
          disabled={isRefreshing}
        >
          {isRefreshing ? "Refreshing…" : "Retry"}
        </button>
      </div>
    </header>
  );
}
