import { useCallback, useEffect, useMemo, useState } from "react";

import { listExecutionAudit } from "../api/capabilities";
import { ApiRequestError } from "../api/client";
import { listDocuments } from "../api/documents";
import { listKnowledge } from "../api/memory";
import { listWorkflowHistory } from "../api/workflows";
import {
  isProcessingInFlight,
  presentProcessingStatus,
  shouldPollProcessing,
} from "../documents/processingPresentation";
import { useAppState } from "../state/AppStateContext";
import { Alert } from "./ui/Alert";
import { EmptyState } from "./ui/EmptyState";
import { LoadingState } from "./ui/LoadingState";
import { SectionHeader } from "./ui/SectionHeader";
import { Tabs } from "./ui/Tabs";

type ActivityKind =
  | "document_uploaded"
  | "processing_started"
  | "processing_completed"
  | "processing_failed"
  | "reindex_requested"
  | "knowledge_extracted"
  | "workflow_executed"
  | "capability_executed";

interface ActivityEvent {
  id: string;
  kind: ActivityKind;
  title: string;
  detail?: string;
  timestamp: string;
}

const KIND_ICON: Record<ActivityKind, string> = {
  document_uploaded: "\u2191",
  processing_started: "\u25B6",
  processing_completed: "\u2713",
  processing_failed: "!",
  reindex_requested: "\u21BB",
  knowledge_extracted: "\u2726",
  workflow_executed: "\u21bb",
  capability_executed: "\u26a1",
};

const PROCESSING_KINDS = new Set<ActivityKind>([
  "processing_started",
  "processing_completed",
  "processing_failed",
  "reindex_requested",
]);

const KIND_FILTERS: ReadonlyArray<{
  id: ActivityKind | "all" | "processing";
  label: string;
}> = [
  { id: "all", label: "All" },
  { id: "document_uploaded", label: "Uploads" },
  { id: "processing", label: "Processing" },
  { id: "knowledge_extracted", label: "Knowledge" },
  { id: "workflow_executed", label: "Workflows" },
  { id: "capability_executed", label: "Capabilities" },
];

const POLL_INTERVAL_MS = 4000;

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function readReprocessHint(documentId: string): string | null {
  try {
    return sessionStorage.getItem(`memovi.reprocess.${documentId}`);
  } catch {
    return null;
  }
}

export function ActivityPage() {
  const { activeWorkspace, connection } = useAppState();
  const workspaceId = activeWorkspace?.id ?? null;
  const canUseBackend =
    connection.status === "connected" || connection.status === "degraded";

  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [filter, setFilter] = useState<ActivityKind | "all" | "processing">(
    "all",
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shouldPoll, setShouldPoll] = useState(false);

  const loadActivity = useCallback(async () => {
    if (!workspaceId || !canUseBackend) {
      setEvents([]);
      setShouldPoll(false);
      return;
    }

    const [documents, knowledge, workflowHistory, audit] = await Promise.all([
      listDocuments(workspaceId),
      listKnowledge(workspaceId),
      listWorkflowHistory(workspaceId),
      listExecutionAudit(workspaceId),
    ]);

    const knowledgeByDocument = new Set(
      knowledge.items.map((item) => item.document_id),
    );
    const collected: ActivityEvent[] = [];

    for (const document of documents.items) {
      collected.push({
        id: `doc-uploaded-${document.id}`,
        kind: "document_uploaded",
        title: `Upload started — ${document.name}`,
        detail: document.source_type,
        timestamp: document.created_at,
      });

      const reprocessAt = readReprocessHint(document.id);
      if (reprocessAt) {
        collected.push({
          id: `doc-reindex-${document.id}-${reprocessAt}`,
          kind: "reindex_requested",
          title: `Re-index requested — ${document.name}`,
          detail: "Queued a new processing job",
          timestamp: reprocessAt,
        });
      }

      const view = presentProcessingStatus(document.processing_status, {
        hasKnowledge: knowledgeByDocument.has(document.id),
      });

      if (isProcessingInFlight(document.processing_status)) {
        collected.push({
          id: `doc-processing-${document.id}`,
          kind: "processing_started",
          title: `${document.name} — ${view.label}`,
          detail: view.explanation,
          timestamp:
            document.processing_updated_at ??
            document.processing_started_at ??
            document.created_at,
        });
      } else if (
        document.processing_status === "completed" &&
        document.processing_updated_at
      ) {
        collected.push({
          id: `doc-completed-${document.id}`,
          kind: "processing_completed",
          title: knowledgeByDocument.has(document.id)
            ? `${document.name} is ready`
            : `${document.name} is indexing`,
          detail: knowledgeByDocument.has(document.id)
            ? "Ready to search and ask about"
            : "Generating searchable knowledge",
          timestamp:
            document.processing_completed_at ??
            document.processing_updated_at,
        });
      } else if (
        document.processing_status === "failed" &&
        document.processing_updated_at
      ) {
        collected.push({
          id: `doc-failed-${document.id}`,
          kind: "processing_failed",
          title: `Processing failed — ${document.name}`,
          detail:
            document.processing_failure_reason ??
            "Open Documents and try Retry processing",
          timestamp: document.processing_updated_at,
        });
      } else if (
        document.processing_status === "cancelled" &&
        document.processing_updated_at
      ) {
        collected.push({
          id: `doc-cancelled-${document.id}`,
          kind: "processing_failed",
          title: `Processing cancelled — ${document.name}`,
          detail:
            document.processing_failure_reason ??
            "Open Documents and try Retry processing",
          timestamp: document.processing_updated_at,
        });
      }
    }

    for (const item of knowledge.items) {
      collected.push({
        id: `knowledge-${item.id}`,
        kind: "knowledge_extracted",
        title: item.summary || "Knowledge extracted",
        detail: `${item.chunk_count} chunk${item.chunk_count === 1 ? "" : "s"}`,
        timestamp: item.created_at,
      });
    }

    for (const run of workflowHistory.items) {
      collected.push({
        id: `workflow-${run.instance_id}`,
        kind: "workflow_executed",
        title: `Workflow "${run.workflow_name}" ${run.status}`,
        detail: `${run.executed_capabilities.length} capabilities`,
        timestamp: run.executed_at,
      });
    }

    for (const entry of audit.items) {
      collected.push({
        id: `capability-${entry.id}`,
        kind: "capability_executed",
        title: `${entry.capability_id}: ${entry.operation}`,
        detail: entry.status,
        timestamp: entry.timestamp,
      });
    }

    collected.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
    setEvents(collected);
    setShouldPoll(
      documents.items.some((doc) =>
        shouldPollProcessing(
          doc.processing_status,
          knowledgeByDocument.has(doc.id),
        ),
      ),
    );
  }, [workspaceId, canUseBackend]);

  useEffect(() => {
    if (!workspaceId || !canUseBackend) {
      setEvents([]);
      setShouldPoll(false);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    void loadActivity()
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError
              ? err.message
              : "Failed to load activity.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [workspaceId, canUseBackend, loadActivity]);

  useEffect(() => {
    if (!shouldPoll || !workspaceId || !canUseBackend) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadActivity().catch(() => undefined);
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [shouldPoll, workspaceId, canUseBackend, loadActivity]);

  const filteredEvents = useMemo(() => {
    if (filter === "all") return events;
    if (filter === "processing") {
      return events.filter((event) => PROCESSING_KINDS.has(event.kind));
    }
    return events.filter((event) => event.kind === filter);
  }, [events, filter]);

  return (
    <div className="activity-page">
      <SectionHeader
        title="Activity"
        description="A timeline of uploads, processing, knowledge, and capability events in this workspace."
        level={1}
      />
      <Tabs
        aria-label="Activity filters"
        className="activity-filters"
        value={filter}
        onChange={(id) =>
          setFilter(id as ActivityKind | "all" | "processing")
        }
        items={KIND_FILTERS.map((entry) => ({
          id: entry.id,
          label: entry.label,
        }))}
      />

      {error ? <Alert tone="bad">{error}</Alert> : null}

      {!canUseBackend ? (
        <EmptyState
          title="Backend unavailable"
          description="Connect to the Memovi backend to see workspace activity."
        />
      ) : isLoading ? (
        <LoadingState label="Loading activity…" />
      ) : filteredEvents.length === 0 ? (
        <EmptyState
          title={
            filter === "processing"
              ? "No processing activity"
              : "No activity yet"
          }
          description={
            filter === "processing"
              ? "Upload a document or reprocess one to see processing events here."
              : "Import documents or run a workflow to see activity here."
          }
        />
      ) : (
        <ul className="activity-timeline">
          {filteredEvents.map((event) => (
            <li key={event.id} className="activity-item">
              <span className="activity-icon" aria-hidden="true">
                {KIND_ICON[event.kind]}
              </span>
              <div className="activity-body">
                <div className="activity-title-row">
                  <span className="activity-title">{event.title}</span>
                  <span className="activity-timestamp">
                    {formatTimestamp(event.timestamp)}
                  </span>
                </div>
                {event.detail ? (
                  <span className="activity-detail">{event.detail}</span>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
