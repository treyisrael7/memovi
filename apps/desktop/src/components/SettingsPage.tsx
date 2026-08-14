import { useEffect, useState } from "react";

import {
  listCapabilities,
  setCapabilityPermissionMode,
} from "../api/capabilities";
import { ApiRequestError } from "../api/client";
import type {
  CapabilityMetadata,
  PermissionMode,
  WorkspaceMembership,
} from "../api/types";
import {
  createWorkspace,
  inviteWorkspaceMember,
  leaveWorkspace,
  listWorkspaceMembers,
  removeWorkspaceMember,
  transferWorkspaceOwnership,
} from "../api/workspaces";
import { type ThemeMode, useAppState } from "../state/AppStateContext";
import type { SettingsSectionId } from "../navigation/pages";
import { describeProviderSetup } from "./gettingStarted";
import {
  ProviderBackendEnvInstructions,
  ProviderConnectedStatus,
  ProviderSetupSteps,
} from "./ProviderSetupGuidance";
import { Alert } from "./ui/Alert";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";
import { ConfirmationDialog } from "./ui/ConfirmDialog";
import { Dropdown } from "./ui/Dropdown";
import { EmptyState } from "./ui/EmptyState";
import { LoadingState } from "./ui/LoadingState";
import { TextInput } from "./ui/TextInput";
import { useToast } from "./ui/ToastContext";

const SECTIONS: ReadonlyArray<{ id: SettingsSectionId; label: string }> = [
  { id: "general", label: "General" },
  { id: "account", label: "Account" },
  { id: "workspaces", label: "Workspaces" },
  { id: "capabilities", label: "Capabilities" },
  { id: "diagnostics", label: "Diagnostics" },
];

const PERMISSION_MODES: ReadonlyArray<{ id: PermissionMode; label: string }> = [
  { id: "ask_every_time", label: "Ask every time" },
  { id: "always_allow", label: "Always allow" },
  { id: "deny", label: "Deny" },
];

function GeneralSection({
  onOpenDiagnostics,
}: {
  onOpenDiagnostics: () => void;
}) {
  const {
    availableModels,
    activeModel,
    setActiveModel,
    theme,
    setTheme,
    connection,
  } = useAppState();
  const providerSetup = describeProviderSetup({
    connectionStatus: connection.status,
    models: availableModels,
  });

  return (
    <div className="settings-section">
      <h2>Model</h2>
      <p className="muted">Choose the language model used for conversations.</p>

      {providerSetup.kind === "none" ? (
        <EmptyState
          title={providerSetup.title}
          description={providerSetup.description}
          action={
            <Button variant="secondary" onClick={onOpenDiagnostics}>
              Open Diagnostics
            </Button>
          }
        />
      ) : null}

      {providerSetup.kind === "fake_only" ? (
        <div className="provider-setup-inline">
          <Alert tone="info">{providerSetup.description}</Alert>
          <ProviderSetupSteps />
          <Button variant="secondary" onClick={onOpenDiagnostics}>
            Open Diagnostics
          </Button>
        </div>
      ) : null}

      {providerSetup.kind === "ready" ? (
        <ProviderConnectedStatus models={availableModels} />
      ) : null}

      {providerSetup.kind !== "none" ? (
        <Dropdown
          label="Active model"
          className="settings-field"
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
          options={availableModels.map((item) => ({
            value: `${item.provider}::${item.model}`,
            label: item.label,
          }))}
        />
      ) : null}

      <h2>Appearance</h2>
      <Dropdown
        label="Theme"
        className="settings-field"
        value={theme}
        onChange={(event) => setTheme(event.target.value as ThemeMode)}
        options={[
          { value: "light", label: "Light" },
          { value: "dark", label: "Dark" },
        ]}
      />
    </div>
  );
}

function AccountSection() {
  const { user, logout } = useAppState();
  const { showToast } = useToast();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleLogout() {
    setBusy(true);
    try {
      await logout();
      showToast("Signed out.", "ok");
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to sign out. Try again.",
        "bad",
      );
      setBusy(false);
      setConfirmOpen(false);
    }
  }

  return (
    <div className="settings-section">
      <h2>Account</h2>
      <p className="muted">
        You are signed in with a server-managed session. Memovi never stores
        your password on this device.
      </p>
      <dl className="meta-grid">
        <div className="meta-card">
          <dt>Email</dt>
          <dd>{user?.email ?? "—"}</dd>
        </div>
      </dl>
      <Button variant="danger" onClick={() => setConfirmOpen(true)}>
        Sign out
      </Button>
      {confirmOpen ? (
        <ConfirmationDialog
          title="Sign out?"
          description="You will need to sign in again to access your workspaces and knowledge."
          confirmLabel="Sign out"
          tone="danger"
          busy={busy}
          onConfirm={() => void handleLogout()}
          onCancel={() => {
            if (!busy) setConfirmOpen(false);
          }}
        />
      ) : null}
    </div>
  );
}

function WorkspacesSection() {
  const {
    user,
    workspaces,
    activeWorkspace,
    setActiveWorkspaceId,
    refreshWorkspaces,
  } = useAppState();
  const { showToast } = useToast();
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [members, setMembers] = useState<WorkspaceMembership[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [isInviting, setIsInviting] = useState(false);
  const [pendingRemove, setPendingRemove] =
    useState<WorkspaceMembership | null>(null);
  const [pendingTransfer, setPendingTransfer] =
    useState<WorkspaceMembership | null>(null);
  const [pendingLeave, setPendingLeave] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);

  const workspaceId = activeWorkspace?.id ?? null;
  const isOwner = (activeWorkspace?.role ?? "").toLowerCase() === "owner";
  const currentUserId = user?.id ?? null;

  async function refreshMembers() {
    if (!workspaceId) {
      setMembers([]);
      return;
    }
    setMembersLoading(true);
    try {
      setMembers(await listWorkspaceMembers(workspaceId));
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to load members.",
        "bad",
      );
    } finally {
      setMembersLoading(false);
    }
  }

  useEffect(() => {
    void refreshMembers();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload when active workspace changes
  }, [workspaceId]);

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

  async function handleInvite() {
    if (!workspaceId || !inviteEmail.trim()) return;
    setIsInviting(true);
    try {
      await inviteWorkspaceMember(workspaceId, inviteEmail.trim());
      setInviteEmail("");
      showToast("Member invited.", "ok");
      await refreshMembers();
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to invite member.",
        "bad",
      );
    } finally {
      setIsInviting(false);
    }
  }

  async function handleConfirmRemove() {
    if (!workspaceId || !pendingRemove) return;
    setActionBusy(true);
    try {
      await removeWorkspaceMember(workspaceId, pendingRemove.user_id);
      showToast("Member removed.", "ok");
      setPendingRemove(null);
      await refreshMembers();
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to remove member.",
        "bad",
      );
    } finally {
      setActionBusy(false);
    }
  }

  async function handleConfirmTransfer() {
    if (!workspaceId || !pendingTransfer) return;
    setActionBusy(true);
    try {
      await transferWorkspaceOwnership(workspaceId, pendingTransfer.user_id);
      showToast("Ownership transferred.", "ok");
      setPendingTransfer(null);
      await refreshWorkspaces();
      await refreshMembers();
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to transfer ownership.",
        "bad",
      );
    } finally {
      setActionBusy(false);
    }
  }

  async function handleConfirmLeave() {
    if (!workspaceId) return;
    setActionBusy(true);
    try {
      await leaveWorkspace(workspaceId);
      showToast("You left the workspace.", "ok");
      setPendingLeave(false);
      await refreshWorkspaces();
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to leave workspace.",
        "bad",
      );
    } finally {
      setActionBusy(false);
    }
  }

  return (
    <div className="settings-section">
      <h2>Workspaces</h2>
      <p className="muted">
        Workspaces isolate documents, knowledge, and conversations. Owners
        manage members and ownership.
      </p>
      <ul className="workspace-list">
        {workspaces.map((workspace) => (
          <li key={workspace.id}>
            <span>
              {workspace.name}
              {workspace.role ? (
                <span className="muted"> · {workspace.role}</span>
              ) : null}
            </span>
            {workspace.id === activeWorkspace?.id ? (
              <Badge label="Active" tone="ok" />
            ) : (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setActiveWorkspaceId(workspace.id)}
              >
                Switch
              </Button>
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
        <TextInput
          label="New workspace name"
          value={newWorkspaceName}
          onChange={(event) => setNewWorkspaceName(event.target.value)}
          placeholder="e.g. Personal Research"
        />
        <Button
          type="submit"
          className="settings-inline-action"
          busy={isCreating}
          disabled={!newWorkspaceName.trim()}
        >
          {isCreating ? "Creating…" : "Create workspace"}
        </Button>
      </form>

      <h3 className="settings-subsection-title">
        Members{activeWorkspace ? ` — ${activeWorkspace.name}` : ""}
      </h3>
      {!workspaceId ? (
        <EmptyState
          title="No active workspace"
          description="Select a workspace to manage members."
        />
      ) : membersLoading ? (
        <LoadingState label="Loading members…" />
      ) : (
        <>
          <ul className="workspace-member-list">
            {members.map((member) => {
              const label = member.email ?? member.user_id;
              const isSelf = member.user_id === currentUserId;
              return (
                <li key={member.id} className="workspace-member-row">
                  <div>
                    <div className="workspace-member-name">
                      {label}
                      {isSelf ? " (you)" : ""}
                    </div>
                    <Badge
                      label={member.role === "owner" ? "Owner" : "Member"}
                      tone={member.role === "owner" ? "ok" : "idle"}
                    />
                  </div>
                  {isOwner && !isSelf ? (
                    <div className="workspace-member-actions">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setPendingTransfer(member)}
                      >
                        Make owner
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => setPendingRemove(member)}
                      >
                        Remove
                      </Button>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>

          {isOwner ? (
            <form
              className="settings-field"
              onSubmit={(event) => {
                event.preventDefault();
                void handleInvite();
              }}
            >
              <TextInput
                label="Invite by email"
                value={inviteEmail}
                onChange={(event) => setInviteEmail(event.target.value)}
                placeholder="registered-user@example.com"
              />
              <Button
                type="submit"
                className="settings-inline-action"
                busy={isInviting}
                disabled={!inviteEmail.trim()}
              >
                {isInviting ? "Inviting…" : "Invite member"}
              </Button>
            </form>
          ) : (
            <p className="muted">
              Only workspace owners can invite or remove members.
            </p>
          )}

          <div className="settings-field">
            <Button
              variant="secondary"
              onClick={() => setPendingLeave(true)}
              disabled={!currentUserId}
            >
              Leave workspace
            </Button>
          </div>
        </>
      )}

      {pendingRemove ? (
        <ConfirmationDialog
          title={`Remove ${pendingRemove.email ?? pendingRemove.user_id}?`}
          description="They will lose access to this workspace's documents and knowledge."
          confirmLabel="Remove"
          tone="danger"
          busy={actionBusy}
          onConfirm={() => void handleConfirmRemove()}
          onCancel={() => setPendingRemove(null)}
        />
      ) : null}

      {pendingTransfer ? (
        <ConfirmationDialog
          title="Transfer ownership?"
          description={`Make ${pendingTransfer.email ?? pendingTransfer.user_id} the owner. You will become a member.`}
          confirmLabel="Transfer ownership"
          busy={actionBusy}
          onConfirm={() => void handleConfirmTransfer()}
          onCancel={() => setPendingTransfer(null)}
        />
      ) : null}

      {pendingLeave ? (
        <ConfirmationDialog
          title="Leave this workspace?"
          description="If you are the sole owner, transfer ownership first."
          confirmLabel="Leave"
          tone="danger"
          busy={actionBusy}
          onConfirm={() => void handleConfirmLeave()}
          onCancel={() => setPendingLeave(false)}
        />
      ) : null}
    </div>
  );
}

function CapabilitiesSection() {
  const { activeWorkspace, connection } = useAppState();
  const { showToast } = useToast();
  const workspaceId = activeWorkspace?.id ?? null;
  const isOwner = (activeWorkspace?.role ?? "").toLowerCase() === "owner";
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
        or never for each capability. Only workspace owners can change these
        policies.
      </p>
      {!isOwner ? (
        <Alert tone="warn">
          Capability policies are read-only for members. Ask a workspace owner
          to change them.
        </Alert>
      ) : null}
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
                disabled={!isOwner || busyId === capability.id}
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
  const { connection, isRefreshing, refreshConnection, availableModels } =
    useAppState();
  const providerSetup = describeProviderSetup({
    connectionStatus: connection.status,
    models: availableModels,
  });

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
        <Alert tone={connection.status === "degraded" ? "warn" : "bad"}>
          {connection.error}
        </Alert>
      ) : null}

      <h3>AI provider setup</h3>
      {providerSetup.kind === "fake_only" ? (
        <Alert tone="info">{providerSetup.description}</Alert>
      ) : null}
      {providerSetup.kind === "ready" ? (
        <ProviderConnectedStatus models={availableModels} />
      ) : null}
      {providerSetup.kind === "backend_unavailable" ? (
        <Alert tone="warn">{providerSetup.description}</Alert>
      ) : null}
      {providerSetup.kind === "none" ? (
        <Alert tone="warn">{providerSetup.description}</Alert>
      ) : null}
      <p className="muted">
        Provider API keys stay in the backend environment. Memovi does not
        accept keys in the desktop app.
      </p>
      <ProviderBackendEnvInstructions />

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

      <Button
        variant="secondary"
        onClick={() => void refreshConnection()}
        busy={isRefreshing}
      >
        {isRefreshing ? "Refreshing…" : "Recheck now"}
      </Button>
    </div>
  );
}

export function SettingsPage() {
  const { settingsSection, setSettingsSection } = useAppState();

  return (
    <div className="settings-page">
      <nav className="settings-nav" aria-label="Settings sections">
        {SECTIONS.map((entry) => (
          <button
            key={entry.id}
            type="button"
            data-active={settingsSection === entry.id}
            onClick={() => setSettingsSection(entry.id)}
          >
            {entry.label}
          </button>
        ))}
      </nav>
      <div className="settings-content">
        {settingsSection === "general" ? (
          <GeneralSection
            onOpenDiagnostics={() => setSettingsSection("diagnostics")}
          />
        ) : null}
        {settingsSection === "account" ? <AccountSection /> : null}
        {settingsSection === "workspaces" ? <WorkspacesSection /> : null}
        {settingsSection === "capabilities" ? <CapabilitiesSection /> : null}
        {settingsSection === "diagnostics" ? <DiagnosticsSection /> : null}
      </div>
    </div>
  );
}
