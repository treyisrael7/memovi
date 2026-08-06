import type { ReactNode } from "react";

import { cx } from "./utils";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

/** Consistent empty-state treatment shared across list and detail panes. */
export function EmptyState({
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cx("empty-state", className)}>
      <p className="empty-state-title">{title}</p>
      {description ? (
        <p className="empty-state-description">{description}</p>
      ) : null}
      {action ? <div className="empty-state-action">{action}</div> : null}
    </div>
  );
}
