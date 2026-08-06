import type { ReactNode } from "react";

import { cx } from "./utils";

export interface TabItem {
  id: string;
  label: string;
  disabled?: boolean;
}

export interface TabsProps {
  items: TabItem[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
  "aria-label"?: string;
}

export interface TabPanelProps {
  id: string;
  activeId: string;
  children: ReactNode;
  className?: string;
}

/** Horizontal tab list for switching peer views. */
export function Tabs({
  items,
  value,
  onChange,
  className,
  "aria-label": ariaLabel = "Tabs",
}: TabsProps) {
  return (
    <div
      className={cx("ui-tabs", "search-tabs", className)}
      role="tablist"
      aria-label={ariaLabel}
    >
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          id={`tab-${item.id}`}
          className={cx("ui-tab", "search-tab")}
          aria-selected={value === item.id}
          data-active={value === item.id}
          disabled={item.disabled}
          tabIndex={value === item.id ? 0 : -1}
          onClick={() => onChange(item.id)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function TabPanel({
  id,
  activeId,
  children,
  className,
}: TabPanelProps) {
  if (id !== activeId) return null;
  return (
    <div
      className={cx("ui-tab-panel", className)}
      role="tabpanel"
      id={`panel-${id}`}
      aria-labelledby={`tab-${id}`}
    >
      {children}
    </div>
  );
}
