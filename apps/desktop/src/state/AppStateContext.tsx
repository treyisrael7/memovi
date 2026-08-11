import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
  type AuthCredentials,
  type AuthUser,
} from "../api/auth";
import { onUnauthorized } from "../api/authEvents";
import { ApiRequestError } from "../api/client";
import {
  CONNECTION_POLL_INTERVAL_MS,
  DEFAULT_WORKSPACE_ID,
} from "../api/config";
import { listModels } from "../api/conversations";
import { probeBackendConnection, type ConnectionSnapshot } from "../api/health";
import type { AvailableModel } from "../api/types";
import { listWorkspaces, resolveActiveWorkspace } from "../api/workspaces";
import { getPage, type PageId } from "../navigation/pages";
import {
  readStoredModel,
  readStoredPage,
  readStoredTheme,
  readStoredWorkspaceId,
  writeStoredModel,
  writeStoredPage,
  writeStoredTheme,
  writeStoredWorkspaceId,
  type ThemeMode,
} from "./sessionPreferences";

export type { ThemeMode };
export type AuthStatus =
  | "checking"
  | "authenticated"
  | "anonymous"
  | "session_expired";

export interface ActiveWorkspace {
  id: string;
  name: string;
  role?: string | null;
}

export interface ActiveModelSelection {
  provider: string;
  model: string;
  label: string;
}

export interface ChatSeed {
  conversationId: string;
  draft: string;
  nonce: number;
}

export interface KnowledgeSeed {
  knowledgeItemId: string;
  nonce: number;
}

export interface DocumentSeed {
  documentId: string;
  nonce: number;
}

interface AppStateValue {
  authStatus: AuthStatus;
  user: AuthUser | null;
  connection: ConnectionSnapshot;
  activeWorkspace: ActiveWorkspace | null;
  workspaces: ActiveWorkspace[];
  availableModels: AvailableModel[];
  activeModel: ActiveModelSelection | null;
  activeModelLabel: string;
  activePage: PageId;
  theme: ThemeMode;
  isRefreshing: boolean;
  chatSeed: ChatSeed | null;
  knowledgeSeed: KnowledgeSeed | null;
  documentSeed: DocumentSeed | null;
  setActivePage: (page: PageId) => void;
  setTheme: (theme: ThemeMode) => void;
  setActiveWorkspaceId: (workspaceId: string) => void;
  setActiveModel: (selection: ActiveModelSelection) => void;
  refreshConnection: () => Promise<void>;
  refreshWorkspaces: () => Promise<void>;
  login: (credentials: AuthCredentials) => Promise<void>;
  register: (credentials: AuthCredentials) => Promise<void>;
  logout: () => Promise<void>;
  acknowledgeSessionExpired: () => void;
  /** Opens Chat with a new conversation prefilled to ground it in a document/knowledge item. */
  startConversationAbout: (conversationId: string, draft: string) => void;
  clearChatSeed: () => void;
  /** Opens Knowledge with the given entity selected. */
  openKnowledgeItem: (knowledgeItemId: string) => void;
  clearKnowledgeSeed: () => void;
  /** Opens Documents with the given document selected. */
  openDocument: (documentId: string) => void;
  clearDocumentSeed: () => void;
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

function clearSessionScopedState(setters: {
  setActiveWorkspace: (value: ActiveWorkspace | null) => void;
  setWorkspaces: (value: ActiveWorkspace[]) => void;
  setAvailableModels: (value: AvailableModel[]) => void;
  setActiveModelState: (value: ActiveModelSelection | null) => void;
  setChatSeed: (value: ChatSeed | null) => void;
  setKnowledgeSeed: (value: KnowledgeSeed | null) => void;
  setDocumentSeed: (value: DocumentSeed | null) => void;
}): void {
  setters.setActiveWorkspace(null);
  setters.setWorkspaces([]);
  setters.setAvailableModels([]);
  setters.setActiveModelState(null);
  setters.setChatSeed(null);
  setters.setKnowledgeSeed(null);
  setters.setDocumentSeed(null);
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [authStatus, setAuthStatus] = useState<AuthStatus>("checking");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [connection, setConnection] =
    useState<ConnectionSnapshot>(initialConnection);
  const [activeWorkspace, setActiveWorkspace] =
    useState<ActiveWorkspace | null>(null);
  const [workspaces, setWorkspaces] = useState<ActiveWorkspace[]>([]);
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([]);
  const [activeModel, setActiveModelState] =
    useState<ActiveModelSelection | null>(null);
  const [activePage, setActivePage] = useState<PageId>("home");
  const [theme, setThemeState] = useState<ThemeMode>(() => readStoredTheme());
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [chatSeed, setChatSeed] = useState<ChatSeed | null>(null);
  const chatSeedNonce = useRef(0);
  const [knowledgeSeed, setKnowledgeSeed] = useState<KnowledgeSeed | null>(
    null,
  );
  const knowledgeSeedNonce = useRef(0);
  const [documentSeed, setDocumentSeed] = useState<DocumentSeed | null>(null);
  const documentSeedNonce = useRef(0);
  const authStatusRef = useRef(authStatus);
  authStatusRef.current = authStatus;

  const applyAuthenticatedUser = useCallback((nextUser: AuthUser) => {
    setUser(nextUser);
    setAuthStatus("authenticated");
    const storedPage = readStoredPage(nextUser.id);
    if (storedPage) {
      setActivePage(storedPage);
    }
  }, []);

  const refreshWorkspaces = useCallback(async () => {
    try {
      const listed = await listWorkspaces();
      const mapped = listed.map((workspace) => ({
        id: workspace.id,
        name: workspace.name,
        role: workspace.role ?? null,
      }));
      setWorkspaces(mapped);
      setActiveWorkspace((current) => {
        const preferredId =
          current?.id ??
          (user ? readStoredWorkspaceId(user.id) : null) ??
          null;
        if (preferredId && mapped.some((item) => item.id === preferredId)) {
          const match = mapped.find((item) => item.id === preferredId)!;
          return match;
        }
        const resolved = resolveActiveWorkspace(listed);
        return resolved
          ? {
              id: resolved.id,
              name: resolved.name,
              role: resolved.role ?? null,
            }
          : {
              id: DEFAULT_WORKSPACE_ID,
              name: "Default Workspace",
              role: null,
            };
      });
    } catch (error) {
      if (error instanceof ApiRequestError && error.status === 401) {
        return;
      }
      setWorkspaces([]);
      setActiveWorkspace({
        id: DEFAULT_WORKSPACE_ID,
        name: "Default Workspace",
        role: null,
      });
    }
  }, [user]);

  const refreshConnection = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const snapshot = await probeBackendConnection();
      setConnection(snapshot);

      const isAuthenticated = authStatusRef.current === "authenticated";
      if (
        isAuthenticated &&
        (snapshot.status === "connected" || snapshot.status === "degraded")
      ) {
        await refreshWorkspaces();

        try {
          const models = await listModels();
          setAvailableModels(models.models);
          setActiveModelState((current) => {
            const findModel = (provider: string, model: string) =>
              models.models.find(
                (item) => item.provider === provider && item.model === model,
              );

            if (current) {
              const existing = findModel(current.provider, current.model);
              if (existing) {
                return {
                  provider: existing.provider,
                  model: existing.model,
                  label: existing.label,
                };
              }
            }

            const stored = user ? readStoredModel(user.id) : null;
            if (stored) {
              const fromStore = findModel(stored.provider, stored.model);
              if (fromStore) {
                return {
                  provider: fromStore.provider,
                  model: fromStore.model,
                  label: fromStore.label,
                };
              }
            }

            const fallback =
              findModel(models.default_provider, models.default_model) ??
              models.models[0];
            return fallback
              ? {
                  provider: fallback.provider,
                  model: fallback.model,
                  label: fallback.label,
                }
              : null;
          });
        } catch (error) {
          if (!(error instanceof ApiRequestError && error.status === 401)) {
            setAvailableModels([]);
          }
        }
      } else if (!isAuthenticated) {
        setActiveWorkspace(null);
        setWorkspaces([]);
        setAvailableModels([]);
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [refreshWorkspaces, user]);

  const restoreSession = useCallback(async () => {
    setAuthStatus("checking");
    try {
      const current = await getCurrentUser();
      applyAuthenticatedUser(current);
    } catch (error) {
      if (error instanceof ApiRequestError && error.status === 401) {
        setUser(null);
        setAuthStatus("anonymous");
        return;
      }
      // Backend unreachable during boot — still show auth screens so the user
      // can retry once the API is up; do not pretend a session exists.
      setUser(null);
      setAuthStatus("anonymous");
    }
  }, [applyAuthenticatedUser]);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    return onUnauthorized(() => {
      if (authStatusRef.current !== "authenticated") {
        return;
      }
      setAuthStatus("session_expired");
      setUser(null);
      clearSessionScopedState({
        setActiveWorkspace,
        setWorkspaces,
        setAvailableModels,
        setActiveModelState,
        setChatSeed,
        setKnowledgeSeed,
        setDocumentSeed,
      });
    });
  }, []);

  useEffect(() => {
    if (authStatus !== "authenticated") {
      return;
    }
    void refreshConnection();
    const timer = window.setInterval(() => {
      void refreshConnection();
    }, CONNECTION_POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [authStatus, refreshConnection]);

  useEffect(() => {
    // Still probe health while anonymous so AuthGate can show backend status.
    if (authStatus === "authenticated" || authStatus === "checking") {
      return;
    }
    void refreshConnection();
    const timer = window.setInterval(() => {
      void refreshConnection();
    }, CONNECTION_POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [authStatus, refreshConnection]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    writeStoredTheme(theme);
  }, [theme]);

  useEffect(() => {
    if (user && authStatus === "authenticated") {
      writeStoredPage(user.id, activePage);
    }
  }, [activePage, authStatus, user]);

  useEffect(() => {
    if (user && authStatus === "authenticated" && activeWorkspace) {
      writeStoredWorkspaceId(user.id, activeWorkspace.id);
    }
  }, [activeWorkspace, authStatus, user]);

  useEffect(() => {
    if (user && authStatus === "authenticated" && activeModel) {
      writeStoredModel(user.id, {
        provider: activeModel.provider,
        model: activeModel.model,
      });
    }
  }, [activeModel, authStatus, user]);

  const setTheme = useCallback((next: ThemeMode) => {
    setThemeState(next);
  }, []);

  const handleSetActivePage = useCallback((page: PageId) => {
    getPage(page);
    setActivePage(page);
  }, []);

  const setActiveWorkspaceId = useCallback(
    (workspaceId: string) => {
      const match = workspaces.find(
        (workspace) => workspace.id === workspaceId,
      );
      if (match) {
        setActiveWorkspace(match);
      }
    },
    [workspaces],
  );

  const setActiveModel = useCallback((selection: ActiveModelSelection) => {
    setActiveModelState(selection);
  }, []);

  const login = useCallback(
    async (credentials: AuthCredentials) => {
      const nextUser = await loginUser(credentials);
      applyAuthenticatedUser(nextUser);
    },
    [applyAuthenticatedUser],
  );

  const register = useCallback(
    async (credentials: AuthCredentials) => {
      const nextUser = await registerUser(credentials);
      applyAuthenticatedUser(nextUser);
    },
    [applyAuthenticatedUser],
  );

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } catch (error) {
      // Session may already be gone; still clear local authenticated state.
      if (!(error instanceof ApiRequestError && error.status === 401)) {
        throw error;
      }
    } finally {
      setUser(null);
      setAuthStatus("anonymous");
      clearSessionScopedState({
        setActiveWorkspace,
        setWorkspaces,
        setAvailableModels,
        setActiveModelState,
        setChatSeed,
        setKnowledgeSeed,
        setDocumentSeed,
      });
      setActivePage("home");
    }
  }, []);

  const acknowledgeSessionExpired = useCallback(() => {
    setAuthStatus("anonymous");
  }, []);

  const startConversationAbout = useCallback(
    (conversationId: string, draft: string) => {
      chatSeedNonce.current += 1;
      setChatSeed({ conversationId, draft, nonce: chatSeedNonce.current });
      setActivePage("chat");
    },
    [],
  );

  const clearChatSeed = useCallback(() => {
    setChatSeed(null);
  }, []);

  const openKnowledgeItem = useCallback((knowledgeItemId: string) => {
    knowledgeSeedNonce.current += 1;
    setKnowledgeSeed({ knowledgeItemId, nonce: knowledgeSeedNonce.current });
    setActivePage("knowledge");
  }, []);

  const clearKnowledgeSeed = useCallback(() => {
    setKnowledgeSeed(null);
  }, []);

  const openDocument = useCallback((documentId: string) => {
    documentSeedNonce.current += 1;
    setDocumentSeed({ documentId, nonce: documentSeedNonce.current });
    setActivePage("documents");
  }, []);

  const clearDocumentSeed = useCallback(() => {
    setDocumentSeed(null);
  }, []);

  const value = useMemo<AppStateValue>(
    () => ({
      authStatus,
      user,
      connection,
      activeWorkspace,
      workspaces,
      availableModels,
      activeModel,
      activeModelLabel: activeModel?.label ?? "No model selected",
      activePage,
      theme,
      isRefreshing,
      chatSeed,
      knowledgeSeed,
      documentSeed,
      setActivePage: handleSetActivePage,
      setTheme,
      setActiveWorkspaceId,
      setActiveModel,
      refreshConnection,
      refreshWorkspaces,
      login,
      register,
      logout,
      acknowledgeSessionExpired,
      startConversationAbout,
      clearChatSeed,
      openKnowledgeItem,
      clearKnowledgeSeed,
      openDocument,
      clearDocumentSeed,
    }),
    [
      authStatus,
      user,
      connection,
      activeWorkspace,
      workspaces,
      availableModels,
      activeModel,
      activePage,
      theme,
      isRefreshing,
      chatSeed,
      knowledgeSeed,
      documentSeed,
      handleSetActivePage,
      setTheme,
      setActiveWorkspaceId,
      setActiveModel,
      refreshConnection,
      refreshWorkspaces,
      login,
      register,
      logout,
      acknowledgeSessionExpired,
      startConversationAbout,
      clearChatSeed,
      openKnowledgeItem,
      clearKnowledgeSeed,
      openDocument,
      clearDocumentSeed,
    ],
  );

  return (
    <AppStateContext.Provider value={value}>
      {children}
    </AppStateContext.Provider>
  );
}

export function useAppState(): AppStateValue {
  const context = useContext(AppStateContext);
  if (!context) {
    throw new Error("useAppState must be used within AppStateProvider");
  }
  return context;
}
