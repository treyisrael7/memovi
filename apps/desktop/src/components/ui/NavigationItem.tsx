import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cx } from "./utils";

export interface NavigationItemProps
  extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  active?: boolean;
  icon?: ReactNode;
}

/** Primary or secondary navigation control with active state. */
export function NavigationItem({
  label,
  active = false,
  icon,
  className,
  type = "button",
  ...rest
}: NavigationItemProps) {
  return (
    <button
      type={type}
      className={cx("nav-item", "ui-nav-item", className)}
      data-active={active}
      aria-current={active ? "page" : undefined}
      {...rest}
    >
      {icon ? <span className="ui-nav-item__icon">{icon}</span> : null}
      <span className="nav-label">{label}</span>
    </button>
  );
}
