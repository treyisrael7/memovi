import { useEffect, useMemo, useState } from "react";

import { ApiRequestError } from "../api/client";
import { getDocument, listDocuments } from "../api/documents";
import {
  getKnowledge,
  getKnowledgeDashboard,
  listConcepts,
  listKnowledge,
  listRelationships,
} from "../api/memory";
import { searchKnowledge, type SearchMode } from "../api/search";
import type {
  ConceptSummary,
  DocumentSummary,
  KnowledgeDashboard,
  KnowledgeDetail,
  KnowledgeSummary,
  RelationshipSummary,
  SearchResultItem,
} from "../api/types";
import { useAppState } from "../state/AppStateContext";

type ExplorerSection =
  | "overview"
  | "search"
  | "concepts"
  | "entities"
  | "relationships"
  | "sources";

const SECTIONS: ReadonlyArray<{ id: ExplorerSection; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "search", label: "Search" },
  { id: "concepts", label: "Concepts" },
  { id: "entities", label: "Entities" },
  { id: "relationships", label: "Relationships" },
  { id: "sources", label: "Sources" },
];

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatConfidence(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(value * 100)}%`;
}

function shortId(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}…` : value;
}

export function KnowledgeExplorerPage() {
  const { activeWorkspace, connection } = useAppState();
  const workspaceId = activeWorkspace?.id ?? null;
  const canUseBackend =
    connection.status === "connected" || connection.status === "degraded";

  const [section, setSection] = useState<ExplorerSection>("overview");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [dashboard, setDashboard] = useState<KnowledgeDashboard | null>(null);
  const [entities, setEntities] = useState<KnowledgeSummary[]>([]);
  const [concepts, setConcepts] = useState<ConceptSummary[]>([]);
  const [relationships, setRelationships] = useState<RelationshipSummary[]>([]);
  const [sources, setSources] = useState<DocumentSummary[]>([]);

  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [selectedConceptId, setSelectedConceptId] = useState<string | null>(null);
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(
    null,
  );
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [selectedSearchKey, setSelectedSearchKey] = useState<string | null>(null);

  const [detail, setDetail] = useState<KnowledgeDetail | null>(null);
  const [sourceDetail, setSourceDetail] = useState<DocumentSummary | null>(null);
  const [relatedEntities, setRelatedEntities] = useState<KnowledgeSummary[]>([]);

  const [query, setQuery] = useState("");
  const [searchMode, setSearchMode] = useState<SearchMode>("hybrid");
  const [filterDocumentId, setFilterDocumentId] = useState("");
  const [filterSourceType, setFilterSourceType] = useState("");
  const [filterEntityType, setFilterEntityType] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);

  const sourceById = useMemo(() => {
    const map = new Map<string, DocumentSummary>();
    for (const source of sources) {
      map.set(source.id, source);
    }
    return map;
  }, [sources]);

  const selectedConcept = useMemo(
    () => concepts.find((item) => item.id === selectedConceptId) ?? null,
    [concepts, selectedConceptId],
  );

  const selectedRelationship = useMemo(
    () => relationships.find((item) => item.id === selectedRelationshipId) ?? null,
    [relationships, selectedRelationshipId],
  );

  const selectedSearchResult = useMemo(
    () =>
      searchResults.find(
        (item) =>
          `${item.search_document_id}:${item.knowledge_item_id}` === selectedSearchKey,
      ) ?? null,
    [searchResults, selectedSearchKey],
  );

  useEffect(() => {
    if (!workspaceId || !canUseBackend) {
      setDashboard(null);
      setEntities([]);
      setConcepts([]);
      setRelationships([]);
      setSources([]);
      setSearchResults([]);
      setDetail(null);
      setSourceDetail(null);
      setRelatedEntities([]);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    void Promise.all([
      getKnowledgeDashboard(workspaceId),
      listKnowledge(workspaceId, {
        documentId: filterDocumentId || undefined,
        sourceType: filterSourceType || undefined,
        entityType: filterEntityType || undefined,
      }),
      listConcepts(workspaceId),
      listRelationships(workspaceId),
      listDocuments(workspaceId),
    ])
      .then(([dash, knowledge, conceptList, relationshipList, documentList]) => {
        if (cancelled) return;
        setDashboard(dash);
        setEntities(knowledge.items);
        setConcepts(conceptList.items);
        setRelationships(relationshipList.items);
        setSources(documentList.items);
        setSelectedEntityId((current) => {
          if (current && knowledge.items.some((item) => item.id === current)) {
            return current;
          }
          return knowledge.items[0]?.id ?? null;
        });
        setSelectedConceptId((current) => {
          if (current && conceptList.items.some((item) => item.id === current)) {
            return current;
          }
          return conceptList.items[0]?.id ?? null;
        });
        setSelectedRelationshipId((current) => {
          if (
            current &&
            relationshipList.items.some((item) => item.id === current)
          ) {
            return current;
          }
          return relationshipList.items[0]?.id ?? null;
        });
        setSelectedSourceId((current) => {
          if (current && documentList.items.some((item) => item.id === current)) {
            return current;
          }
          return documentList.items[0]?.id ?? null;
        });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Failed to load knowledge explorer data.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [
    workspaceId,
    canUseBackend,
    filterDocumentId,
    filterSourceType,
    filterEntityType,
  ]);

  useEffect(() => {
    if (!workspaceId || !canUseBackend || !selectedEntityId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    void getKnowledge(workspaceId, selectedEntityId)
      .then((payload) => {
        if (!cancelled) setDetail(payload);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Failed to load knowledge detail.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, canUseBackend, selectedEntityId]);

  useEffect(() => {
    if (!workspaceId || !canUseBackend || !selectedSourceId) {
      setSourceDetail(null);
      setRelatedEntities([]);
      return;
    }
    let cancelled = false;
    void Promise.all([
      getDocument(workspaceId, selectedSourceId),
      listKnowledge(workspaceId, { documentId: selectedSourceId }),
    ])
      .then(([document, knowledge]) => {
        if (cancelled) return;
        setSourceDetail(document);
        setRelatedEntities(knowledge.items);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Failed to load source detail.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, canUseBackend, selectedSourceId]);

  useEffect(() => {
    if (!workspaceId || !canUseBackend) {
      setSearchResults([]);
      return;
    }
    const trimmed = query.trim();
    if (!trimmed) {
      setSearchResults([]);
      setSelectedSearchKey(null);
      return;
    }

    let cancelled = false;
    const handle = window.setTimeout(() => {
      void searchKnowledge(workspaceId, {
        q: trimmed,
        mode: searchMode,
        documentId: filterDocumentId || undefined,
        sourceType: filterSourceType || filterEntityType || undefined,
      })
        .then((payload) => {
          if (cancelled) return;
          setSearchResults(payload.results);
          setSelectedSearchKey((current) => {
            if (
              current &&
              payload.results.some(
                (item) =>
                  `${item.search_document_id}:${item.knowledge_item_id}` === current,
              )
            ) {
              return current;
            }
            const first = payload.results[0];
            return first
              ? `${first.search_document_id}:${first.knowledge_item_id}`
              : null;
          });
        })
        .catch((err: unknown) => {
          if (!cancelled) {
            setError(
              err instanceof ApiRequestError
                ? err.message
                : "Search failed.",
            );
          }
        });
    }, 200);

    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [
    workspaceId,
    canUseBackend,
    query,
    searchMode,
    filterDocumentId,
    filterSourceType,
    filterEntityType,
  ]);

  useEffect(() => {
    if (
      section === "search" &&
      selectedSearchResult?.knowledge_item_id &&
      selectedSearchResult.knowledge_item_id !== selectedEntityId
    ) {
      setSelectedEntityId(selectedSearchResult.knowledge_item_id);
    }
  }, [section, selectedSearchResult, selectedEntityId]);

  function openEntity(knowledgeItemId: string) {
    setSelectedEntityId(knowledgeItemId);
    setSection("entities");
  }

  function openSource(documentId: string) {
    setSelectedSourceId(documentId);
    setSection("sources");
  }

  function renderDetailPanel() {
    if (section === "overview") {
      if (!dashboard) {
        return <p className="muted">No dashboard data yet.</p>;
      }
      return (
        <div className="explorer-detail-body">
          <h2>Knowledge overview</h2>
          <p className="lede">
            What Memovi knows in workspace{" "}
            <strong>{activeWorkspace?.name ?? dashboard.workspace_id}</strong>.
          </p>
          <dl className="meta-grid">
            <div className="meta-card">
              <dt>Entities</dt>
              <dd>{dashboard.knowledge_item_count}</dd>
            </div>
            <div className="meta-card">
              <dt>Chunks</dt>
              <dd>{dashboard.chunk_count}</dd>
            </div>
            <div className="meta-card">
              <dt>Sources</dt>
              <dd>{dashboard.source_document_count}</dd>
            </div>
            <div className="meta-card">
              <dt>Concepts</dt>
              <dd>{dashboard.concept_count}</dd>
            </div>
            <div className="meta-card">
              <dt>Relationships</dt>
              <dd>{dashboard.relationship_count}</dd>
            </div>
          </dl>
          <h3>By source type</h3>
          <ul className="explorer-count-list">
            {Object.entries(dashboard.source_type_counts).map(([key, count]) => (
              <li key={key}>
                <span>{key}</span>
                <strong>{count}</strong>
              </li>
            ))}
            {Object.keys(dashboard.source_type_counts).length === 0 && (
              <li className="muted">No source types yet.</li>
            )}
          </ul>
          <h3>By MIME type</h3>
          <ul className="explorer-count-list">
            {Object.entries(dashboard.mime_type_counts).map(([key, count]) => (
              <li key={key}>
                <span>{key}</span>
                <strong>{count}</strong>
              </li>
            ))}
            {Object.keys(dashboard.mime_type_counts).length === 0 && (
              <li className="muted">No MIME types yet.</li>
            )}
          </ul>
        </div>
      );
    }

    if (section === "concepts") {
      if (!selectedConcept) {
        return <p className="muted">Select a concept to inspect.</p>;
      }
      const related = entities.filter((item) =>
        selectedConcept.knowledge_item_ids.includes(item.id),
      );
      return (
        <div className="explorer-detail-body">
          <h2>{selectedConcept.label}</h2>
          <dl className="explorer-meta">
            <div>
              <dt>Kind</dt>
              <dd>{selectedConcept.kind}</dd>
            </div>
            <div>
              <dt>Related entities</dt>
              <dd>{selectedConcept.knowledge_item_count}</dd>
            </div>
            <div>
              <dt>Confidence</dt>
              <dd>—</dd>
            </div>
            <div>
              <dt>Workspace</dt>
              <dd>{activeWorkspace?.name ?? "—"}</dd>
            </div>
          </dl>
          <h3>Related entities</h3>
          <ul className="explorer-link-list">
            {related.map((item) => (
              <li key={item.id}>
                <button type="button" onClick={() => openEntity(item.id)}>
                  {item.summary || shortId(item.id)}
                </button>
              </li>
            ))}
          </ul>
        </div>
      );
    }

    if (section === "relationships") {
      if (!selectedRelationship) {
        return <p className="muted">Select a relationship to inspect.</p>;
      }
      return (
        <div className="explorer-detail-body">
          <h2>{selectedRelationship.relationship_type}</h2>
          <p className="lede">
            {selectedRelationship.from_kind} → {selectedRelationship.to_kind}
          </p>
          <dl className="explorer-meta">
            <div>
              <dt>From</dt>
              <dd>
                {selectedRelationship.from_kind} {shortId(selectedRelationship.from_id)}
              </dd>
            </div>
            <div>
              <dt>To</dt>
              <dd>
                {selectedRelationship.to_kind} {shortId(selectedRelationship.to_id)}
              </dd>
            </div>
            <div>
              <dt>Source document</dt>
              <dd>
                <button
                  type="button"
                  className="linkish"
                  onClick={() => openSource(selectedRelationship.document_id)}
                >
                  {sourceById.get(selectedRelationship.document_id)?.name ??
                    shortId(selectedRelationship.document_id)}
                </button>
              </dd>
            </div>
            <div>
              <dt>Created</dt>
              <dd>{formatTimestamp(selectedRelationship.created_at)}</dd>
            </div>
            <div>
              <dt>Workspace</dt>
              <dd>{activeWorkspace?.name ?? "—"}</dd>
            </div>
          </dl>
          {selectedRelationship.knowledge_item_id && (
            <button
              type="button"
              className="primary-action"
              onClick={() => openEntity(selectedRelationship.knowledge_item_id!)}
            >
              Open related entity
            </button>
          )}
        </div>
      );
    }

    if (section === "sources") {
      if (!sourceDetail) {
        return <p className="muted">Select a source document to inspect.</p>;
      }
      return (
        <div className="explorer-detail-body">
          <h2>{sourceDetail.name}</h2>
          <dl className="explorer-meta">
            <div>
              <dt>Source type</dt>
              <dd>{sourceDetail.source_type}</dd>
            </div>
            <div>
              <dt>MIME type</dt>
              <dd>{sourceDetail.mime_type}</dd>
            </div>
            <div>
              <dt>Created</dt>
              <dd>{formatTimestamp(sourceDetail.created_at)}</dd>
            </div>
            <div>
              <dt>Workspace</dt>
              <dd>{activeWorkspace?.name ?? "—"}</dd>
            </div>
            <div>
              <dt>Document ID</dt>
              <dd>{sourceDetail.id}</dd>
            </div>
          </dl>
          <h3>Derived knowledge</h3>
          <ul className="explorer-link-list">
            {relatedEntities.map((item) => (
              <li key={item.id}>
                <button type="button" onClick={() => openEntity(item.id)}>
                  {item.summary || shortId(item.id)}
                </button>
              </li>
            ))}
            {relatedEntities.length === 0 && (
              <li className="muted">No materialized knowledge for this source yet.</li>
            )}
          </ul>
        </div>
      );
    }

    // search + entities share knowledge detail
    if (!detail) {
      return <p className="muted">Select an item to inspect.</p>;
    }

    const relatedConcepts = concepts.filter((concept) =>
      concept.knowledge_item_ids.includes(detail.id),
    );

    return (
      <div className="explorer-detail-body">
        <h2>Knowledge entity</h2>
        <p className="lede">{detail.summary || "No summary available."}</p>
        <dl className="explorer-meta">
          <div>
            <dt>Source document</dt>
            <dd>
              <button
                type="button"
                className="linkish"
                onClick={() => openSource(detail.document_id)}
              >
                {sourceById.get(detail.document_id)?.name ??
                  shortId(detail.document_id)}
              </button>
            </dd>
          </div>
          <div>
            <dt>Source type</dt>
            <dd>{detail.source_type}</dd>
          </div>
          <div>
            <dt>MIME type</dt>
            <dd>{detail.mime_type}</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>{formatConfidence(detail.confidence)}</dd>
          </div>
          <div>
            <dt>Extracted</dt>
            <dd>{formatTimestamp(detail.created_at)}</dd>
          </div>
          <div>
            <dt>Last updated</dt>
            <dd>{formatTimestamp(detail.updated_at)}</dd>
          </div>
          <div>
            <dt>Workspace</dt>
            <dd>{activeWorkspace?.name ?? detail.workspace_id}</dd>
          </div>
          <div>
            <dt>Chunks</dt>
            <dd>{detail.chunks.length}</dd>
          </div>
        </dl>

        <h3>Related concepts</h3>
        <ul className="explorer-link-list">
          {relatedConcepts.map((concept) => (
            <li key={concept.id}>
              <button
                type="button"
                onClick={() => {
                  setSelectedConceptId(concept.id);
                  setSection("concepts");
                }}
              >
                {concept.label} ({concept.kind})
              </button>
            </li>
          ))}
          {relatedConcepts.length === 0 && (
            <li className="muted">No structural concepts linked.</li>
          )}
        </ul>

        <h3>Related entities</h3>
        <ul className="explorer-link-list">
          {entities
            .filter(
              (item) =>
                item.document_id === detail.document_id && item.id !== detail.id,
            )
            .map((item) => (
              <li key={item.id}>
                <button type="button" onClick={() => openEntity(item.id)}>
                  {item.summary || shortId(item.id)}
                </button>
              </li>
            ))}
          {entities.filter(
            (item) =>
              item.document_id === detail.document_id && item.id !== detail.id,
          ).length === 0 && (
            <li className="muted">No sibling entities from this source.</li>
          )}
        </ul>

        <h3>Chunks</h3>
        <ol className="explorer-chunk-list">
          {detail.chunks.map((chunk) => (
            <li key={chunk.id}>
              <header>
                <span>#{chunk.chunk_index}</span>
                <time>{formatTimestamp(chunk.created_at)}</time>
              </header>
              <p>{chunk.text}</p>
            </li>
          ))}
        </ol>
      </div>
    );
  }

  function renderList() {
    if (section === "overview") {
      return (
        <div className="explorer-list-empty">
          <p className="muted">
            Overview summarizes the active workspace. Use the sections to inspect
            entities, concepts, relationships, and sources.
          </p>
        </div>
      );
    }

    if (section === "search") {
      return (
        <ul className="explorer-list">
          {searchResults.map((result) => {
            const key = `${result.search_document_id}:${result.knowledge_item_id}`;
            return (
              <li key={key}>
                <button
                  type="button"
                  data-active={selectedSearchKey === key}
                  onClick={() => {
                    setSelectedSearchKey(key);
                    setSelectedEntityId(result.knowledge_item_id);
                  }}
                >
                  <span className="explorer-list-title">
                    {result.text.slice(0, 120) || shortId(result.knowledge_item_id)}
                  </span>
                  <span className="explorer-list-meta">
                    score {result.score.toFixed(3)} ·{" "}
                    {sourceById.get(result.document_id)?.name ??
                      shortId(result.document_id)}
                  </span>
                </button>
              </li>
            );
          })}
          {query.trim() && searchResults.length === 0 && (
            <li className="muted explorer-list-empty-item">No matches.</li>
          )}
          {!query.trim() && (
            <li className="muted explorer-list-empty-item">
              Type a query to search knowledge.
            </li>
          )}
        </ul>
      );
    }

    if (section === "concepts") {
      return (
        <ul className="explorer-list">
          {concepts.map((concept) => (
            <li key={concept.id}>
              <button
                type="button"
                data-active={selectedConceptId === concept.id}
                onClick={() => setSelectedConceptId(concept.id)}
              >
                <span className="explorer-list-title">{concept.label}</span>
                <span className="explorer-list-meta">
                  {concept.kind} · {concept.knowledge_item_count} entities
                </span>
              </button>
            </li>
          ))}
          {concepts.length === 0 && (
            <li className="muted explorer-list-empty-item">No concepts yet.</li>
          )}
        </ul>
      );
    }

    if (section === "relationships") {
      return (
        <ul className="explorer-list">
          {relationships.map((rel) => (
            <li key={rel.id}>
              <button
                type="button"
                data-active={selectedRelationshipId === rel.id}
                onClick={() => setSelectedRelationshipId(rel.id)}
              >
                <span className="explorer-list-title">{rel.relationship_type}</span>
                <span className="explorer-list-meta">
                  {rel.from_kind} → {rel.to_kind}
                </span>
              </button>
            </li>
          ))}
          {relationships.length === 0 && (
            <li className="muted explorer-list-empty-item">
              No relationships yet.
            </li>
          )}
        </ul>
      );
    }

    if (section === "sources") {
      return (
        <ul className="explorer-list">
          {sources.map((source) => (
            <li key={source.id}>
              <button
                type="button"
                data-active={selectedSourceId === source.id}
                onClick={() => setSelectedSourceId(source.id)}
              >
                <span className="explorer-list-title">{source.name}</span>
                <span className="explorer-list-meta">
                  {source.source_type} · {source.mime_type}
                </span>
              </button>
            </li>
          ))}
          {sources.length === 0 && (
            <li className="muted explorer-list-empty-item">No sources yet.</li>
          )}
        </ul>
      );
    }

    return (
      <ul className="explorer-list">
        {entities.map((entity) => (
          <li key={entity.id}>
            <button
              type="button"
              data-active={selectedEntityId === entity.id}
              onClick={() => setSelectedEntityId(entity.id)}
            >
              <span className="explorer-list-title">
                {entity.summary || shortId(entity.id)}
              </span>
              <span className="explorer-list-meta">
                {entity.source_type} · {entity.chunk_count} chunks ·{" "}
                {formatTimestamp(entity.updated_at)}
              </span>
            </button>
          </li>
        ))}
        {entities.length === 0 && (
          <li className="muted explorer-list-empty-item">
            No knowledge entities yet. Ingest documents to materialize knowledge.
          </li>
        )}
      </ul>
    );
  }

  return (
    <div className="explorer-layout">
      <aside className="explorer-nav">
        <div className="explorer-nav-header">
          <h2>Knowledge</h2>
          <p className="muted">Inspect what Memovi knows.</p>
        </div>
        <nav className="explorer-section-nav" aria-label="Knowledge sections">
          {SECTIONS.map((entry) => (
            <button
              key={entry.id}
              type="button"
              data-active={section === entry.id}
              onClick={() => setSection(entry.id)}
            >
              {entry.label}
            </button>
          ))}
        </nav>
      </aside>

      <section className="explorer-main">
        <header className="explorer-toolbar">
          <div className="explorer-filters">
            {(section === "search" || section === "entities") && (
              <>
                {section === "search" && (
                  <>
                    <label>
                      <span>Search</span>
                      <input
                        type="search"
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                        placeholder="Search knowledge…"
                        autoFocus={section === "search"}
                      />
                    </label>
                    <label>
                      <span>Mode</span>
                      <select
                        value={searchMode}
                        onChange={(event) =>
                          setSearchMode(event.target.value as SearchMode)
                        }
                      >
                        <option value="hybrid">Hybrid</option>
                        <option value="keyword">Keyword</option>
                        <option value="semantic">Semantic</option>
                      </select>
                    </label>
                  </>
                )}
                <label>
                  <span>Source document</span>
                  <select
                    value={filterDocumentId}
                    onChange={(event) => setFilterDocumentId(event.target.value)}
                  >
                    <option value="">All sources</option>
                    {sources.map((source) => (
                      <option key={source.id} value={source.id}>
                        {source.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Source type</span>
                  <select
                    value={filterSourceType}
                    onChange={(event) => setFilterSourceType(event.target.value)}
                  >
                    <option value="">All</option>
                    {Array.from(
                      new Set(sources.map((source) => source.source_type)),
                    ).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Entity type</span>
                  <input
                    type="text"
                    value={filterEntityType}
                    onChange={(event) => setFilterEntityType(event.target.value)}
                    placeholder="source or mime"
                  />
                </label>
              </>
            )}
          </div>
          <div className="explorer-toolbar-status">
            {isLoading ? "Loading…" : `${entities.length} entities`}
          </div>
        </header>

        {error && (
          <p className="chat-error" role="alert">
            {error}
          </p>
        )}

        {!canUseBackend && (
          <p className="muted">
            Connect to the backend to inspect knowledge for the active workspace.
          </p>
        )}

        <div className="explorer-split">
          <div className="explorer-list-pane">{renderList()}</div>
          <div className="explorer-detail-pane">{renderDetailPanel()}</div>
        </div>
      </section>
    </div>
  );
}
