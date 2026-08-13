import { describe, expect, it, vi } from "vitest";

import { ApiRequestError } from "../api/client";
import type { Citation } from "../api/types";
import {
  resolveCitationDestination,
  SOURCE_UNAVAILABLE_MESSAGE,
} from "./resolveCitationDestination";

const citation: Citation = {
  document_id: "doc-1",
  chunk_id: "chunk-1",
  document_title: "Notes",
};

function lookup(overrides: {
  knowledge?: { items: Array<{ id: string }> } | Error;
  document?: unknown | Error;
}) {
  return {
    listDocumentKnowledge: vi.fn(async () => {
      if (overrides.knowledge instanceof Error) {
        throw overrides.knowledge;
      }
      return overrides.knowledge ?? { items: [] };
    }),
    getDocument: vi.fn(async () => {
      if (overrides.document instanceof Error) {
        throw overrides.document;
      }
      return overrides.document ?? { id: "doc-1" };
    }),
  };
}

describe("resolveCitationDestination", () => {
  it("opens the knowledge item when the document has materialized knowledge", async () => {
    const deps = lookup({ knowledge: { items: [{ id: "ki-1" }] } });
    await expect(
      resolveCitationDestination("ws-1", citation, deps),
    ).resolves.toEqual({ kind: "knowledge", knowledgeItemId: "ki-1" });
    expect(deps.getDocument).not.toHaveBeenCalled();
  });

  it("opens the document when knowledge is missing but the document exists", async () => {
    const deps = lookup({ knowledge: { items: [] }, document: { id: "doc-1" } });
    await expect(
      resolveCitationDestination("ws-1", citation, deps),
    ).resolves.toEqual({ kind: "document", documentId: "doc-1" });
  });

  it("falls back to search filtered to the source when neither knowledge nor document can be opened", async () => {
    const deps = lookup({
      knowledge: { items: [] },
      document: new ApiRequestError("missing", { kind: "http", status: 404 }),
    });
    await expect(
      resolveCitationDestination("ws-1", citation, deps),
    ).resolves.toEqual({
      kind: "search",
      documentId: "doc-1",
      query: "Notes",
    });
  });

  it("reports unavailable when lookups fail for a reason other than a missing document", async () => {
    const deps = lookup({
      knowledge: { items: [] },
      document: new ApiRequestError("offline", { kind: "network" }),
    });
    await expect(
      resolveCitationDestination("ws-1", citation, deps),
    ).resolves.toEqual({
      kind: "unavailable",
      message: SOURCE_UNAVAILABLE_MESSAGE,
    });
  });
});
