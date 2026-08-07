import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiRequestError } from "../api/client";
import {
  addCollectionMember,
  createCollection,
  deleteCollection,
  getCollectionSummary,
  listCollectionMembers,
  listCollections,
  removeCollectionMember,
  renameCollection,
  type CollectionMemberKind,
} from "../api/collections";
import { listConversations } from "../api/conversations";
import { listDocuments } from "../api/documents";
import { listKnowledge } from "../api/memory";
import { listWorkflows } from "../api/workflows";
import type {
  CollectionListItem,
  CollectionMembershipResponse,
  CollectionSummaryResponse,
  ConversationSummary,
  DocumentSummary,
  KnowledgeSummary,
  WorkflowDefinition,
} from "../api/types";
import { useAppState } from "../state/AppStateContext";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";
import { ConfirmDialog } from "./ui/ConfirmDialog";
import { EmptyState } from "./ui/EmptyState";
import { LoadingState } from "./ui/LoadingState";
import { Modal } from "./ui/Modal";
import { SearchInput } from "./ui/SearchInput";
import { SectionHeader } from "./ui/SectionHeader";
import { TextArea } from "./ui/TextArea";
import { TextInput } from "./ui/TextInput";
import { useToast } from "./ui/ToastContext";

const MEMBER_KINDS: ReadonlyArray<{ id: CollectionMemberKind; label: string }> =
  [
    { id: "document", label: "Document" },
    { id: "knowledge", label: "Knowledge" },
    { id: "conversation", label: "Conversation" },
    { id: "workflow", label: "Workflow" },
  ];

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function kindLabel(kind: string): string {
  return MEMBER_KINDS.find((entry) => entry.id === kind)?.label ?? kind;
}

export function CollectionsPage() {
  const {
    activeWorkspace,
    connection,
    openDocument,
    openKnowledgeItem,
    setActivePage,
  } = useAppState();
  const { showToast } = useToast();
  const workspaceId = activeWorkspace?.id ?? null;
  const canUseBackend =
    connection.status === "connected" || connection.status === "degraded";

  const [collections, setCollections] = useState<CollectionListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [summary, setSummary] = useState<CollectionSummaryResponse | null>(
    null,
  );
  const [members, setMembers] = useState<CollectionMembershipResponse[]>([]);
  const [memberQuery, setMemberQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const [renameOpen, setRenameOpen] = useState(false);
  const [renameName, setRenameName] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);

  const [pendingDelete, setPendingDelete] = useState<CollectionListItem | null>(
    null,
  );
  const [isDeleting, setIsDeleting] = useState(false);

  const [addOpen, setAddOpen] = useState(false);
  const [addKind, setAddKind] = useState<CollectionMemberKind>("document");
  const [addMemberId, setAddMemberId] = useState("");
  const [addReason, setAddReason] = useState("Added by user");
  const [isAdding, setIsAdding] = useState(false);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeSummary[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([]);

  const selected = useMemo(
    () => collections.find((item) => item.id === selectedId) ?? null,
    [collections, selectedId],
  );

  const refreshList = useCallback(async () => {
    if (!workspaceId || !canUseBackend) {
      setCollections([]);
      return;
    }
    const payload = await listCollections(workspaceId);
    setCollections(payload.items);
    setSelectedId((current) => {
      if (current && payload.items.some((item) => item.id === current)) {
        return current;
      }
      return payload.items[0]?.id ?? null;
    });
  }, [workspaceId, canUseBackend]);

  const refreshDetail = useCallback(
    async (collectionId: string, query: string) => {
      if (!workspaceId || !canUseBackend) {
        setSummary(null);
        setMembers([]);
        return;
      }
      setIsDetailLoading(true);
      try {
        const [summaryPayload, membersPayload] = await Promise.all([
          getCollectionSummary(workspaceId, collectionId),
          listCollectionMembers(workspaceId, collectionId, {
            q: query.trim() || undefined,
          }),
        ]);
        setSummary(summaryPayload);
        setMembers(membersPayload.items);
      } finally {
        setIsDetailLoading(false);
      }
    },
    [workspaceId, canUseBackend],
  );

  useEffect(() => {
    if (!workspaceId || !canUseBackend) {
      setCollections([]);
      setSelectedId(null);
      setSummary(null);
      setMembers([]);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    void listCollections(workspaceId)
      .then((payload) => {
        if (cancelled) return;
        setCollections(payload.items);
        setSelectedId(payload.items[0]?.id ?? null);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Failed to load collections.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, canUseBackend]);

  useEffect(() => {
    if (!selectedId || !workspaceId || !canUseBackend) {
      setSummary(null);
      setMembers([]);
      return;
    }
    let cancelled = false;
    setIsDetailLoading(true);
    setError(null);
    void Promise.all([
      getCollectionSummary(workspaceId, selectedId),
      listCollectionMembers(workspaceId, selectedId, {
        q: memberQuery.trim() || undefined,
      }),
    ])
      .then(([summaryPayload, membersPayload]) => {
        if (cancelled) return;
        setSummary(summaryPayload);
        setMembers(membersPayload.items);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Failed to load collection details.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setIsDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, workspaceId, canUseBackend, memberQuery]);

  useEffect(() => {
    if (!addOpen || !workspaceId || !canUseBackend) return;
    let cancelled = false;
    void Promise.all([
      listDocuments(workspaceId),
      listKnowledge(workspaceId),
      listConversations(workspaceId),
      listWorkflows(workspaceId),
    ])
      .then(([docs, knowledge, chats, flows]) => {
        if (cancelled) return;
        setDocuments(docs.items);
        setKnowledgeItems(knowledge.items);
        setConversations(chats.conversations);
        setWorkflows(flows.items);
      })
      .catch(() => {
        // Picker options are best-effort; manual IDs still work.
      });
    return () => {
      cancelled = true;
    };
  }, [addOpen, workspaceId, canUseBackend]);

  const candidateOptions = useMemo(() => {
    switch (addKind) {
      case "document":
        return documents.map((doc) => ({ id: doc.id, label: doc.name }));
      case "knowledge":
        return knowledgeItems.map((item) => ({
          id: item.id,
          label: item.summary || item.id,
        }));
      case "conversation":
        return conversations.map((item) => ({
          id: item.conversation_id,
          label: item.title || item.conversation_id,
        }));
      case "workflow":
        return workflows.map((item) => ({
          id: item.workflow_id,
          label: item.name,
        }));
      default:
        return [];
    }
  }, [addKind, documents, knowledgeItems, conversations, workflows]);

  async function handleCreate() {
    if (!workspaceId || !createName.trim()) return;
    setIsCreating(true);
    try {
      const created = await createCollection(workspaceId, {
        name: createName.trim(),
        description: createDescription,
      });
      showToast(`Created “${created.name}”.`, "ok");
      setCreateOpen(false);
      setCreateName("");
      setCreateDescription("");
      await refreshList();
      setSelectedId(created.id);
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to create collection.",
        "bad",
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function handleRename() {
    if (!workspaceId || !selectedId || !renameName.trim()) return;
    setIsRenaming(true);
    try {
      const updated = await renameCollection(
        workspaceId,
        selectedId,
        renameName.trim(),
      );
      showToast(`Renamed to “${updated.name}”.`, "ok");
      setRenameOpen(false);
      await refreshList();
      await refreshDetail(selectedId, memberQuery);
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to rename collection.",
        "bad",
      );
    } finally {
      setIsRenaming(false);
    }
  }

  async function handleDelete() {
    if (!workspaceId || !pendingDelete) return;
    setIsDeleting(true);
    try {
      await deleteCollection(workspaceId, pendingDelete.id);
      showToast(`Deleted “${pendingDelete.name}”.`, "ok");
      setPendingDelete(null);
      await refreshList();
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to delete collection.",
        "bad",
      );
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleAddMember() {
    if (!workspaceId || !selectedId || !addMemberId.trim()) return;
    setIsAdding(true);
    try {
      await addCollectionMember(workspaceId, selectedId, {
        memberKind: addKind,
        memberId: addMemberId.trim(),
        reason: addReason.trim() || "Added by user",
      });
      showToast("Item added to collection.", "ok");
      setAddOpen(false);
      setAddMemberId("");
      setAddReason("Added by user");
      await refreshList();
      await refreshDetail(selectedId, memberQuery);
    } catch (err) {
      showToast(
        err instanceof ApiRequestError ? err.message : "Failed to add item.",
        "bad",
      );
    } finally {
      setIsAdding(false);
    }
  }

  async function handleRemoveMember(member: CollectionMembershipResponse) {
    if (!workspaceId || !selectedId) return;
    try {
      await removeCollectionMember(
        workspaceId,
        selectedId,
        member.member_kind,
        member.member_id,
      );
      showToast("Item removed from collection.", "ok");
      await refreshList();
      await refreshDetail(selectedId, memberQuery);
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to remove item.",
        "bad",
      );
    }
  }

  function openMember(member: CollectionMembershipResponse) {
    if (member.member_kind === "document") {
      openDocument(member.member_id);
      return;
    }
    if (member.member_kind === "knowledge") {
      openKnowledgeItem(member.member_id);
      return;
    }
    if (member.member_kind === "conversation") {
      setActivePage("chat");
      return;
    }
    if (member.member_kind === "workflow") {
      setActivePage("workflows");
    }
  }

  return (
    <div className="collections-page">
      <SectionHeader
        title="Collections"
        description="Organize documents, knowledge, conversations, and workflows into flat groups. Collections do not change ingestion or ownership."
        level={1}
        actions={
          <Button
            disabled={!canUseBackend || !workspaceId}
            onClick={() => setCreateOpen(true)}
          >
            New collection
          </Button>
        }
      />

      {!canUseBackend ? (
        <Alert tone="warn">Connect to the backend to manage collections.</Alert>
      ) : null}
      {error ? <Alert tone="bad">{error}</Alert> : null}

      <div className="documents-split">
        {isLoading ? (
          <LoadingState label="Loading collections…" />
        ) : collections.length === 0 ? (
          <EmptyState
            title="No collections yet"
            description="Create a collection such as Projects, Research, or Finance to group related knowledge."
            action={
              <Button
                disabled={!canUseBackend || !workspaceId}
                onClick={() => setCreateOpen(true)}
              >
                New collection
              </Button>
            }
          />
        ) : (
          <ul className="documents-list">
            {collections.map((collection) => (
              <li key={collection.id}>
                <button
                  type="button"
                  data-active={collection.id === selectedId}
                  onClick={() => setSelectedId(collection.id)}
                >
                  <div className="documents-list-title-row">
                    <span className="documents-list-title">
                      {collection.name}
                    </span>
                  </div>
                  <span className="documents-list-meta">
                    {collection.item_count} item
                    {collection.item_count === 1 ? "" : "s"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="document-detail">
          {!selected ? (
            <EmptyState
              title="Select a collection"
              description="Choose a collection to browse contents, statistics, and recent activity."
            />
          ) : isDetailLoading && !summary ? (
            <LoadingState label="Loading collection…" />
          ) : (
            <>
              <div className="document-detail-header">
                <div>
                  <h2>{summary?.name ?? selected.name}</h2>
                  <p className="muted">
                    {(summary?.description || selected.description) ||
                      "No description"}
                  </p>
                </div>
                <div className="document-detail-actions">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setRenameName(summary?.name ?? selected.name);
                      setRenameOpen(true);
                    }}
                  >
                    Rename
                  </Button>
                  <Button variant="secondary" onClick={() => setAddOpen(true)}>
                    Add item
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => setPendingDelete(selected)}
                  >
                    Delete
                  </Button>
                </div>
              </div>

              <dl className="meta-grid">
                <div className="meta-card">
                  <dt>Items</dt>
                  <dd>{summary?.item_count ?? selected.item_count}</dd>
                </div>
                <div className="meta-card">
                  <dt>Documents</dt>
                  <dd>{summary?.counts_by_kind.document ?? 0}</dd>
                </div>
                <div className="meta-card">
                  <dt>Knowledge</dt>
                  <dd>{summary?.counts_by_kind.knowledge ?? 0}</dd>
                </div>
                <div className="meta-card">
                  <dt>Updated</dt>
                  <dd>{formatTimestamp(summary?.updated_at)}</dd>
                </div>
              </dl>

              <SectionHeader title="Contents" />
              <SearchInput
                value={memberQuery}
                onChange={(event) => setMemberQuery(event.target.value)}
                placeholder="Search members by ID, kind, or reason…"
              />
              {members.length === 0 ? (
                <EmptyState
                  title="No items in this collection"
                  description="Add documents, knowledge, conversations, or workflows. Each membership keeps a reason so you know why it belongs here."
                  action={
                    <Button onClick={() => setAddOpen(true)}>Add item</Button>
                  }
                />
              ) : (
                <ul className="documents-list collection-members">
                  {members.map((member) => (
                    <li key={member.id} className="collection-member-row">
                      <button
                        type="button"
                        className="linkish"
                        onClick={() => openMember(member)}
                      >
                        {kindLabel(member.member_kind)} · {member.member_id}
                      </button>
                      <p className="muted">
                        {member.reason} · added{" "}
                        {formatTimestamp(member.added_at)}
                      </p>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => void handleRemoveMember(member)}
                      >
                        Remove
                      </Button>
                    </li>
                  ))}
                </ul>
              )}

              <SectionHeader title="Recent activity" />
              {(summary?.recent_activity.length ?? 0) === 0 ? (
                <p className="muted">No activity yet.</p>
              ) : (
                <ul className="explorer-link-list">
                  {summary?.recent_activity.map((entry, index) => (
                    <li key={`${entry.occurred_at}-${index}`}>
                      <strong>{entry.activity_type}</strong>
                      <span className="muted">
                        {" "}
                        · {formatTimestamp(entry.occurred_at)}
                      </span>
                      {entry.detail ? (
                        <p className="muted">{entry.detail}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      </div>

      {createOpen ? (
        <Modal
          title="Create collection"
          onClose={() => !isCreating && setCreateOpen(false)}
          busy={isCreating}
          footer={
            <>
              <Button
                variant="secondary"
                onClick={() => setCreateOpen(false)}
                disabled={isCreating}
              >
                Cancel
              </Button>
              <Button
                onClick={() => void handleCreate()}
                disabled={isCreating || !createName.trim()}
                busy={isCreating}
              >
                Create
              </Button>
            </>
          }
        >
          <TextInput
            label="Name"
            value={createName}
            onChange={(event) => setCreateName(event.target.value)}
            placeholder="e.g. Research"
          />
          <TextArea
            label="Description"
            value={createDescription}
            onChange={(event) => setCreateDescription(event.target.value)}
            placeholder="Optional context for this collection"
          />
        </Modal>
      ) : null}

      {renameOpen ? (
        <Modal
          title="Rename collection"
          onClose={() => !isRenaming && setRenameOpen(false)}
          busy={isRenaming}
          footer={
            <>
              <Button
                variant="secondary"
                onClick={() => setRenameOpen(false)}
                disabled={isRenaming}
              >
                Cancel
              </Button>
              <Button
                onClick={() => void handleRename()}
                disabled={isRenaming || !renameName.trim()}
                busy={isRenaming}
              >
                Save
              </Button>
            </>
          }
        >
          <TextInput
            label="Name"
            value={renameName}
            onChange={(event) => setRenameName(event.target.value)}
          />
        </Modal>
      ) : null}

      {addOpen ? (
        <Modal
          title="Add to collection"
          onClose={() => !isAdding && setAddOpen(false)}
          busy={isAdding}
          footer={
            <>
              <Button
                variant="secondary"
                onClick={() => setAddOpen(false)}
                disabled={isAdding}
              >
                Cancel
              </Button>
              <Button
                onClick={() => void handleAddMember()}
                disabled={isAdding || !addMemberId.trim()}
                busy={isAdding}
              >
                Add
              </Button>
            </>
          }
        >
          <label className="ui-field">
            <span className="ui-field__label">Type</span>
            <select
              className="ui-input"
              value={addKind}
              onChange={(event) => {
                setAddKind(event.target.value as CollectionMemberKind);
                setAddMemberId("");
              }}
            >
              {MEMBER_KINDS.map((kind) => (
                <option key={kind.id} value={kind.id}>
                  {kind.label}
                </option>
              ))}
            </select>
          </label>
          <label className="ui-field">
            <span className="ui-field__label">Item</span>
            <select
              className="ui-input"
              value={addMemberId}
              onChange={(event) => setAddMemberId(event.target.value)}
            >
              <option value="">Select…</option>
              {candidateOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <TextInput
            label="Or paste ID"
            value={addMemberId}
            onChange={(event) => setAddMemberId(event.target.value)}
            placeholder="Resource ID"
          />
          <TextInput
            label="Why is it here?"
            value={addReason}
            onChange={(event) => setAddReason(event.target.value)}
            placeholder="Added by user"
          />
        </Modal>
      ) : null}

      {pendingDelete ? (
        <ConfirmDialog
          title="Delete collection?"
          description={`Delete “${pendingDelete.name}”? Memberships are removed; documents and knowledge are not.`}
          confirmLabel="Delete"
          tone="danger"
          busy={isDeleting}
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => void handleDelete()}
        />
      ) : null}
    </div>
  );
}
