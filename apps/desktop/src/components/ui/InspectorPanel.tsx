import type { HTMLAttributes, ReactNode } from "react";

import { EmptyState } from "./EmptyState";
import { cx } from "./utils";

export interface InspectorPanelProps extends HTMLAttributes<HTMLElement> {
  title?: string;
  actions?: ReactNode;
  children?: ReactNode;
  emptyTitle?: string;
  emptyDescription?: string;
  isEmpty?: boolean;
}

/** Detail / inspector pane used beside list and explorer views. */
export function InspectorPanel({
  title,
  actions,
  children,
  emptyTitle = "Nothing selected",
  emptyDescription,
  isEmpty = false,
  className,
  ...rest
}: InspectorPanelProps) {
  return (
    <aside className={cx("ui-inspector", className)} {...rest}>
      {(title || actions) && (
        <header className="ui-inspector__header">
          {title ? <h2>{title}</h2> : <span />}
          {actions ? <div className="ui-inspector__actions">{actions}</div> : null}
        </header>
      )}
      <div className="ui-inspector__body">
        {isEmpty ? (
          <EmptyState title={emptyTitle} description={emptyDescription} />
        ) : (
          children
        )}
      </div>
    </aside>
  );
}
