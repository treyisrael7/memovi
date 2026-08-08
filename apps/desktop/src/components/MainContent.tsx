import { API_BASE_URL } from "../api/config";
import { getPage } from "../navigation/pages";
import { useAppState } from "../state/AppStateContext";
import { ActivityPage } from "./ActivityPage";
import { ChatPage } from "./ChatPage";
import { CollectionsPage } from "./CollectionsPage";
import { ConnectorsPage } from "./ConnectorsPage";
import { DocumentsPage } from "./DocumentsPage";
import { KnowledgeExplorerPage } from "./KnowledgeExplorerPage";
import { SearchPage } from "./SearchPage";
import { SettingsPage } from "./SettingsPage";
import { TagsPage } from "./TagsPage";
import { WorkflowsPage } from "./WorkflowsPage";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";
import { PageLayout } from "./ui/PageLayout";

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

  return <Alert tone="ok">Connected to {API_BASE_URL}</Alert>;
}

function HomePage() {
  const { connection, activeWorkspace, activeModelLabel, setActivePage } =
    useAppState();

  return (
    <PageLayout
      title="Welcome to Memovi"
      description="Import documents, let Memovi turn them into connected knowledge, then search or ask questions grounded in what it knows."
    >
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

      <div className="document-detail-actions home-actions">
        <Button onClick={() => setActivePage("documents")}>
          Import documents
        </Button>
        <Button variant="secondary" onClick={() => setActivePage("chat")}>
          Start a conversation
        </Button>
      </div>
    </PageLayout>
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
    case "collections":
      body = <CollectionsPage />;
      break;
    case "tags":
      body = <TagsPage />;
      break;
    case "workflows":
      body = <WorkflowsPage />;
      break;
    case "documents":
      body = <DocumentsPage />;
      break;
    case "connectors":
      body = <ConnectorsPage />;
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

  return <main className="content">{body}</main>;
}
