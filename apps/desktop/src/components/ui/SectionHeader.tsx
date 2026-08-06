import type { HTMLAttributes, ReactNode } from "react";

import { cx } from "./utils";

export interface SectionHeaderProps extends HTMLAttributes<HTMLElement> {
  title: string;
  description?: string;
  actions?: ReactNode;
  level?: 1 | 2 | 3;
}

/** Consistent section title row used inside pages and inspectors. */
export function SectionHeader({
  title,
  description,
  actions,
  level = 2,
  className,
  ...rest
}: SectionHeaderProps) {
  const HeadingTag = level === 1 ? "h1" : level === 3 ? "h3" : "h2";
  return (
    <header className={cx("ui-section-header", className)} {...rest}>
      <div className="ui-section-header__text">
        <HeadingTag>{title}</HeadingTag>
        {description ? <p>{description}</p> : null}
      </div>
      {actions ? (
        <div className="ui-section-header__actions">{actions}</div>
      ) : null}
    </header>
  );
}
