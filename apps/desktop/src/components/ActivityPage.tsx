import { useEffect, useMemo, useState } from "react";

import { listExecutionAudit } from "../api/capabilities";
import { ApiRequestError } from "../api/client";
import { listDocuments } from "../api/documents";
import { listKnowledge } from "../api/memory";
import { listWorkflowHistory } from "../api/workflows";
import { useAppState } from "../state/AppStateContext";
import { Alert } from "./ui/Alert";
import { EmptyState } from "./ui/EmptyState";
import { LoadingState } from "./ui/LoadingState";
import { SectionHeader } from "./ui/SectionHeader";
import { Tabs } from "./ui/Tabs";

type ActivityKind =
  | "document_uploaded"
  | "processing_completed"
  | "processing_failed"
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
  processing_completed: "\u2713",
  processing_failed: "!",
  knowledge_extracted: "\u2726",
  workflow_executed: "\u21bb",
  capability_executed: "\u26a1",
};

const KIND_FILTERS: ReadonlyArray<{ id: ActivityKind | "all"; label: string }> =
  [
    { id: "all", label: "All" },
    { id: "document_uploaded", label: "Uploads" },
    { id: "processing_completed", label: "Processing" },
    { id: "knowledge_extracted", label: "Knowledge" },
    { id: "workflow_executed", label: "Workflows" },
    { id: "capability_executed", label: "Capabilities" },
  ];

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function ActivityPage() {
  const { activeWorkspace, connection } = useAppState();
  const workspaceId = activeWorkspace?.id ?? null;
  const canUseBackend =
    connection.status === "connected" || connection.status === "degraded";

  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [filter, setFilter] = useState<ActivityKind | "all">("all");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId || !canUseBackend) {
      setEvents([]);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    void Promise.all([
      listDocuments(workspaceId),
      listKnowledge(workspaceId),
      listWorkflowHistory(workspaceId),
      listExecutionAudit(workspaceId),
    ])
      .then(([documents, knowledge, workflowHistory, audit]) => {
        if (cancelled) return;
        const collected: ActivityEvent[] = [];

        for (const document of documents.items) {
          collected.push({
            id: `doc-uploaded-${document.id}`,
            kind: "document_uploaded",
            title: `${document.name} imported`,
            detail: document.source_type,
            timestamp: document.created_at,
          });
          if (
            document.processing_status === "completed" &&
            document.processing_updated_at
          ) {
            collected.push({
              id: `doc-completed-${document.id}`,
              kind: "processing_completed",
              title: `${document.name} finished processing`,
              detail: "Knowledge ready",
              timestamp: document.processing_updated_at,
            });
          } else if (
            document.processing_status === "failed" &&
            document.processing_updated_at
          ) {
            collected.push({
              id: `doc-failed-${document.id}`,
              kind: "processing_failed",
              title: `${document.name} failed to process`,
              detail: document.processing_failure_reason ?? undefined,
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
      })
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
  }, [workspaceId, canUseBackend]);

  const filteredEvents = useMemo(
    () =>
      filter === "all"
        ? events
        : events.filter((event) => event.kind === filter),
    [events, filter],
  );

  return (
    <div className="activity-page">
      <SectionHeader
        title="Activity"
        description="A timeline of ingestion, knowledge, and capability events in this workspace."
        level={1}
      />
      <Tabs
        aria-label="Activity filters"
        className="activity-filters"
        value={filter}
        onChange={(id) => setFilter(id as ActivityKind | "all")}
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
          title="No activity yet"
          description="Import documents or run a workflow to see activity here."
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
