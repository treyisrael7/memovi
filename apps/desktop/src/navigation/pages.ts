/**
 * Navigation registry for the desktop shell.
 * Every entry here is a real, working product surface — unfinished
 * functionality stays out of the registry rather than being advertised
 * as a placeholder.
 */
export type PageId =
  | "home"
  | "chat"
  | "documents"
  | "connectors"
  | "knowledge"
  | "collections"
  | "search"
  | "workflows"
  | "activity"
  | "settings";

export interface PageDefinition {
  id: PageId;
  label: string;
  description: string;
}

export const PAGES: readonly PageDefinition[] = [
  {
    id: "home",
    label: "Home",
    description: "Application shell overview and connection status.",
  },
  {
    id: "chat",
    label: "Conversations",
    description: "Ask questions grounded in your knowledge.",
  },
  {
    id: "documents",
    label: "Documents",
    description: "Import documents and track processing into knowledge.",
  },
  {
    id: "connectors",
    label: "Connectors",
    description: "Connect local folders and sync them into Documents.",
  },
  {
    id: "knowledge",
    label: "Knowledge",
    description: "Explore what Memovi knows, its provenance, and connections.",
  },
  {
    id: "collections",
    label: "Collections",
    description: "Organize knowledge into flat, searchable groups.",
  },
  {
    id: "search",
    label: "Search",
    description: "Search documents and extracted knowledge.",
  },
  {
    id: "workflows",
    label: "Workflows",
    description:
      "Reusable capability workflows: library, run, progress, and history.",
  },
  {
    id: "activity",
    label: "Activity",
    description: "A timeline of ingestion, knowledge, and capability events.",
  },
  {
    id: "settings",
    label: "Settings",
    description: "Model, workspace, capability, and appearance preferences.",
  },
] as const;

export function getPage(id: PageId): PageDefinition {
  const page = PAGES.find((entry) => entry.id === id);
  if (!page) {
    throw new Error(`Unknown page: ${id}`);
  }
  return page;
}
