import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  CONNECTION_POLL_INTERVAL_MS,
  DEFAULT_WORKSPACE_ID,
} from "../api/config";
import {
  probeBackendConnection,
  type ConnectionSnapshot,
} from "../api/health";
import { listWorkspaces, resolveActiveWorkspace } from "../api/workspaces";
import { getPage, type PageId } from "../navigation/pages";

export type ThemeMode = "light" | "dark";

export interface ActiveWorkspace {
  id: string;
  name: string;
}

interface AppStateValue {
  connection: ConnectionSnapshot;
  activeWorkspace: ActiveWorkspace | null;
  activeModelLabel: string;
  activePage: PageId;
  theme: ThemeMode;
  isRefreshing: boolean;
  setActivePage: (page: PageId) => void;
  setTheme: (theme: ThemeMode) => void;
  refreshConnection: () => Promise<void>;
}

const initialConnection: ConnectionSnapshot = {
  status: "checking",
  healthOk: false,
  readyOk: false,
  environment: null,
  components: [],
  error: null,
  lastCheckedAt: new Date(0).toISOString(),
};

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [connection, setConnection] =
    useState<ConnectionSnapshot>(initialConnection);
  const [activeWorkspace, setActiveWorkspace] =
    useState<ActiveWorkspace | null>(null);
  const [activePage, setActivePage] = useState<PageId>("home");
  const [theme, setThemeState] = useState<ThemeMode>("light");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refreshConnection = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const snapshot = await probeBackendConnection();
      setConnection(snapshot);

      if (snapshot.status === "connected" || snapshot.status === "degraded") {
        try {
          const workspaces = await listWorkspaces();
          const resolved = resolveActiveWorkspace(workspaces);
          setActiveWorkspace(
            resolved
              ? { id: resolved.id, name: resolved.name }
              : {
                  id: DEFAULT_WORKSPACE_ID,
                  name: "Default Workspace",
                },
          );
        } catch {
          setActiveWorkspace({
            id: DEFAULT_WORKSPACE_ID,
            name: "Default Workspace",
          });
        }
      } else {
        setActiveWorkspace(null);
      }
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void refreshConnection();
    const timer = window.setInterval(() => {
      void refreshConnection();
    }, CONNECTION_POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [refreshConnection]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const setTheme = useCallback((next: ThemeMode) => {
    setThemeState(next);
  }, []);

  const handleSetActivePage = useCallback((page: PageId) => {
    // Validate against the registry so unknown ids cannot enter state.
    getPage(page);
    setActivePage(page);
  }, []);

  const value = useMemo<AppStateValue>(
    () => ({
      connection,
      activeWorkspace,
      activeModelLabel: "No model selected",
      activePage,
      theme,
      isRefreshing,
      setActivePage: handleSetActivePage,
      setTheme,
      refreshConnection,
    }),
    [
      connection,
      activeWorkspace,
      activePage,
      theme,
      isRefreshing,
      handleSetActivePage,
      setTheme,
      refreshConnection,
    ],
  );

  return (
    <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>
  );
}

export function useAppState(): AppStateValue {
  const context = useContext(AppStateContext);
  if (!context) {
    throw new Error("useAppState must be used within AppStateProvider");
  }
  return context;
}
