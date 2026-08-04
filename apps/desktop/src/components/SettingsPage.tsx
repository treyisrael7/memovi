import { useEffect, useState } from "react";

import {
  listCapabilities,
  setCapabilityPermissionMode,
} from "../api/capabilities";
import { ApiRequestError } from "../api/client";
import type { CapabilityMetadata, PermissionMode } from "../api/types";
import { createWorkspace } from "../api/workspaces";
import { type ThemeMode, useAppState } from "../state/AppStateContext";
import { EmptyState } from "./ui/EmptyState";
import { LoadingState } from "./ui/LoadingState";
import { useToast } from "./ui/ToastContext";

type SettingsSection =
  "general" | "workspaces" | "capabilities" | "diagnostics";

const SECTIONS: ReadonlyArray<{ id: SettingsSection; label: string }> = [
  { id: "general", label: "General" },
  { id: "workspaces", label: "Workspaces" },
  { id: "capabilities", label: "Capabilities" },
  { id: "diagnostics", label: "Diagnostics" },
];

const PERMISSION_MODES: ReadonlyArray<{ id: PermissionMode; label: string }> = [
  { id: "ask_every_time", label: "Ask every time" },
  { id: "always_allow", label: "Always allow" },
  { id: "deny", label: "Deny" },
];

function GeneralSection() {
  const { availableModels, activeModel, setActiveModel, theme, setTheme } =
    useAppState();

  return (
    <div className="settings-section">
      <h2>Model</h2>
      <p className="muted">Choose the language model used for conversations.</p>
      <label className="settings-field">
        <span>Active model</span>
        <select
          value={
            activeModel ? `${activeModel.provider}::${activeModel.model}` : ""
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
            <option value="">No model available</option>
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

      <h2>Appearance</h2>
      <label className="settings-field">
        <span>Theme</span>
        <select
          value={theme}
          onChange={(event) => setTheme(event.target.value as ThemeMode)}
        >
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
      </label>
    </div>
  );
}

function WorkspacesSection() {
  const {
    workspaces,
    activeWorkspace,
    setActiveWorkspaceId,
    refreshWorkspaces,
  } = useAppState();
  const { showToast } = useToast();
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  async function handleCreate() {
    const name = newWorkspaceName.trim();
    if (!name) return;
    setIsCreating(true);
    try {
      await createWorkspace(name);
      await refreshWorkspaces();
      setNewWorkspaceName("");
      showToast(`Created workspace "${name}".`, "ok");
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to create workspace.",
        "bad",
      );
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <div className="settings-section">
      <h2>Workspaces</h2>
      <p className="muted">
        Workspaces isolate documents, knowledge, and conversations from each
        other.
      </p>
      <ul className="workspace-list">
        {workspaces.map((workspace) => (
          <li key={workspace.id}>
            <span>{workspace.name}</span>
            {workspace.id === activeWorkspace?.id ? (
              <span className="status-badge" data-tone="ok">
                Active
              </span>
            ) : (
              <button
                type="button"
                className="retry-button"
                onClick={() => setActiveWorkspaceId(workspace.id)}
              >
                Switch
              </button>
            )}
          </li>
        ))}
        {workspaces.length === 0 ? (
          <li className="muted">No workspaces yet.</li>
        ) : null}
      </ul>

      <form
        className="settings-field"
        onSubmit={(event) => {
          event.preventDefault();
          void handleCreate();
        }}
      >
        <span>New workspace name</span>
        <input
          type="text"
          value={newWorkspaceName}
          onChange={(event) => setNewWorkspaceName(event.target.value)}
          placeholder="e.g. Personal Research"
        />
        <button
          type="submit"
          className="primary-button settings-inline-action"
          disabled={isCreating || !newWorkspaceName.trim()}
        >
          {isCreating ? "Creating…" : "Create workspace"}
        </button>
      </form>
    </div>
  );
}

function CapabilitiesSection() {
  const { activeWorkspace, connection } = useAppState();
  const { showToast } = useToast();
  const workspaceId = activeWorkspace?.id ?? null;
  const canUseBackend =
    connection.status === "connected" || connection.status === "degraded";

  const [capabilities, setCapabilities] = useState<CapabilityMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId || !canUseBackend) {
      setCapabilities([]);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    void listCapabilities(workspaceId)
      .then((payload) => {
        if (!cancelled) setCapabilities(payload.items);
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, canUseBackend]);

  async function handleChange(capabilityId: string, mode: PermissionMode) {
    if (!workspaceId) return;
    setBusyId(capabilityId);
    try {
      await setCapabilityPermissionMode(workspaceId, capabilityId, mode);
      setCapabilities((current) =>
        current.map((item) =>
          item.id === capabilityId ? { ...item, permission_mode: mode } : item,
        ),
      );
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to update capability policy.",
        "bad",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="settings-section">
      <h2>Capability policies</h2>
      <p className="muted">
        Control whether Memovi may act on your behalf automatically, ask first,
        or never for each capability.
      </p>
      {isLoading ? (
        <LoadingState label="Loading capabilities…" />
      ) : capabilities.length === 0 ? (
        <EmptyState title="No capabilities registered" />
      ) : (
        <ul className="capability-policy-list">
          {capabilities.map((capability) => (
            <li key={capability.id} className="capability-policy-row">
              <div>
                <div className="capability-policy-name">{capability.id}</div>
                <div className="capability-policy-description">
                  {capability.description}
                </div>
              </div>
              <select
                value={capability.permission_mode}
                disabled={busyId === capability.id}
                onChange={(event) =>
                  void handleChange(
                    capability.id,
                    event.target.value as PermissionMode,
                  )
                }
              >
                {PERMISSION_MODES.map((mode) => (
                  <option key={mode.id} value={mode.id}>
                    {mode.label}
                  </option>
                ))}
              </select>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function DiagnosticsSection() {
  const { connection, isRefreshing, refreshConnection } = useAppState();

  return (
    <div className="settings-section">
      <h2>Diagnostics</h2>
      <p className="muted">
        Live status of the Memovi backend and its platform components.
      </p>
      <dl className="meta-grid">
        <div className="meta-card">
          <dt>Connection</dt>
          <dd>{connection.status}</dd>
        </div>
        <div className="meta-card">
          <dt>Environment</dt>
          <dd>{connection.environment ?? "—"}</dd>
        </div>
        <div className="meta-card">
          <dt>Last checked</dt>
          <dd>
            {connection.lastCheckedAt === new Date(0).toISOString()
              ? "—"
              : new Date(connection.lastCheckedAt).toLocaleTimeString()}
          </dd>
        </div>
      </dl>

      {connection.error ? (
        <div
          className="banner"
          data-tone={connection.status === "degraded" ? "warn" : "bad"}
        >
          {connection.error}
        </div>
      ) : null}

      <ul className="component-list">
        {connection.components.map((component) => (
          <li key={component.name}>
            <span className="component-name">{component.name}</span>
            <span
              className="component-status"
              data-status={component.status === "up" ? "up" : "down"}
            >
              {component.status}
              {component.detail ? ` — ${component.detail}` : ""}
            </span>
          </li>
        ))}
        {connection.components.length === 0 ? (
          <li className="muted">No component detail reported yet.</li>
        ) : null}
      </ul>

      <button
        type="button"
        className="retry-button"
        onClick={() => void refreshConnection()}
        disabled={isRefreshing}
      >
        {isRefreshing ? "Refreshing…" : "Recheck now"}
      </button>
    </div>
  );
}

export function SettingsPage() {
  const [section, setSection] = useState<SettingsSection>("general");

  return (
    <div className="settings-page">
      <nav className="settings-nav" aria-label="Settings sections">
        {SECTIONS.map((entry) => (
          <button
            key={entry.id}
            type="button"
            data-active={section === entry.id}
            onClick={() => setSection(entry.id)}
          >
            {entry.label}
          </button>
        ))}
      </nav>
      <div className="settings-content">
        {section === "general" ? <GeneralSection /> : null}
        {section === "workspaces" ? <WorkspacesSection /> : null}
        {section === "capabilities" ? <CapabilitiesSection /> : null}
        {section === "diagnostics" ? <DiagnosticsSection /> : null}
      </div>
    </div>
  );
}
