import { describe, expect, it } from "vitest";

import type { ConnectionSnapshot } from "../api/health";
import type { AvailableModel } from "../api/types";
import {
  buildGettingStartedChecklist,
  describeModelAvailability,
  nextGettingStartedAction,
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

const fakeModels: AvailableModel[] = [
  { provider: "fake", model: "fake-model", label: "Fake Model" },
];

const realModels: AvailableModel[] = [
  { provider: "openai", model: "gpt-4o-mini", label: "GPT-4o mini" },
];

describe("gettingStarted", () => {
  it("explains missing and fake-only model states", () => {
    expect(describeModelAvailability([]).kind).toBe("none");
    expect(describeModelAvailability(fakeModels).kind).toBe("fake_only");
    expect(describeModelAvailability(realModels).kind).toBe("ready");
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
    expect(items.find((item) => item.id === "folder")?.done).toBe(false);
    expect(items.find((item) => item.id === "documents")?.done).toBe(true);
    expect(items.find((item) => item.id === "question")?.done).toBe(false);
    expect(nextGettingStartedAction(items)?.id).toBe("ai_provider");
  });
});
