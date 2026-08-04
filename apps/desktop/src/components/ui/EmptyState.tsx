import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

/** Consistent empty-state treatment shared across list and detail panes. */
export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <p className="empty-state-title">{title}</p>
      {description ? (
        <p className="empty-state-description">{description}</p>
      ) : null}
      {action ? <div className="empty-state-action">{action}</div> : null}
    </div>
  );
}
