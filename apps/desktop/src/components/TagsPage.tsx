import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiRequestError } from "../api/client";
import { listConversations } from "../api/conversations";
import { listDocuments } from "../api/documents";
import { listKnowledge } from "../api/memory";
import {
  getResourceMetadata,
  putResourceMetadata,
} from "../api/resourceMetadata";
import {
  assignTag,
  createTag,
  deleteTag,
  listTagAssignments,
  listTags,
  unassignTag,
  updateTag,
  type TagMemberKind,
} from "../api/tags";
import type {
  ConversationSummary,
  DocumentSummary,
  KnowledgeSummary,
  ResourceMetadataResponse,
  TagAssignmentResponse,
  TagListItem,
  WorkflowDefinition,
} from "../api/types";
import { listWorkflows } from "../api/workflows";
import { useAppState } from "../state/AppStateContext";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";
import { ConfirmDialog } from "./ui/ConfirmDialog";
import { EmptyState } from "./ui/EmptyState";
import { LoadingState } from "./ui/LoadingState";
import { Modal } from "./ui/Modal";
import { SearchInput } from "./ui/SearchInput";
import { SectionHeader } from "./ui/SectionHeader";
import { TagChips } from "./ui/TagChips";
import { TextArea } from "./ui/TextArea";
import { TextInput } from "./ui/TextInput";
import { useToast } from "./ui/ToastContext";

const MEMBER_KINDS: ReadonlyArray<{ id: TagMemberKind; label: string }> = [
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

export function TagsPage() {
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

  const [tags, setTags] = useState<TagListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [assignments, setAssignments] = useState<TagAssignmentResponse[]>([]);
  const [assignmentQuery, setAssignmentQuery] = useState("");
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<
    string | null
  >(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createColor, setCreateColor] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const [editOpen, setEditOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editColor, setEditColor] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [isEditing, setIsEditing] = useState(false);

  const [pendingDelete, setPendingDelete] = useState<TagListItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const [addOpen, setAddOpen] = useState(false);
  const [addKind, setAddKind] = useState<TagMemberKind>("document");
  const [addMemberId, setAddMemberId] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeSummary[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([]);

  const [metadata, setMetadata] = useState<ResourceMetadataResponse | null>(
    null,
  );
  const [metadataTitle, setMetadataTitle] = useState("");
  const [metadataDescription, setMetadataDescription] = useState("");
  const [metadataNotes, setMetadataNotes] = useState("");
  const [isMetadataLoading, setIsMetadataLoading] = useState(false);
  const [isSavingMetadata, setIsSavingMetadata] = useState(false);

  const selected = useMemo(
    () => tags.find((item) => item.id === selectedId) ?? null,
    [tags, selectedId],
  );

  const selectedAssignment = useMemo(
    () =>
      assignments.find((item) => item.id === selectedAssignmentId) ?? null,
    [assignments, selectedAssignmentId],
  );

  const refreshList = useCallback(async () => {
    if (!workspaceId || !canUseBackend) {
      setTags([]);
      return;
    }
    const payload = await listTags(workspaceId);
    setTags(payload.items);
    setSelectedId((current) => {
      if (current && payload.items.some((item) => item.id === current)) {
        return current;
      }
      return payload.items[0]?.id ?? null;
    });
  }, [workspaceId, canUseBackend]);

  const refreshDetail = useCallback(
    async (tagId: string, query: string) => {
      if (!workspaceId || !canUseBackend) {
        setAssignments([]);
        return;
      }
      setIsDetailLoading(true);
      try {
        const payload = await listTagAssignments(workspaceId, tagId, {
          q: query.trim() || undefined,
        });
        setAssignments(payload.items);
        setSelectedAssignmentId((current) => {
          if (current && payload.items.some((item) => item.id === current)) {
            return current;
          }
          return null;
        });
      } finally {
        setIsDetailLoading(false);
      }
    },
    [workspaceId, canUseBackend],
  );

  useEffect(() => {
    if (!workspaceId || !canUseBackend) {
      setTags([]);
      setSelectedId(null);
      setAssignments([]);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    void listTags(workspaceId)
      .then((payload) => {
        if (cancelled) return;
        setTags(payload.items);
        setSelectedId(payload.items[0]?.id ?? null);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Failed to load tags.",
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
      setAssignments([]);
      setSelectedAssignmentId(null);
      return;
    }
    let cancelled = false;
    setIsDetailLoading(true);
    setError(null);
    void listTagAssignments(workspaceId, selectedId, {
      q: assignmentQuery.trim() || undefined,
    })
      .then((payload) => {
        if (cancelled) return;
        setAssignments(payload.items);
        setSelectedAssignmentId((current) => {
          if (current && payload.items.some((item) => item.id === current)) {
            return current;
          }
          return null;
        });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Failed to load tag assignments.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setIsDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, workspaceId, canUseBackend, assignmentQuery]);

  useEffect(() => {
    if (!selectedAssignment || !workspaceId || !canUseBackend) {
      setMetadata(null);
      setMetadataTitle("");
      setMetadataDescription("");
      setMetadataNotes("");
      return;
    }
    let cancelled = false;
    setIsMetadataLoading(true);
    void getResourceMetadata(
      workspaceId,
      selectedAssignment.member_kind,
      selectedAssignment.member_id,
    )
      .then((payload) => {
        if (cancelled) return;
        setMetadata(payload);
        setMetadataTitle(payload.title ?? "");
        setMetadataDescription(payload.description ?? "");
        setMetadataNotes(payload.notes ?? "");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiRequestError && err.status === 404) {
          setMetadata(null);
          setMetadataTitle("");
          setMetadataDescription("");
          setMetadataNotes("");
          return;
        }
        showToast(
          err instanceof ApiRequestError
            ? err.message
            : "Failed to load resource metadata.",
          "bad",
        );
      })
      .finally(() => {
        if (!cancelled) setIsMetadataLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedAssignment, workspaceId, canUseBackend, showToast]);

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
      const created = await createTag(workspaceId, {
        name: createName.trim(),
        color: createColor.trim() || null,
        description: createDescription,
      });
      showToast(`Created “${created.name}”.`, "ok");
      setCreateOpen(false);
      setCreateName("");
      setCreateColor("");
      setCreateDescription("");
      await refreshList();
      setSelectedId(created.id);
    } catch (err) {
      showToast(
        err instanceof ApiRequestError ? err.message : "Failed to create tag.",
        "bad",
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function handleEdit() {
    if (!workspaceId || !selectedId || !editName.trim()) return;
    setIsEditing(true);
    try {
      const updated = await updateTag(workspaceId, selectedId, {
        name: editName.trim(),
        color: editColor.trim() || null,
        description: editDescription,
      });
      showToast(`Updated “${updated.name}”.`, "ok");
      setEditOpen(false);
      await refreshList();
      await refreshDetail(selectedId, assignmentQuery);
    } catch (err) {
      showToast(
        err instanceof ApiRequestError ? err.message : "Failed to update tag.",
        "bad",
      );
    } finally {
      setIsEditing(false);
    }
  }

  async function handleDelete() {
    if (!workspaceId || !pendingDelete) return;
    setIsDeleting(true);
    try {
      await deleteTag(workspaceId, pendingDelete.id);
      showToast(`Deleted “${pendingDelete.name}”.`, "ok");
      setPendingDelete(null);
      setSelectedAssignmentId(null);
      await refreshList();
    } catch (err) {
      showToast(
        err instanceof ApiRequestError ? err.message : "Failed to delete tag.",
        "bad",
      );
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleAssign() {
    if (!workspaceId || !selectedId || !addMemberId.trim()) return;
    setIsAdding(true);
    try {
      await assignTag(workspaceId, selectedId, {
        memberKind: addKind,
        memberId: addMemberId.trim(),
      });
      showToast("Tag assigned.", "ok");
      setAddOpen(false);
      setAddMemberId("");
      await refreshList();
      await refreshDetail(selectedId, assignmentQuery);
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to assign tag.",
        "bad",
      );
    } finally {
      setIsAdding(false);
    }
  }

  async function handleUnassign(assignment: TagAssignmentResponse) {
    if (!workspaceId || !selectedId) return;
    try {
      await unassignTag(
        workspaceId,
        selectedId,
        assignment.member_kind,
        assignment.member_id,
      );
      showToast("Assignment removed.", "ok");
      if (selectedAssignmentId === assignment.id) {
        setSelectedAssignmentId(null);
      }
      await refreshList();
      await refreshDetail(selectedId, assignmentQuery);
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to remove assignment.",
        "bad",
      );
    }
  }

  async function handleSaveMetadata() {
    if (!workspaceId || !selectedAssignment) return;
    setIsSavingMetadata(true);
    try {
      const saved = await putResourceMetadata(
        workspaceId,
        selectedAssignment.member_kind,
        selectedAssignment.member_id,
        {
          title: metadataTitle.trim() || null,
          description: metadataDescription.trim() || null,
          notes: metadataNotes.trim() || null,
        },
      );
      setMetadata(saved);
      showToast("Metadata saved.", "ok");
    } catch (err) {
      showToast(
        err instanceof ApiRequestError
          ? err.message
          : "Failed to save metadata.",
        "bad",
      );
    } finally {
      setIsSavingMetadata(false);
    }
  }

  function openAssignment(assignment: TagAssignmentResponse) {
    if (assignment.member_kind === "document") {
      openDocument(assignment.member_id);
      return;
    }
    if (assignment.member_kind === "knowledge") {
      openKnowledgeItem(assignment.member_id);
      return;
    }
    if (assignment.member_kind === "conversation") {
      setActivePage("chat");
      return;
    }
    if (assignment.member_kind === "workflow") {
      setActivePage("workflows");
    }
  }

  return (
    <div className="tags-page">
      <SectionHeader
        title="Tags"
        description="Label documents, knowledge, conversations, and workflows. Tags complement collections and do not change ingestion or ownership."
        level={1}
        actions={
          <Button
            disabled={!canUseBackend || !workspaceId}
            onClick={() => setCreateOpen(true)}
          >
            New tag
          </Button>
        }
      />

      {!canUseBackend ? (
        <Alert tone="warn">Connect to the backend to manage tags.</Alert>
      ) : null}
      {error ? <Alert tone="bad">{error}</Alert> : null}

      <div className="documents-split">
        {isLoading ? (
          <LoadingState label="Loading tags…" />
        ) : tags.length === 0 ? (
          <EmptyState
            title="No tags yet"
            description="Create tags such as urgent, research, or personal to label related knowledge."
            action={
              <Button
                disabled={!canUseBackend || !workspaceId}
                onClick={() => setCreateOpen(true)}
              >
                New tag
              </Button>
            }
          />
        ) : (
          <ul className="documents-list">
            {tags.map((tag) => (
              <li key={tag.id}>
                <button
                  type="button"
                  data-active={tag.id === selectedId}
                  onClick={() => {
                    setSelectedId(tag.id);
                    setSelectedAssignmentId(null);
                  }}
                >
                  <div className="documents-list-title-row">
                    <TagChips
                      tags={[tag]}
                      size="sm"
                      className="tag-list-chip"
                    />
                  </div>
                  <span className="documents-list-meta">
                    {tag.assignment_count} assignment
                    {tag.assignment_count === 1 ? "" : "s"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="document-detail">
          {!selected ? (
            <EmptyState
              title="Select a tag"
              description="Choose a tag to browse assignments and edit resource metadata."
            />
          ) : isDetailLoading && assignments.length === 0 ? (
            <LoadingState label="Loading tag…" />
          ) : (
            <>
              <div className="document-detail-header">
                <div>
                  <h2>{selected.name}</h2>
                  <p className="muted">
                    {selected.description || "No description"}
                  </p>
                  <TagChips tags={[selected]} className="tag-detail-chip" />
                </div>
                <div className="document-detail-actions">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setEditName(selected.name);
                      setEditColor(selected.color ?? "");
                      setEditDescription(selected.description);
                      setEditOpen(true);
                    }}
                  >
                    Edit
                  </Button>
                  <Button variant="secondary" onClick={() => setAddOpen(true)}>
                    Assign
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
                  <dt>Assignments</dt>
                  <dd>{selected.assignment_count}</dd>
                </div>
                <div className="meta-card">
                  <dt>Documents</dt>
                  <dd>{selected.counts_by_kind.document ?? 0}</dd>
                </div>
                <div className="meta-card">
                  <dt>Knowledge</dt>
                  <dd>{selected.counts_by_kind.knowledge ?? 0}</dd>
                </div>
                <div className="meta-card">
                  <dt>Updated</dt>
                  <dd>{formatTimestamp(selected.updated_at)}</dd>
                </div>
              </dl>

              <SectionHeader title="Assignments" />
              <SearchInput
                value={assignmentQuery}
                onChange={(event) => setAssignmentQuery(event.target.value)}
                placeholder="Search assignments by ID or kind…"
              />
              {assignments.length === 0 ? (
                <EmptyState
                  title="No assignments yet"
                  description="Assign this tag to documents, knowledge, conversations, or workflows."
                  action={
                    <Button onClick={() => setAddOpen(true)}>Assign</Button>
                  }
                />
              ) : (
                <ul className="documents-list collection-members">
                  {assignments.map((assignment) => (
                    <li
                      key={assignment.id}
                      className="collection-member-row"
                      data-active={assignment.id === selectedAssignmentId}
                    >
                      <button
                        type="button"
                        className="linkish"
                        onClick={() =>
                          setSelectedAssignmentId(assignment.id)
                        }
                      >
                        {kindLabel(assignment.member_kind)} ·{" "}
                        {assignment.member_id}
                      </button>
                      <p className="muted">
                        assigned {formatTimestamp(assignment.assigned_at)}
                      </p>
                      <div className="document-detail-actions">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => openAssignment(assignment)}
                        >
                          Open
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => void handleUnassign(assignment)}
                        >
                          Remove
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}

              <SectionHeader title="Resource metadata" />
              {!selectedAssignment ? (
                <p className="muted">
                  Select an assignment to view or edit title, description, and
                  notes for that target.
                </p>
              ) : isMetadataLoading ? (
                <LoadingState label="Loading metadata…" />
              ) : (
                <div className="tag-metadata-panel">
                  <p className="muted">
                    {kindLabel(selectedAssignment.member_kind)} ·{" "}
                    {selectedAssignment.member_id}
                    {metadata?.updated_at
                      ? ` · updated ${formatTimestamp(metadata.updated_at)}`
                      : ""}
                  </p>
                  <TextInput
                    label="Title"
                    value={metadataTitle}
                    onChange={(event) => setMetadataTitle(event.target.value)}
                    placeholder="Optional display title"
                  />
                  <TextArea
                    label="Description"
                    value={metadataDescription}
                    onChange={(event) =>
                      setMetadataDescription(event.target.value)
                    }
                    placeholder="Optional description"
                  />
                  <TextArea
                    label="Notes"
                    value={metadataNotes}
                    onChange={(event) => setMetadataNotes(event.target.value)}
                    placeholder="Optional notes"
                  />
                  <Button
                    onClick={() => void handleSaveMetadata()}
                    disabled={isSavingMetadata}
                    busy={isSavingMetadata}
                  >
                    Save metadata
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {createOpen ? (
        <Modal
          title="Create tag"
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
            placeholder="e.g. research"
          />
          <TextInput
            label="Color"
            value={createColor}
            onChange={(event) => setCreateColor(event.target.value)}
            placeholder="Optional CSS color, e.g. #4f8cff"
          />
          <TextArea
            label="Description"
            value={createDescription}
            onChange={(event) => setCreateDescription(event.target.value)}
            placeholder="Optional context for this tag"
          />
        </Modal>
      ) : null}

      {editOpen ? (
        <Modal
          title="Edit tag"
          onClose={() => !isEditing && setEditOpen(false)}
          busy={isEditing}
          footer={
            <>
              <Button
                variant="secondary"
                onClick={() => setEditOpen(false)}
                disabled={isEditing}
              >
                Cancel
              </Button>
              <Button
                onClick={() => void handleEdit()}
                disabled={isEditing || !editName.trim()}
                busy={isEditing}
              >
                Save
              </Button>
            </>
          }
        >
          <TextInput
            label="Name"
            value={editName}
            onChange={(event) => setEditName(event.target.value)}
          />
          <TextInput
            label="Color"
            value={editColor}
            onChange={(event) => setEditColor(event.target.value)}
            placeholder="Optional CSS color"
          />
          <TextArea
            label="Description"
            value={editDescription}
            onChange={(event) => setEditDescription(event.target.value)}
          />
        </Modal>
      ) : null}

      {addOpen ? (
        <Modal
          title="Assign tag"
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
                onClick={() => void handleAssign()}
                disabled={isAdding || !addMemberId.trim()}
                busy={isAdding}
              >
                Assign
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
                setAddKind(event.target.value as TagMemberKind);
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
        </Modal>
      ) : null}

      {pendingDelete ? (
        <ConfirmDialog
          title="Delete tag?"
          description={`Delete “${pendingDelete.name}”? Assignments are removed; documents and knowledge are kept.`}
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
