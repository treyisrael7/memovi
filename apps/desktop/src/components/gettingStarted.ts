import type { AvailableModel } from "../api/types";
import type { PageId } from "../navigation/pages";
import type { AuthStatus } from "../state/AppStateContext";
import type { ConnectionSnapshot } from "../api/health";

export interface GettingStartedItem {
  id: string;
  label: string;
  done: boolean;
  /** Primary navigation target when this step is the next action. */
  page: PageId;
}

export interface GettingStartedSnapshot {
  folderCount: number;
  documentCount: number;
  conversationCount: number;
  askedQuestion: boolean;
}

export function isRealAiProvider(provider: string): boolean {
  return provider.trim().toLowerCase() !== "fake";
}

export function hasConfiguredAiProvider(models: AvailableModel[]): boolean {
  return models.some((model) => isRealAiProvider(model.provider));
}

export function describeModelAvailability(models: AvailableModel[]): {
  kind: "ready" | "fake_only" | "none";
  title: string;
  description: string;
} {
  if (models.length === 0) {
    return {
      kind: "none",
      title: "No AI models available",
      description:
        "Memovi could not load a language model. This usually means no intelligence provider is configured, the backend is still using an incomplete setup, or an API key such as OPENAI_API_KEY is missing. Open Settings to review the active model and diagnostics.",
    };
  }

  if (!hasConfiguredAiProvider(models)) {
    return {
      kind: "fake_only",
      title: "Using the local fake provider",
      description:
        "Conversations will run against Memovi’s built-in fake model. Configure a real provider (for example OpenAI via OPENAI_API_KEY and INTELLIGENCE_PROVIDER) on the backend, then refresh connection from Settings.",
    };
  }

  return {
    kind: "ready",
    title: "AI provider ready",
    description: "A configured language model is available for conversations.",
  };
}

export function buildGettingStartedChecklist(input: {
  connection: ConnectionSnapshot;
  authStatus: AuthStatus;
  availableModels: AvailableModel[];
  snapshot: GettingStartedSnapshot;
}): GettingStartedItem[] {
  const connected =
    input.connection.status === "connected" ||
    input.connection.status === "degraded";
  const signedIn = input.authStatus === "authenticated";

  return [
    {
      id: "connected",
      label: "Connected to backend",
      done: connected,
      page: "home",
    },
    {
      id: "signed_in",
      label: "Signed in",
      done: signedIn,
      page: "settings",
    },
    {
      id: "ai_provider",
      label: "Configure an AI provider",
      done: hasConfiguredAiProvider(input.availableModels),
      page: "settings",
    },
    {
      id: "folder",
      label: "Add a folder",
      done: input.snapshot.folderCount > 0,
      page: "connectors",
    },
    {
      id: "documents",
      label: "Upload documents",
      done: input.snapshot.documentCount > 0,
      page: "documents",
    },
    {
      id: "question",
      label: "Ask your first question",
      done: input.snapshot.askedQuestion,
      page: "chat",
    },
  ];
}

export function nextGettingStartedAction(
  items: GettingStartedItem[],
): GettingStartedItem | null {
  return items.find((item) => !item.done) ?? null;
}
