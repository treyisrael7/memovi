/**
 * Navigation registry for the desktop shell.
 * Future product pages register here without redesigning the shell layout.
 */
export type PageId =
  | "home"
  | "chat"
  | "documents"
  | "search"
  | "workspaces"
  | "models"
  | "activity"
  | "capabilities"
  | "settings";

export interface PageDefinition {
  id: PageId;
  label: string;
  /** When false, the shell shows a placeholder instead of a real page. */
  available: boolean;
  description: string;
}

export const PAGES: readonly PageDefinition[] = [
  {
    id: "home",
    label: "Home",
    available: true,
    description: "Application shell overview and connection status.",
  },
  {
    id: "chat",
    label: "Chat",
    available: true,
    description: "Conversation interface over the Reasoning API.",
  },
  {
    id: "documents",
    label: "Documents",
    available: false,
    description: "Document library and ingestion status.",
  },
  {
    id: "search",
    label: "Search",
    available: false,
    description: "Keyword, semantic, and hybrid retrieval.",
  },
  {
    id: "workspaces",
    label: "Workspaces",
    available: false,
    description: "Workspace selection and management.",
  },
  {
    id: "models",
    label: "Models",
    available: false,
    description: "Model provider configuration and health.",
  },
  {
    id: "activity",
    label: "Activity",
    available: false,
    description: "Background jobs and indexing activity.",
  },
  {
    id: "capabilities",
    label: "Capabilities",
    available: false,
    description: "Permissioned environment capabilities.",
  },
  {
    id: "settings",
    label: "Settings",
    available: false,
    description: "Desktop and account preferences.",
  },
] as const;

export function getPage(id: PageId): PageDefinition {
  const page = PAGES.find((entry) => entry.id === id);
  if (!page) {
    throw new Error(`Unknown page: ${id}`);
  }
  return page;
}
