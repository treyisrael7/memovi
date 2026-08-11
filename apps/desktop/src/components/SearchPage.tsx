import { useEffect, useMemo, useState } from "react";

import { ApiRequestError } from "../api/client";
import { listCollections } from "../api/collections";
import { createConversation } from "../api/conversations";
import { listDocuments } from "../api/documents";
import { listKnowledge } from "../api/memory";
import { searchKnowledge, type SearchMode } from "../api/search";
import { listTags } from "../api/tags";
import type {
  CollectionListItem,
  DocumentSummary,
  SearchResultItem,
  TagListItem,
} from "../api/types";
import {
  isProcessingInFlight,
  presentIndexedState,
  presentProcessingStatus,
} from "../documents/processingPresentation";
import { useAppState } from "../state/AppStateContext";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";
import { Dropdown } from "./ui/Dropdown";
import { EmptyState } from "./ui/EmptyState";
import { LoadingState } from "./ui/LoadingState";
import { SearchInput } from "./ui/SearchInput";
import { SectionHeader } from "./ui/SectionHeader";
import { StatusBadge } from "./ui/StatusBadge";
import { Tabs } from "./ui/Tabs";
import { TagChips } from "./ui/TagChips";
import { useToast } from "./ui/ToastContext";

type SearchScope = "all" | "document" | "knowledge";

const SCOPES: ReadonlyArray<{
  id: SearchScope;
  label: string;
  mode: SearchMode;
}> = [
  { id: "all", label: "All content", mode: "hybrid" },
  { id: "document", label: "This document", mode: "keyword" },
  { id: "knowledge", label: "Knowledge", mode: "semantic" },
];

const RECENT_LIMIT = 8;

function recentSearchesKey(workspaceId: string): string {
  return `memovi.recentSearches.${workspaceId}`;
}

function loadRecentSearches(workspaceId: string): string[] {
  try {
    const raw = window.localStorage.getItem(recentSearchesKey(workspaceId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed)
      ? parsed.filter((item) => typeof item === "string")
      : [];
  } catch {
    return [];
  }
}

function saveRecentSearches(workspaceId: string, searches: string[]): void {
  try {
    window.localStorage.setItem(
      recentSearchesKey(workspaceId),
      JSON.stringify(searches.slice(0, RECENT_LIMIT)),
    );
  } catch {
    // Recent searches are a convenience; ignore storage failures.
  }
}

export function SearchPage() {
  const {
    activeWorkspace,
    connection,
    openKnowledgeItem,
    startConversationAbout,
    setActivePage,
  } = useAppState();
  const { showToast } = useToast();
  const workspaceId = activeWorkspace?.id ?? null;
  const canUseBackend =
    connection.status === "connected" || connection.status === "degraded";

  const [scope, setScope] = useState<SearchScope>("all");
  const [query, setQuery] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [collectionId, setCollectionId] = useState("");
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [knowledgeDocumentIds, setKnowledgeDocumentIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [collections, setCollections] = useState<CollectionListItem[]>([]);
  const [tags, setTags] = useState<TagListItem[]>([]);
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  const sourceById = useMemo(() => {
    const map = new Map<string, DocumentSummary>();
    for (const document of documents) {
      map.set(document.id, document);
    }
    return map;
  }, [documents]);

  const processingDocs = useMemo(
    () =>
      documents.filter((doc) => isProcessingInFlight(doc.processing_status)),
    [documents],
  );
  const failedDocs = useMemo(
    () => documents.filter((doc) => doc.processing_status === "failed"),
    [documents],
  );
  const notIndexedDocs = useMemo(
    () =>
      documents.filter((doc) => {
        const state = presentIndexedState(
          doc.processing_status,
          knowledgeDocumentIds.has(doc.id),
        );
        return state.state === "not_indexed" || state.state === "indexing";
      }),
    [documents, knowledgeDocumentIds],
  );

  const selectedDocument = documentId ? sourceById.get(documentId) : null;
  const selectedIndexed = selectedDocument
    ? presentIndexedState(
        selectedDocument.processing_status,
        knowledgeDocumentIds.has(selectedDocument.id),
      )
    : null;

  useEffect(() => {
    if (!workspaceId) {
      setDocuments([]);
      setKnowledgeDocumentIds(new Set());
      return;
    }
    setRecentSearches(loadRecentSearches(workspaceId));
    if (!canUseBackend) {
      setDocuments([]);
      setKnowledgeDocumentIds(new Set());
      return;
    }
    let cancelled = false;
    void Promise.all([
      listDocuments(workspaceId),
      listKnowledge(workspaceId).catch(() => ({ items: [], count: 0 })),
      listCollections(workspaceId),
      listTags(workspaceId).catch(() => ({ items: [], count: 0 })),
    ])
      .then(([docsPayload, knowledgePayload, collectionsPayload, tagsPayload]) => {
        if (cancelled) return;
        setDocuments(docsPayload.items);
        setKnowledgeDocumentIds(
          new Set(knowledgePayload.items.map((item) => item.document_id)),
        );
        setCollections(collectionsPayload.items);
        setTags(tagsPayload.items);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [workspaceId, canUseBackend]);

  useEffect(() => {
    if (!workspaceId || !canUseBackend) {
      setResults([]);
      return;
    }
    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      return;
    }

    let cancelled = false;
    setIsSearching(true);
    setError(null);
    const activeScope = SCOPES.find((entry) => entry.id === scope) ?? SCOPES[0];
    const handle = window.setTimeout(() => {
      void searchKnowledge(workspaceId, {
        q: trimmed,
        mode: activeScope.mode,
        documentId: scope === "document" ? documentId || undefined : undefined,
        collectionId: collectionId || undefined,
        tagIds: selectedTagIds.length > 0 ? selectedTagIds : undefined,
      })
        .then((payload) => {
          if (cancelled) return;
          setResults(payload.results);
        })
        .catch((err: unknown) => {
          if (!cancelled) {
            setError(
              err instanceof ApiRequestError ? err.message : "Search failed.",
            );
          }
        })
        .finally(() => {
          if (!cancelled) setIsSearching(false);
        });
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [
    workspaceId,
    canUseBackend,
    query,
    scope,
    documentId,
    collectionId,
    selectedTagIds,
  ]);

  function recordRecentSearch(term: string) {
    if (!workspaceId || !term.trim()) return;
    setRecentSearches((current) => {
      const next = [term, ...current.filter((item) => item !== term)].slice(
        0,
        RECENT_LIMIT,
      );
      saveRecentSearches(workspaceId, next);
      return next;
    });
  }

  function handleSubmit() {
    recordRecentSearch(query.trim());
  }

  async function handleAskAbout(result: SearchResultItem) {
    if (!workspaceId) return;
    try {
      const created = await createConversation(workspaceId);
      const documentName =
        sourceById.get(result.document_id)?.name ?? "this document";
      startConversationAbout(
        created.conversation_id,
        `Tell me more about this, from ${documentName}: "${result.text.slice(0, 200)}"`,
      );
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to start a conversation.",
        "bad",
      );
    }
  }

  const emptyDescription = (() => {
    if (
      scope === "document" &&
      selectedDocument &&
      selectedIndexed &&
      selectedIndexed.state !== "indexed"
    ) {
      return `${selectedDocument.name} is ${selectedIndexed.label.toLowerCase()}. ${selectedIndexed.detail} Open Documents to track progress or retry.`;
    }
    if (processingDocs.length > 0) {
      return `${processingDocs.length} document${processingDocs.length === 1 ? " is" : "s are"} still processing and will not appear in search until indexing completes.`;
    }
    if (failedDocs.length > 0) {
      return `${failedDocs.length} document${failedDocs.length === 1 ? " failed" : "s failed"} processing. Open Documents to retry, then search again.`;
    }
    return "Try a different query or scope. Documents that are still processing are excluded from search until they are indexed.";
  })();

  return (
    <div className="search-page">
      <div className="search-header">
        <SectionHeader title="Search" level={1} />
        <form
          className="search-input-row"
          onSubmit={(event) => {
            event.preventDefault();
            handleSubmit();
          }}
        >
          <SearchInput
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onBlur={() => handleSubmit()}
            placeholder="Search documents and knowledge…"
            autoFocus
            disabled={!canUseBackend}
          />
        </form>

        <div className="search-scope-row">
          <Tabs
            aria-label="Search scope"
            value={scope}
            onChange={(id) => setScope(id as SearchScope)}
            items={SCOPES.map((entry) => ({
              id: entry.id,
              label: entry.label,
            }))}
          />
          {scope === "document" ? (
            <Dropdown
              aria-label="Document"
              value={documentId}
              onChange={(event) => setDocumentId(event.target.value)}
              placeholder="Choose a document…"
              options={documents.map((document) => {
                const indexed = presentIndexedState(
                  document.processing_status,
                  knowledgeDocumentIds.has(document.id),
                );
                const processing = presentProcessingStatus(
                  document.processing_status,
                  { hasKnowledge: knowledgeDocumentIds.has(document.id) },
                );
                return {
                  value: document.id,
                  label: `${document.name} · ${processing.label} · ${indexed.label}`,
                };
              })}
            />
          ) : null}
          <Dropdown
            aria-label="Collection"
            value={collectionId}
            onChange={(event) => setCollectionId(event.target.value)}
            placeholder="Any collection"
            options={collections.map((collection) => ({
              value: collection.id,
              label: collection.name,
            }))}
          />
        </div>

        {tags.length > 0 ? (
          <div className="search-tag-filters">
            <span className="muted">Tags:</span>
            <TagChips
              tags={tags}
              selectedIds={selectedTagIds}
              size="sm"
              onToggle={(tagId) => {
                setSelectedTagIds((current) =>
                  current.includes(tagId)
                    ? current.filter((id) => id !== tagId)
                    : [...current, tagId],
                );
              }}
            />
          </div>
        ) : null}

        {!query.trim() && recentSearches.length > 0 ? (
          <div className="recent-searches">
            <span className="muted">Recent:</span>
            {recentSearches.map((term) => (
              <button
                key={term}
                type="button"
                className="recent-search-chip"
                onClick={() => setQuery(term)}
              >
                {term}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {error ? <Alert tone="bad">{error}</Alert> : null}

      {canUseBackend && notIndexedDocs.length > 0 ? (
        <Alert tone="warn" className="search-indexing-banner">
          {notIndexedDocs.length === 1
            ? "1 document is still processing and may be missing from results."
            : `${notIndexedDocs.length} documents are still processing and may be missing from results.`}{" "}
          <button
            type="button"
            className="link-button"
            onClick={() => setActivePage("documents")}
          >
            View Documents
          </button>
        </Alert>
      ) : null}

      {!canUseBackend ? (
        <EmptyState
          title="Search unavailable"
          description="Connect to the Memovi backend to search indexed knowledge. Offline or disconnected sessions cannot query the index."
        />
      ) : !query.trim() ? (
        <EmptyState
          title="Search your knowledge"
          description={
            documents.length === 0
              ? "Import documents first. Search only includes content that has finished processing and indexing."
              : "Find documents and extracted knowledge across your workspace. Content still processing will not appear until it is indexed."
          }
          action={
            documents.length === 0 ? (
              <Button
                variant="secondary"
                onClick={() => setActivePage("documents")}
              >
                Go to Documents
              </Button>
            ) : undefined
          }
        />
      ) : isSearching ? (
        <LoadingState label="Searching…" />
      ) : results.length === 0 ? (
        <EmptyState
          title="No matches"
          description={emptyDescription}
          action={
            processingDocs.length > 0 || failedDocs.length > 0 ? (
              <Button
                variant="secondary"
                onClick={() => setActivePage("documents")}
              >
                Open Documents
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="search-results">
          {results.map((result) => {
            const source = sourceById.get(result.document_id);
            const indexed = presentIndexedState(
              source?.processing_status,
              knowledgeDocumentIds.has(result.document_id),
            );
            return (
              <div
                key={`${result.search_document_id}:${result.knowledge_item_id}`}
                className="search-result-card"
              >
                <button
                  type="button"
                  className="search-result-header"
                  onClick={() => openKnowledgeItem(result.knowledge_item_id)}
                >
                  <span className="search-result-source">
                    <span>
                      {source?.name ?? "Unknown source"}
                    </span>
                    <StatusBadge label={indexed.label} tone={indexed.tone} />
                  </span>
                  <span>score {result.score.toFixed(3)}</span>
                </button>
                <p className="search-result-snippet">{result.text}</p>
                <div className="search-result-actions">
                  <Button
                    variant="secondary"
                    onClick={() => void handleAskAbout(result)}
                  >
                    Ask about this
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
