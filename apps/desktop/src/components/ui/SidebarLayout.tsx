import type { HTMLAttributes, ReactNode } from "react";

import { cx } from "./utils";

export interface SidebarLayoutProps extends HTMLAttributes<HTMLElement> {
  brand?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
}

/**
 * Structural sidebar frame for application chrome.
 * App-specific navigation content is passed as children.
 */
export function SidebarLayout({
  brand,
  footer,
  children,
  className,
  ...rest
}: SidebarLayoutProps) {
  return (
    <aside className={cx("sidebar", "ui-sidebar", className)} {...rest}>
      {brand ? <div className="brand">{brand}</div> : null}
      <div className="ui-sidebar__body">{children}</div>
      {footer ? <div className="sidebar-footer">{footer}</div> : null}
    </aside>
  );
}

/** @deprecated Prefer SidebarLayout — alias matches design-system naming. */
export const Sidebar = SidebarLayout;
