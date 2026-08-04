import { API_BASE_URL } from "../api/config";
import { getPage } from "../navigation/pages";
import { useAppState } from "../state/AppStateContext";
import { ActivityPage } from "./ActivityPage";
import { ChatPage } from "./ChatPage";
import { DocumentsPage } from "./DocumentsPage";
import { KnowledgeExplorerPage } from "./KnowledgeExplorerPage";
import { SearchPage } from "./SearchPage";
import { SettingsPage } from "./SettingsPage";
import { WorkflowsPage } from "./WorkflowsPage";

function ConnectionBanner() {
  const { connection } = useAppState();

  if (connection.status === "checking") {
    return (
      <div className="banner" data-tone="ok">
        Checking backend availability…
      </div>
    );
  }

  if (connection.status === "disconnected") {
    return (
      <div className="banner" data-tone="bad" role="alert">
        {connection.error ??
          "Backend is unavailable. Start the API with `task backend`."}
      </div>
    );
  }

  if (connection.status === "degraded") {
    return (
      <div className="banner" data-tone="warn" role="status">
        {connection.error ?? "Backend is reachable but not fully ready."}
      </div>
    );
  }

  return (
    <div className="banner" data-tone="ok" role="status">
      Connected to {API_BASE_URL}
    </div>
  );
}

function HomePage() {
  const { connection, activeWorkspace, activeModelLabel, setActivePage } =
    useAppState();

  return (
    <section className="panel">
      <ConnectionBanner />
      <h1>Welcome to Memovi</h1>
      <p className="lede">
        Import documents, let Memovi turn them into connected knowledge, then
        search or ask questions grounded in what it knows.
      </p>

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

      <div className="document-detail-actions home-actions">
        <button
          type="button"
          className="primary-button"
          onClick={() => setActivePage("documents")}
        >
          Import documents
        </button>
        <button
          type="button"
          className="retry-button"
          onClick={() => setActivePage("chat")}
        >
          Start a conversation
        </button>
      </div>
    </section>
  );
}

export function MainContent() {
  const { activePage } = useAppState();
  const page = getPage(activePage);

  let body;
  switch (page.id) {
    case "chat":
      body = <ChatPage />;
      break;
    case "knowledge":
      body = <KnowledgeExplorerPage />;
      break;
    case "workflows":
      body = <WorkflowsPage />;
      break;
    case "documents":
      body = <DocumentsPage />;
      break;
    case "search":
      body = <SearchPage />;
      break;
    case "activity":
      body = <ActivityPage />;
      break;
    case "settings":
      body = <SettingsPage />;
      break;
    case "home":
    default:
      body = <HomePage />;
      break;
  }

  return (
    <main className="content" data-page={page.id}>
      {body}
    </main>
  );
}
