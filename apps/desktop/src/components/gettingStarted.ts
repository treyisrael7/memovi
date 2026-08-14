import type { ConnectionSnapshot, ConnectionStatus } from "../api/health";
import type { AvailableModel } from "../api/types";
import type { PageId, SettingsSectionId } from "../navigation/pages";
import type { AuthStatus } from "../state/AppStateContext";

export interface GettingStartedItem {
  id: string;
  label: string;
  done: boolean;
  /** Primary navigation target when this step is the next action. */
  page: PageId;
  settingsSection?: SettingsSectionId;
}

export interface GettingStartedSnapshot {
  folderCount: number;
  documentCount: number;
  conversationCount: number;
  askedQuestion: boolean;
}

export type ProviderSetupKind =
  "backend_unavailable" | "none" | "fake_only" | "ready";

export interface ProviderSetupGuidance {
  kind: ProviderSetupKind;
  title: string;
  description: string;
}

export const PROVIDER_SETUP_STEPS = [
  "Add your OpenAI API key to the backend environment.",
  "Set INTELLIGENCE_PROVIDER=openai.",
  "Restart the Memovi API.",
  "Return here and recheck.",
] as const;

export const OPENAI_BACKEND_ENV_INSTRUCTIONS = [
  "OPENAI_API_KEY=<your key>",
  "INTELLIGENCE_PROVIDER=openai",
].join("\n");

export const PROVIDER_SETUP_RESTART_NOTE =
  "Restart the Memovi API after changing these values.";

export function isRealAiProvider(provider: string): boolean {
  return provider.trim().toLowerCase() !== "fake";
}

export function hasConfiguredAiProvider(models: AvailableModel[]): boolean {
  return models.some((model) => isRealAiProvider(model.provider));
}

export function connectedProviderStatusLabel(
  models: AvailableModel[],
): string | null {
  if (!hasConfiguredAiProvider(models)) {
    return null;
  }
  const hasOpenAi = models.some(
    (model) => model.provider.trim().toLowerCase() === "openai",
  );
  return hasOpenAi ? "OpenAI connected" : "AI provider connected";
}

export function isBackendReachable(status: ConnectionStatus): boolean {
  return status === "connected" || status === "degraded";
}

export function describeProviderSetup(input: {
  connectionStatus: ConnectionStatus;
  models: AvailableModel[];
}): ProviderSetupGuidance {
  if (!isBackendReachable(input.connectionStatus)) {
    return {
      kind: "backend_unavailable",
      title: "Backend unavailable",
      description:
        "Memovi cannot check AI providers until the API is running. Start it with `task backend`, then recheck.",
    };
  }

  if (input.models.length === 0) {
    return {
      kind: "none",
      title: "No AI models available",
      description:
        "Memovi could not load a language model. Open Diagnostics to review the backend, then configure OpenAI in the API environment if needed.",
    };
  }

  if (!hasConfiguredAiProvider(input.models)) {
    return {
      kind: "fake_only",
      title: "AI provider not configured",
      description:
        "Memovi is currently using its built-in demo model. To use a real AI provider, configure OpenAI on the backend.",
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
  const connected = isBackendReachable(input.connection.status);
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
      done: connected && hasConfiguredAiProvider(input.availableModels),
      page: "settings",
      settingsSection: "diagnostics",
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
