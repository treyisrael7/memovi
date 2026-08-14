import { useEffect, useState } from "react";

import { API_BASE_URL } from "../api/config";
import { listFilesystemFolders } from "../api/connectors";
import { listConversations } from "../api/conversations";
import { listDocuments } from "../api/documents";
import { useAppState } from "../state/AppStateContext";
import {
  buildGettingStartedChecklist,
  describeProviderSetup,
  nextGettingStartedAction,
  type GettingStartedSnapshot,
} from "./gettingStarted";
import { ProviderSetupCard } from "./ProviderSetupGuidance";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";
import { PageLayout } from "./ui/PageLayout";
import { SectionHeader } from "./ui/SectionHeader";

const EMPTY_SNAPSHOT: GettingStartedSnapshot = {
  folderCount: 0,
  documentCount: 0,
  conversationCount: 0,
  askedQuestion: false,
};

function ConnectionBanner() {
  const { connection } = useAppState();

  if (connection.status === "checking") {
    return <Alert tone="info">Checking backend availability…</Alert>;
  }

  if (connection.status === "disconnected") {
    return (
      <Alert tone="bad">
        {connection.error ??
          "Backend is unavailable. Start the API with `task backend`."}
      </Alert>
    );
  }

  if (connection.status === "degraded") {
    return (
      <Alert tone="warn">
        {connection.error ?? "Backend is reachable but not fully ready."}
      </Alert>
    );
  }

  return <Alert tone="ok">Connected to Memovi</Alert>;
}

export function HomePage() {
  const {
    connection,
    authStatus,
    activeWorkspace,
    availableModels,
    activeModelLabel,
    setActivePage,
    openSettings,
  } = useAppState();
  const [snapshot, setSnapshot] =
    useState<GettingStartedSnapshot>(EMPTY_SNAPSHOT);
  const [snapshotError, setSnapshotError] = useState<string | null>(null);

  useEffect(() => {
    const workspaceId = activeWorkspace?.id;
    if (!workspaceId) {
      setSnapshot(EMPTY_SNAPSHOT);
      return;
    }
    if (connection.status !== "connected" && connection.status !== "degraded") {
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        const [folders, documents, conversations] = await Promise.all([
          listFilesystemFolders(workspaceId),
          listDocuments(workspaceId),
          listConversations(workspaceId),
        ]);
        if (cancelled) {
          return;
        }
        const conversationList = conversations.conversations ?? [];
        setSnapshot({
          folderCount: folders.items?.length ?? folders.count ?? 0,
          documentCount: documents.items?.length ?? 0,
          conversationCount: conversationList.length,
          askedQuestion: conversationList.some(
            (item) => (item.message_count ?? 0) > 0,
          ),
        });
        setSnapshotError(null);
      } catch {
        if (!cancelled) {
          setSnapshotError(
            "Some getting-started progress could not be loaded yet.",
          );
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [activeWorkspace?.id, connection.status]);

  const checklist = buildGettingStartedChecklist({
    connection,
    authStatus,
    availableModels,
    snapshot,
  });
  const nextAction = nextGettingStartedAction(checklist);
  const providerSetup = describeProviderSetup({
    connectionStatus: connection.status,
    models: availableModels,
  });
  const completedCount = checklist.filter((item) => item.done).length;

  return (
    <PageLayout
      title="Welcome to Memovi"
      description="Memovi turns folders and documents into searchable knowledge you can ask about. Start with the checklist below."
    >
      {providerSetup.kind === "none" ? (
        <ProviderSetupCard
          kind="none"
          title={providerSetup.title}
          description={providerSetup.description}
          onOpenDiagnostics={() => openSettings("diagnostics")}
          onViewInstructions={() => openSettings("diagnostics")}
        />
      ) : null}

      {providerSetup.kind === "fake_only" ? (
        <ProviderSetupCard
          kind="fake_only"
          title="Connect an AI provider"
          description="Memovi is running, but only the built-in demo model is available."
          onOpenDiagnostics={() => openSettings("diagnostics")}
          onViewInstructions={() => openSettings("diagnostics")}
        />
      ) : null}

      <section
        className="home-getting-started"
        aria-labelledby="getting-started-heading"
      >
        <SectionHeader
          id="getting-started-heading"
          title="Getting started"
          description={`${completedCount} of ${checklist.length} complete`}
          level={2}
        />
        {snapshotError ? <Alert tone="warn">{snapshotError}</Alert> : null}
        <ul className="home-checklist">
          {checklist.map((item) => (
            <li
              key={item.id}
              className="home-checklist-item"
              data-done={item.done ? "true" : "false"}
            >
              <span className="home-checklist-mark" aria-hidden="true">
                {item.done ? "✓" : "○"}
              </span>
              <span className="home-checklist-label">{item.label}</span>
              {!item.done && nextAction?.id === item.id ? (
                <Button
                  variant="secondary"
                  className="home-checklist-action"
                  onClick={() => {
                    if (item.settingsSection) {
                      openSettings(item.settingsSection);
                      return;
                    }
                    setActivePage(item.page);
                  }}
                >
                  Continue
                </Button>
              ) : null}
            </li>
          ))}
        </ul>

        {nextAction ? (
          <div className="home-actions">
            <Button
              onClick={() => {
                if (nextAction.settingsSection) {
                  openSettings(nextAction.settingsSection);
                  return;
                }
                setActivePage(nextAction.page);
              }}
            >
              {nextAction.id === "ai_provider"
                ? "Open Diagnostics"
                : nextAction.id === "folder"
                  ? "Add a folder"
                  : nextAction.id === "documents"
                    ? "Upload documents"
                    : nextAction.id === "question"
                      ? "Ask a question"
                      : "Continue"}
            </Button>
            <Button variant="secondary" onClick={() => setActivePage("chat")}>
              Go to Conversations
            </Button>
          </div>
        ) : (
          <div className="home-actions">
            <Alert tone="ok">
              You are set up. Search your knowledge or keep asking questions in
              Conversations.
            </Alert>
            <Button onClick={() => setActivePage("chat")}>
              Open Conversations
            </Button>
            <Button variant="secondary" onClick={() => setActivePage("search")}>
              Search knowledge
            </Button>
          </div>
        )}
      </section>

      <section className="home-next-steps" aria-label="What you can do">
        <SectionHeader
          title="What Memovi helps you do"
          description="Import once, then search and ask across everything you have connected."
          level={2}
        />
        <div className="home-path-grid">
          <button
            type="button"
            className="home-path-card"
            onClick={() => setActivePage("connectors")}
          >
            <strong>Connect a folder</strong>
            <span>Sync local files into Documents automatically.</span>
          </button>
          <button
            type="button"
            className="home-path-card"
            onClick={() => setActivePage("documents")}
          >
            <strong>Upload documents</strong>
            <span>Bring in PDFs, Markdown, and text for processing.</span>
          </button>
          <button
            type="button"
            className="home-path-card"
            onClick={() => setActivePage("chat")}
          >
            <strong>Ask a question</strong>
            <span>Chat with answers grounded in your knowledge.</span>
          </button>
        </div>
      </section>

      <section className="home-diagnostics" aria-label="Diagnostics">
        <SectionHeader
          title="Diagnostics"
          description="Connection details for troubleshooting. Most days you can ignore this section."
          level={2}
        />
        <ConnectionBanner />
        <dl className="meta-grid">
          <div className="meta-card">
            <dt>Connection</dt>
            <dd>{connection.status}</dd>
          </div>
          <div className="meta-card">
            <dt>Active workspace</dt>
            <dd>{activeWorkspace?.name ?? "—"}</dd>
          </div>
          <div className="meta-card">
            <dt>Active model</dt>
            <dd>{activeModelLabel}</dd>
          </div>
          <div className="meta-card">
            <dt>API base</dt>
            <dd>{API_BASE_URL}</dd>
          </div>
        </dl>
        <Button variant="secondary" onClick={() => openSettings("diagnostics")}>
          Open Diagnostics
        </Button>
      </section>
    </PageLayout>
  );
}
