import { describe, expect, it } from "vitest";

import type { ConnectionSnapshot } from "../api/health";
import type { AvailableModel } from "../api/types";
import {
  buildGettingStartedChecklist,
  connectedProviderStatusLabel,
  describeProviderSetup,
  nextGettingStartedAction,
  OPENAI_BACKEND_ENV_INSTRUCTIONS,
  PROVIDER_SETUP_RESTART_NOTE,
  PROVIDER_SETUP_STEPS,
} from "./gettingStarted";

const connected: ConnectionSnapshot = {
  status: "connected",
  healthOk: true,
  readyOk: true,
  environment: "local",
  components: [],
  error: null,
  lastCheckedAt: new Date().toISOString(),
};

const disconnected: ConnectionSnapshot = {
  ...connected,
  status: "disconnected",
  healthOk: false,
  readyOk: false,
  error: "Cannot reach the Memovi backend.",
};

const fakeModels: AvailableModel[] = [
  { provider: "fake", model: "fake-model", label: "Fake Model" },
];

const realModels: AvailableModel[] = [
  { provider: "openai", model: "gpt-4o-mini", label: "GPT-4o mini" },
];

describe("gettingStarted", () => {
  it("distinguishes backend unavailable from fake-only and ready providers", () => {
    expect(
      describeProviderSetup({
        connectionStatus: "disconnected",
        models: fakeModels,
      }).kind,
    ).toBe("backend_unavailable");
    expect(
      describeProviderSetup({
        connectionStatus: "checking",
        models: [],
      }).kind,
    ).toBe("backend_unavailable");
    expect(
      describeProviderSetup({
        connectionStatus: "connected",
        models: [],
      }).kind,
    ).toBe("none");
    expect(
      describeProviderSetup({
        connectionStatus: "connected",
        models: fakeModels,
      }).kind,
    ).toBe("fake_only");
    expect(
      describeProviderSetup({
        connectionStatus: "connected",
        models: realModels,
      }).kind,
    ).toBe("ready");
  });

  it("does not treat a disconnected backend as an unconfigured provider", () => {
    const guidance = describeProviderSetup({
      connectionStatus: "disconnected",
      models: fakeModels,
    });
    expect(guidance.title).not.toMatch(/not configured/i);
    expect(guidance.description).toMatch(/API is running/i);
  });

  it("removes the fake-only warning when a non-fake model is registered", () => {
    const fake = describeProviderSetup({
      connectionStatus: "connected",
      models: fakeModels,
    });
    const ready = describeProviderSetup({
      connectionStatus: "connected",
      models: realModels,
    });
    expect(fake.kind).toBe("fake_only");
    expect(ready.kind).toBe("ready");
    expect(connectedProviderStatusLabel(fakeModels)).toBeNull();
    expect(connectedProviderStatusLabel(realModels)).toBe("OpenAI connected");
  });

  it("never includes secret values in setup instructions", () => {
    const blob = [
      ...PROVIDER_SETUP_STEPS,
      OPENAI_BACKEND_ENV_INSTRUCTIONS,
      PROVIDER_SETUP_RESTART_NOTE,
      describeProviderSetup({
        connectionStatus: "connected",
        models: fakeModels,
      }).description,
    ].join("\n");
    expect(blob).toContain("OPENAI_API_KEY=<your key>");
    expect(blob).toContain("INTELLIGENCE_PROVIDER=openai");
    expect(blob).not.toMatch(/sk-/);
    expect(blob).not.toMatch(/OPENAI_API_KEY=\s*[A-Za-z0-9]/);
  });

  it("builds a checklist from existing app signals", () => {
    const items = buildGettingStartedChecklist({
      connection: connected,
      authStatus: "authenticated",
      availableModels: fakeModels,
      snapshot: {
        folderCount: 0,
        documentCount: 1,
        conversationCount: 0,
        askedQuestion: false,
      },
    });

    expect(items.find((item) => item.id === "connected")?.done).toBe(true);
    expect(items.find((item) => item.id === "signed_in")?.done).toBe(true);
    expect(items.find((item) => item.id === "ai_provider")?.done).toBe(false);
    expect(
      items.find((item) => item.id === "ai_provider")?.settingsSection,
    ).toBe("diagnostics");
    expect(items.find((item) => item.id === "folder")?.done).toBe(false);
    expect(items.find((item) => item.id === "documents")?.done).toBe(true);
    expect(items.find((item) => item.id === "question")?.done).toBe(false);
    expect(nextGettingStartedAction(items)?.id).toBe("ai_provider");
  });

  it("does not mark the provider step done while the backend is down", () => {
    const items = buildGettingStartedChecklist({
      connection: disconnected,
      authStatus: "authenticated",
      availableModels: fakeModels,
      snapshot: {
        folderCount: 0,
        documentCount: 0,
        conversationCount: 0,
        askedQuestion: false,
      },
    });
    expect(nextGettingStartedAction(items)?.id).toBe("connected");
    expect(items.find((item) => item.id === "ai_provider")?.done).toBe(false);
  });
});
