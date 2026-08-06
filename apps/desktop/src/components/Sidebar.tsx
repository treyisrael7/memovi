import { PAGES } from "../navigation/pages";
import { useAppState } from "../state/AppStateContext";
import { NavigationItem } from "./ui/NavigationItem";
import { SidebarLayout } from "./ui/SidebarLayout";
import { Toggle } from "./ui/Toggle";

export function Sidebar() {
  const { activePage, setActivePage, theme, setTheme } = useAppState();

  return (
    <SidebarLayout
      brand={
        <>
          <span className="brand-name">Memovi</span>
          <span className="brand-tag">Knowledge OS</span>
        </>
      }
      footer={
        <Toggle
          label={theme === "light" ? "Light theme" : "Dark theme"}
          checked={theme === "dark"}
          onCheckedChange={(dark) => setTheme(dark ? "dark" : "light")}
          className="theme-toggle-switch"
        />
      }
    >
      <nav className="nav" aria-label="Primary">
        {PAGES.map((page) => (
          <NavigationItem
            key={page.id}
            label={page.label}
            active={activePage === page.id}
            onClick={() => setActivePage(page.id)}
          />
        ))}
      </nav>
    </SidebarLayout>
  );
}
