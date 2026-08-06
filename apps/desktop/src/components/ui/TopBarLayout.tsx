import type { HTMLAttributes, ReactNode } from "react";

import { cx } from "./utils";

export interface TopBarLayoutProps extends HTMLAttributes<HTMLElement> {
  left?: ReactNode;
  right?: ReactNode;
  children?: ReactNode;
}

/**
 * Structural top bar frame for application chrome.
 * Clusters content into left / right regions by default.
 */
export function TopBarLayout({
  left,
  right,
  children,
  className,
  ...rest
}: TopBarLayoutProps) {
  return (
    <header className={cx("top-bar", "ui-topbar", className)} {...rest}>
      {children ?? (
        <>
          <div className="top-bar-cluster">{left}</div>
          <div className="top-bar-cluster">{right}</div>
        </>
      )}
    </header>
  );
}

/** @deprecated Prefer TopBarLayout — alias matches design-system naming. */
export const TopBar = TopBarLayout;
