import type { HTMLAttributes, ReactNode } from "react";

import { cx } from "./utils";

export interface ListProps extends HTMLAttributes<HTMLUListElement> {
  children: ReactNode;
  density?: "comfortable" | "compact";
}

export interface ListItemProps extends HTMLAttributes<HTMLLIElement> {
  children: ReactNode;
  active?: boolean;
  interactive?: boolean;
}

/** Vertical list container for navigation and result lists. */
export function List({
  children,
  density = "comfortable",
  className,
  ...rest
}: ListProps) {
  return (
    <ul
      className={cx("ui-list", `ui-list--${density}`, className)}
      {...rest}
    >
      {children}
    </ul>
  );
}

export function ListItem({
  children,
  active = false,
  interactive = false,
  className,
  ...rest
}: ListItemProps) {
  return (
    <li
      className={cx(
        "ui-list__item",
        interactive && "ui-list__item--interactive",
        className,
      )}
      data-active={active}
      {...rest}
    >
      {children}
    </li>
  );
}
