import { useEffect, useMemo, useState } from "react";

import { ApiRequestError } from "../api/client";
import { createConversation } from "../api/conversations";
import { listDocuments } from "../api/documents";
import { searchKnowledge, type SearchMode } from "../api/search";
import type { DocumentSummary, SearchResultItem } from "../api/types";
import { useAppState } from "../state/AppStateContext";
import { EmptyState } from "./ui/EmptyState";
import { LoadingState } from "./ui/LoadingState";
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
  } = useAppState();
  const { showToast } = useToast();
  const workspaceId = activeWorkspace?.id ?? null;
  const canUseBackend =
    connection.status === "connected" || connection.status === "degraded";

  const [scope, setScope] = useState<SearchScope>("all");
  const [query, setQuery] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
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

  useEffect(() => {
    if (!workspaceId) {
      setDocuments([]);
      return;
    }
    setRecentSearches(loadRecentSearches(workspaceId));
    if (!canUseBackend) {
      setDocuments([]);
      return;
    }
    let cancelled = false;
    void listDocuments(workspaceId)
      .then((payload) => {
        if (!cancelled) setDocuments(payload.items);
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
  }, [workspaceId, canUseBackend, query, scope, documentId]);

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

  return (
    <div className="search-page">
      <div className="search-header">
        <h1>Search</h1>
        <form
          className="search-input-row"
          onSubmit={(event) => {
            event.preventDefault();
            handleSubmit();
          }}
        >
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onBlur={() => handleSubmit()}
            placeholder="Search documents and knowledge…"
            autoFocus
            disabled={!canUseBackend}
          />
        </form>

        <div className="search-tabs" role="tablist" aria-label="Search scope">
          {SCOPES.map((entry) => (
            <button
              key={entry.id}
              type="button"
              role="tab"
              className="search-tab"
              data-active={scope === entry.id}
              onClick={() => setScope(entry.id)}
            >
              {entry.label}
            </button>
          ))}
          {scope === "document" ? (
            <select
              value={documentId}
              onChange={(event) => setDocumentId(event.target.value)}
            >
              <option value="">Choose a document…</option>
              {documents.map((document) => (
                <option key={document.id} value={document.id}>
                  {document.name}
                </option>
              ))}
            </select>
          ) : null}
        </div>

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

      {error ? (
        <div className="banner" data-tone="bad" role="alert">
          {error}
        </div>
      ) : null}

      {!canUseBackend ? (
        <EmptyState
          title="Backend unavailable"
          description="Connect to the Memovi backend to search your knowledge."
        />
      ) : !query.trim() ? (
        <EmptyState
          title="Search your knowledge"
          description="Find documents and extracted knowledge across your workspace."
        />
      ) : isSearching ? (
        <LoadingState label="Searching…" />
      ) : results.length === 0 ? (
        <EmptyState
          title="No matches"
          description="Try a different query or scope."
        />
      ) : (
        <div className="search-results">
          {results.map((result) => (
            <div
              key={`${result.search_document_id}:${result.knowledge_item_id}`}
              className="search-result-card"
            >
              <button
                type="button"
                className="search-result-header"
                onClick={() => openKnowledgeItem(result.knowledge_item_id)}
              >
                <span>
                  {sourceById.get(result.document_id)?.name ?? "Unknown source"}
                </span>
                <span>score {result.score.toFixed(3)}</span>
              </button>
              <p className="search-result-snippet">{result.text}</p>
              <div className="search-result-actions">
                <button
                  type="button"
                  className="retry-button"
                  onClick={() => void handleAskAbout(result)}
                >
                  Ask about this
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
