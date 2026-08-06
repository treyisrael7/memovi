import type { HTMLAttributes, ReactNode } from "react";

import { cx } from "./utils";

export interface PageLayoutProps extends HTMLAttributes<HTMLElement> {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  /** Use the bordered panel surface (default) or a flush content area. */
  variant?: "panel" | "flush";
}

/** Standard page chrome: optional header row + scrollable body. */
export function PageLayout({
  title,
  description,
  actions,
  children,
  variant = "panel",
  className,
  ...rest
}: PageLayoutProps) {
  const hasHeader = Boolean(title || description || actions);

  return (
    <section
      className={cx(
        "ui-page",
        variant === "panel" && "panel",
        className,
      )}
      {...rest}
    >
      {hasHeader ? (
        <header className="ui-page__header">
          <div className="ui-page__heading">
            {title ? <h1>{title}</h1> : null}
            {description ? <p className="lede">{description}</p> : null}
          </div>
          {actions ? <div className="ui-page__actions">{actions}</div> : null}
        </header>
      ) : null}
      <div className="ui-page__body">{children}</div>
    </section>
  );
}
