import { PAGES } from "../navigation/pages";
import { useAppState } from "../state/AppStateContext";

export function Sidebar() {
  const { activePage, setActivePage, theme, setTheme } = useAppState();

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-name">Memovi</span>
        <span className="brand-tag">Knowledge OS</span>
      </div>

      <nav className="nav" aria-label="Primary">
        {PAGES.map((page) => (
          <button
            key={page.id}
            type="button"
            className="nav-item"
            data-active={activePage === page.id}
            onClick={() => setActivePage(page.id)}
          >
            <span className="nav-label">{page.label}</span>
            {!page.available ? <span className="nav-badge">Soon</span> : null}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button
          type="button"
          className="theme-toggle"
          onClick={() => setTheme(theme === "light" ? "dark" : "light")}
        >
          Theme: {theme === "light" ? "Light" : "Dark"}
        </button>
      </div>
    </aside>
  );
}
