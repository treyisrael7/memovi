import type { HTMLAttributes, ReactNode } from "react";

import { cx } from "./utils";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  padding?: "sm" | "md" | "lg";
}

/** Surface container for grouped content. Prefer for interactive groupings. */
export function Card({
  children,
  padding = "md",
  className,
  ...rest
}: CardProps) {
  return (
    <div
      className={cx("ui-card", `ui-card--pad-${padding}`, className)}
      {...rest}
    >
      {children}
    </div>
  );
}
