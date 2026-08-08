import { describe, expect, it } from "vitest";

import {
  isProcessingInFlight,
  presentIndexedState,
  presentProcessingStatus,
  shouldPollProcessing,
} from "./processingPresentation";

describe("presentProcessingStatus", () => {
  it("maps backend statuses to lifecycle labels", () => {
    expect(presentProcessingStatus("pending").label).toBe("Queued");
    expect(presentProcessingStatus("extracting").label).toBe("Processing");
    expect(presentProcessingStatus("normalizing").label).toBe("Chunking");
    expect(presentProcessingStatus("completed").label).toBe("Completed");
    expect(presentProcessingStatus("failed").label).toBe("Failed");
    expect(presentProcessingStatus("cancelled").label).toBe("Cancelled");
  });

  it("shows Indexing when completed but knowledge is missing", () => {
    const view = presentProcessingStatus("completed", { hasKnowledge: false });
    expect(view.label).toBe("Indexing");
    expect(view.progressPercent).toBe(85);
  });

  it("marks failed and cancelled as retryable attention states", () => {
    expect(presentProcessingStatus("failed").canRetry).toBe(true);
    expect(presentProcessingStatus("failed").requiresAttention).toBe(true);
    expect(presentProcessingStatus("cancelled").canRetry).toBe(true);
  });
});

describe("presentIndexedState", () => {
  it("distinguishes indexed vs not yet indexed", () => {
    expect(presentIndexedState("pending", false).state).toBe("not_indexed");
    expect(presentIndexedState("completed", true).label).toBe("Indexed");
    expect(presentIndexedState("completed", false).label).toBe("Indexing");
    expect(presentIndexedState("failed", false).label).toBe("Failed indexing");
  });
});

describe("polling helpers", () => {
  it("polls in-flight jobs and indexing catch-up", () => {
    expect(isProcessingInFlight("extracting")).toBe(true);
    expect(shouldPollProcessing("pending", false)).toBe(true);
    expect(shouldPollProcessing("completed", false)).toBe(true);
    expect(shouldPollProcessing("completed", true)).toBe(false);
    expect(shouldPollProcessing("failed", false)).toBe(false);
  });
});
