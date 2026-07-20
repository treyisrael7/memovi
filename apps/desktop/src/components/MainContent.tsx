import { API_BASE_URL } from "../api/config";
import { getPage } from "../navigation/pages";
import { useAppState } from "../state/AppStateContext";

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
        {connection.error ??
          "Backend is reachable but not fully ready."}
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
  const { connection, activeWorkspace, activeModelLabel } = useAppState();

  return (
    <section className="panel">
      <ConnectionBanner />
      <h1>Desktop shell</h1>
      <p className="lede">
        Memovi&apos;s flagship client is a lightweight native shell over the
        FastAPI platform. This milestone establishes window lifecycle,
        navigation, theme, and backend connection management only.
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

      {connection.components.length > 0 ? (
        <div className="components">
          <h2>Readiness components</h2>
          <ul className="component-list">
            {connection.components.map((component) => (
              <li key={component.name}>
                <span className="component-name">{component.name}</span>
                <span
                  className="component-status"
                  data-status={component.status}
                >
                  {component.status}
                  {component.detail ? ` · ${component.detail}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function PlaceholderPage({ pageId }: { pageId: ReturnType<typeof getPage>["id"] }) {
  const page = getPage(pageId);

  return (
    <section className="panel placeholder-page">
      <h1>{page.label}</h1>
      <p>{page.description}</p>
      <p>
        This page is reserved for a future product surface. The shell already
        supports navigation here without redesigning the application layout.
      </p>
    </section>
  );
}

export function MainContent() {
  const { activePage } = useAppState();
  const page = getPage(activePage);

  return (
    <main className="content">
      {page.available && page.id === "home" ? (
        <HomePage />
      ) : (
        <PlaceholderPage pageId={page.id} />
      )}
    </main>
  );
}
