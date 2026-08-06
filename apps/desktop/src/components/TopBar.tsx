import type { ConnectionStatus } from "../api/health";
import { useAppState } from "../state/AppStateContext";
import { Button } from "./ui/Button";
import { Dropdown } from "./ui/Dropdown";
import { TopBarLayout } from "./ui/TopBarLayout";

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
    <TopBarLayout
      left={
        <>
          <Dropdown
            label="Workspace"
            className="top-bar-field"
            value={activeWorkspace?.id ?? ""}
            disabled={!activeWorkspace || workspaces.length === 0}
            onChange={(event) => setActiveWorkspaceId(event.target.value)}
            options={
              workspaces.length === 0
                ? [{ value: "", label: "Unavailable" }]
                : workspaces.map((workspace) => ({
                    value: workspace.id,
                    label: workspace.name,
                  }))
            }
          />
          <Dropdown
            label="Model"
            className="top-bar-field"
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
            options={
              availableModels.length === 0
                ? [{ value: "", label: "No model selected" }]
                : availableModels.map((item) => ({
                    value: `${item.provider}::${item.model}`,
                    label: item.label,
                  }))
            }
          />
        </>
      }
      right={
        <>
          <span className="status-pill">
            <span
              className="status-dot"
              data-tone={toneForStatus(connection.status)}
              aria-hidden="true"
            />
            {labelForStatus(connection.status)}
          </span>
          <Button
            variant="secondary"
            onClick={() => void refreshConnection()}
            busy={isRefreshing}
          >
            {isRefreshing ? "Refreshing…" : "Retry"}
          </Button>
        </>
      }
    />
  );
}
