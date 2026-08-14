import { describe, expect, it } from "vitest";

import {
  DOCUMENT_READY_TOAST,
  formatFailureReason,
  isProcessingInFlight,
  presentIndexedState,
  presentProcessingStatus,
  shouldPollProcessing,
} from "./processingPresentation";

describe("presentProcessingStatus", () => {
  it("maps backend statuses to user-friendly labels", () => {
    expect(presentProcessingStatus("pending").label).toBe("Received");
    expect(presentProcessingStatus("extracting").label).toBe("Processing");
    expect(presentProcessingStatus("normalizing").label).toBe("Processing");
    expect(presentProcessingStatus("completed").label).toBe("Ready");
    expect(presentProcessingStatus("failed").label).toBe("Failed");
    expect(presentProcessingStatus("cancelled").label).toBe("Cancelled");
  });

  it("explains each state in plain language without invented stages", () => {
    expect(presentProcessingStatus("pending").explanation).toMatch(
      /Memovi received this/i,
    );
    expect(presentProcessingStatus("extracting").explanation).toBe(
      "Memovi is processing this document.",
    );
    expect(presentProcessingStatus("normalizing").explanation).toBe(
      presentProcessingStatus("extracting").explanation,
    );
    expect(presentProcessingStatus("completed").explanation).toBe(
      "This is ready to search.",
    );
    expect(presentProcessingStatus("failed").explanation).toBe(
      "Processing failed.",
    );
    expect(presentProcessingStatus("failed").nextActionHint).toBe(
      "Try processing again.",
    );
  });

  it("does not invent indexing or embedding stages", () => {
    const completedWithoutKnowledge = presentProcessingStatus("completed", {
      hasKnowledge: false,
      hasModel: false,
    });
    expect(completedWithoutKnowledge.label).toBe("Ready");
    expect(completedWithoutKnowledge.explanation).not.toMatch(/index/i);
    expect(completedWithoutKnowledge.explanation).not.toMatch(/embedd/i);
    expect(presentProcessingStatus("extracting").explanation).not.toMatch(
      /embedd/i,
    );
  });

  it("marks failed and cancelled as retryable attention states", () => {
    expect(presentProcessingStatus("failed").canRetry).toBe(true);
    expect(presentProcessingStatus("failed").requiresAttention).toBe(true);
    expect(presentProcessingStatus("cancelled").canRetry).toBe(true);
  });
});

describe("presentIndexedState", () => {
  it("treats document status as the source of truth for search readiness", () => {
    expect(presentIndexedState("pending", false).state).toBe("not_indexed");
    expect(presentIndexedState("completed", true).label).toBe("Ready");
    expect(presentIndexedState("completed", false).label).toBe("Ready");
    expect(presentIndexedState("completed", false).label).not.toMatch(/index/i);
    expect(presentIndexedState("failed", false).label).toBe("Failed");
  });
});

describe("polling helpers", () => {
  it("polls only while the Documents job is in flight", () => {
    expect(isProcessingInFlight("extracting")).toBe(true);
    expect(shouldPollProcessing("pending", false)).toBe(true);
    expect(shouldPollProcessing("completed", false)).toBe(false);
    expect(shouldPollProcessing("completed", true)).toBe(false);
    expect(shouldPollProcessing("failed", false)).toBe(false);
    expect(shouldPollProcessing("cancelled", false)).toBe(false);
  });
});

describe("formatFailureReason", () => {
  it("returns a short reason unchanged", () => {
    expect(formatFailureReason("Unsupported file type.")).toBe(
      "Unsupported file type.",
    );
  });

  it("does not expose stack traces", () => {
    const traceback = `Traceback (most recent call last):
  File "worker.py", line 12, in run
    raise RuntimeError("parser exploded")
RuntimeError: parser exploded`;
    expect(formatFailureReason(traceback)).toBe(
      "RuntimeError: parser exploded",
    );
    expect(formatFailureReason(traceback)).not.toMatch(/File "/);
  });
});

describe("ready toast copy", () => {
  it("uses the canonical ready message", () => {
    expect(DOCUMENT_READY_TOAST).toBe("Document ready to search.");
  });
});
