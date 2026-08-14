import { useCallback, useEffect, useState } from "react";

import { ApiRequestError } from "../api/client";
import {
  addFilesystemFolder,
  listFilesystemFolders,
  removeFilesystemFolder,
  syncFilesystemFolder,
} from "../api/connectors";
import type { FilesystemFolder } from "../api/types";
import { folderDisplayName } from "../connectors/folderPath";
import { useAppState } from "../state/AppStateContext";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";
import { ConfirmDialog } from "./ui/ConfirmDialog";
import { EmptyState } from "./ui/EmptyState";
import { FilePicker } from "./ui/FilePicker";
import { LoadingState } from "./ui/LoadingState";
import { SectionHeader } from "./ui/SectionHeader";
import { StatusBadge, type StatusTone } from "./ui/StatusBadge";
import { TextInput } from "./ui/TextInput";
import { useToast } from "./ui/ToastContext";
import { Tooltip } from "./ui/Tooltip";

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "Never";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function syncStatusTone(status: string): StatusTone {
  switch (status) {
    case "healthy":
      return "ok";
    case "syncing":
      return "warn";
    case "error":
      return "bad";
    case "idle":
    default:
      return "idle";
  }
}

export function ConnectorsPage() {
  const { activeWorkspace, connection } = useAppState();
  const { showToast } = useToast();
  const workspaceId = activeWorkspace?.id ?? null;
  const canUseBackend =
    connection.status === "connected" || connection.status === "degraded";

  const [folders, setFolders] = useState<FilesystemFolder[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rootPath, setRootPath] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [pendingRemove, setPendingRemove] = useState<FilesystemFolder | null>(
    null,
  );
  const [isRemoving, setIsRemoving] = useState(false);

  const refresh = useCallback(async () => {
    if (!workspaceId || !canUseBackend) {
      setFolders([]);
      return;
    }
    try {
      setIsLoading(true);
      setError(null);
      const payload = await listFilesystemFolders(workspaceId);
      setFolders(payload.items);
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? err.message
          : "Failed to load connected folders.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId, canUseBackend]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleAdd = async () => {
    if (!workspaceId || !rootPath.trim()) return;
    try {
      setIsAdding(true);
      setError(null);
      await addFilesystemFolder(workspaceId, {
        root_path: rootPath.trim(),
        display_name: displayName.trim() || null,
      });
      setRootPath("");
      setDisplayName("");
      showToast("Folder connected.", "ok");
      await refresh();
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? err.message
          : "Failed to connect folder.";
      setError(message);
      showToast(message, "bad");
    } finally {
      setIsAdding(false);
    }
  };

  const handleSync = async (folder: FilesystemFolder) => {
    if (!workspaceId) return;
    try {
      setSyncingId(folder.id);
      setError(null);
      const result = await syncFilesystemFolder(workspaceId, folder.id);
      if (result.success) {
        showToast(
          `Synced ${folder.display_name}: ${result.imported_count} imported, ${result.updated_count} updated, ${result.deleted_count} deleted.`,
          "ok",
        );
      } else {
        showToast(result.error_message ?? "Sync failed.", "bad");
      }
      await refresh();
    } catch (err) {
      const message =
        err instanceof ApiRequestError ? err.message : "Sync failed.";
      setError(message);
      showToast(message, "bad");
      await refresh();
    } finally {
      setSyncingId(null);
    }
  };

  const handleRemove = async () => {
    if (!workspaceId || !pendingRemove) return;
    try {
      setIsRemoving(true);
      await removeFilesystemFolder(workspaceId, pendingRemove.id);
      showToast("Folder disconnected.", "ok");
      setPendingRemove(null);
      await refresh();
    } catch (err) {
      const message =
        err instanceof ApiRequestError
          ? err.message
          : "Failed to remove folder.";
      showToast(message, "bad");
    } finally {
      setIsRemoving(false);
    }
  };

  return (
    <div className="connectors-page">
      <SectionHeader
        title="Connectors"
        level={1}
        description="Connect local folders as knowledge sources. Files import through the Documents pipeline and become searchable after processing."
      />

      {!canUseBackend ? (
        <Alert tone="warn">
          Connect to the backend to manage filesystem folders.
        </Alert>
      ) : null}

      {error ? <Alert tone="bad">{error}</Alert> : null}

      <section className="panel">
        <h2 className="panel-title">Add folder</h2>
        <p className="muted">
          Choose a folder with Browse…, or enter an absolute path to a notes
          folder, Obsidian vault, or project docs directory on this machine.
        </p>
        <div className="stack connector-add-form">
          <div className="connector-path-row">
            <TextInput
              label="Folder path"
              name="root_path"
              placeholder="C:\Users\you\Documents\notes"
              value={rootPath}
              onChange={(event) => setRootPath(event.target.value)}
              disabled={!canUseBackend || isAdding}
            />
            <FilePicker
              mode="directory"
              buttonLabel="Browse..."
              disabled={!canUseBackend || isAdding}
              defaultPath={rootPath}
              onDirectorySelected={setRootPath}
            />
          </div>
          <TextInput
            label="Display name (optional)"
            name="display_name"
            placeholder="Research notes"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            disabled={!canUseBackend || isAdding}
          />
          <div className="document-detail-actions">
            <Button
              onClick={() => void handleAdd()}
              disabled={!canUseBackend || isAdding || !rootPath.trim()}
            >
              {isAdding ? "Connecting…" : "Add folder"}
            </Button>
          </div>
        </div>
      </section>

      <section className="panel">
        <SectionHeader
          title="Connected folders"
          description="Manual sync imports new and changed files. Background watchers are not enabled yet."
        />

        {isLoading && folders.length === 0 ? (
          <LoadingState label="Loading folders…" />
        ) : null}

        {!isLoading && folders.length === 0 ? (
          <EmptyState
            title="No folders connected"
            description="Add a local folder to import markdown, text, and PDF files into Memovi."
          />
        ) : null}

        <ul className="connector-folder-list">
          {folders.map((folder) => (
            <li key={folder.id} className="connector-folder-item">
              <div className="connector-folder-header">
                <div>
                  <strong>{folder.display_name}</strong>
                  <p className="muted connector-folder-path">
                    <Tooltip content={folder.root_path}>
                      <span title={folder.root_path}>
                        {folderDisplayName(folder.root_path)}
                      </span>
                    </Tooltip>
                  </p>
                </div>
                <StatusBadge
                  label={folder.sync_status}
                  tone={syncStatusTone(folder.sync_status)}
                />
              </div>
              <dl className="meta-grid connector-folder-meta">
                <div className="meta-card">
                  <dt>Last sync</dt>
                  <dd>{formatTimestamp(folder.last_synchronized_at)}</dd>
                </div>
                <div className="meta-card">
                  <dt>Imported documents</dt>
                  <dd>{folder.imported_document_count}</dd>
                </div>
                <div className="meta-card">
                  <dt>Error</dt>
                  <dd>{folder.last_error || "—"}</dd>
                </div>
              </dl>
              <div className="document-detail-actions">
                <Button
                  onClick={() => void handleSync(folder)}
                  disabled={syncingId === folder.id}
                >
                  {syncingId === folder.id ? "Syncing…" : "Sync now"}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setPendingRemove(folder)}
                  disabled={syncingId === folder.id}
                >
                  Remove
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {pendingRemove ? (
        <ConfirmDialog
          title="Remove folder?"
          description={`Disconnect “${pendingRemove.display_name}”? Already imported documents remain in Documents until you delete them.`}
          confirmLabel="Remove"
          tone="danger"
          busy={isRemoving}
          onCancel={() => setPendingRemove(null)}
          onConfirm={() => void handleRemove()}
        />
      ) : null}
    </div>
  );
}
