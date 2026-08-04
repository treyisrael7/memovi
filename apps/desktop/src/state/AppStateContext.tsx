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
  CONNECTION_POLL_INTERVAL_MS,
  DEFAULT_WORKSPACE_ID,
} from "../api/config";
import { listModels } from "../api/conversations";
import { probeBackendConnection, type ConnectionSnapshot } from "../api/health";
import type { AvailableModel } from "../api/types";
import { listWorkspaces, resolveActiveWorkspace } from "../api/workspaces";
import { getPage, type PageId } from "../navigation/pages";

export type ThemeMode = "light" | "dark";

export interface ActiveWorkspace {
  id: string;
  name: string;
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

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [connection, setConnection] =
    useState<ConnectionSnapshot>(initialConnection);
  const [activeWorkspace, setActiveWorkspace] =
    useState<ActiveWorkspace | null>(null);
  const [workspaces, setWorkspaces] = useState<ActiveWorkspace[]>([]);
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([]);
  const [activeModel, setActiveModelState] =
    useState<ActiveModelSelection | null>(null);
  const [activePage, setActivePage] = useState<PageId>("chat");
  const [theme, setThemeState] = useState<ThemeMode>("light");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [chatSeed, setChatSeed] = useState<ChatSeed | null>(null);
  const chatSeedNonce = useRef(0);
  const [knowledgeSeed, setKnowledgeSeed] = useState<KnowledgeSeed | null>(
    null,
  );
  const knowledgeSeedNonce = useRef(0);
  const [documentSeed, setDocumentSeed] = useState<DocumentSeed | null>(null);
  const documentSeedNonce = useRef(0);

  const refreshWorkspaces = useCallback(async () => {
    try {
      const listed = await listWorkspaces();
      const mapped = listed.map((workspace) => ({
        id: workspace.id,
        name: workspace.name,
      }));
      setWorkspaces(mapped);
      setActiveWorkspace((current) => {
        if (current && mapped.some((item) => item.id === current.id)) {
          return current;
        }
        const resolved = resolveActiveWorkspace(listed);
        return resolved
          ? { id: resolved.id, name: resolved.name }
          : {
              id: DEFAULT_WORKSPACE_ID,
              name: "Default Workspace",
            };
      });
    } catch {
      setWorkspaces([]);
      setActiveWorkspace({
        id: DEFAULT_WORKSPACE_ID,
        name: "Default Workspace",
      });
    }
  }, []);

  const refreshConnection = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const snapshot = await probeBackendConnection();
      setConnection(snapshot);

      if (snapshot.status === "connected" || snapshot.status === "degraded") {
        await refreshWorkspaces();

        try {
          const models = await listModels();
          setAvailableModels(models.models);
          setActiveModelState((current) => {
            if (
              current &&
              models.models.some(
                (item) =>
                  item.provider === current.provider &&
                  item.model === current.model,
              )
            ) {
              return current;
            }
            const fallback =
              models.models.find(
                (item) =>
                  item.provider === models.default_provider &&
                  item.model === models.default_model,
              ) ?? models.models[0];
            return fallback
              ? {
                  provider: fallback.provider,
                  model: fallback.model,
                  label: fallback.label,
                }
              : null;
          });
        } catch {
          setAvailableModels([]);
        }
      } else {
        setActiveWorkspace(null);
        setWorkspaces([]);
        setAvailableModels([]);
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [refreshWorkspaces]);

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
      startConversationAbout,
      clearChatSeed,
      openKnowledgeItem,
      clearKnowledgeSeed,
      openDocument,
      clearDocumentSeed,
    }),
    [
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
