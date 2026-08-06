import type { SVGProps } from "react";

import { cx } from "./utils";

export type IconName =
  | "search"
  | "check"
  | "close"
  | "chevron-down"
  | "chevron-right"
  | "warning"
  | "info"
  | "moon"
  | "sun"
  | "more"
  | "plus"
  | "trash"
  | "upload"
  | "refresh"
  | "external"
  | "home"
  | "document"
  | "chat"
  | "settings";

export type IconSize = "sm" | "md" | "lg";

interface IconProps extends Omit<SVGProps<SVGSVGElement>, "children"> {
  name: IconName;
  size?: IconSize;
  title?: string;
}

const PATHS: Record<IconName, string> = {
  search:
    "M11 19a8 8 0 1 1 5.3-14L21 10.7M16.5 16.5 21 21",
  check: "M5 12.5 9.5 17 19 7",
  close: "M6 6 18 18M18 6 6 18",
  "chevron-down": "M6 9l6 6 6-6",
  "chevron-right": "M9 6l6 6-6 6",
  warning:
    "M12 3 2.5 20h19L12 3Zm0 6v5M12 17.5h.01",
  info: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 8v5M12 8h.01",
  moon: "M19 14.5A7.5 7.5 0 1 1 9.5 5 6 6 0 0 0 19 14.5Z",
  sun: "M12 4V2M12 22v-2M4.9 4.9 3.5 3.5M20.5 20.5 19.1 19.1M4 12H2M22 12h-2M4.9 19.1 3.5 20.5M20.5 3.5 19.1 4.9M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z",
  more: "M6 12h.01M12 12h.01M18 12h.01",
  plus: "M12 5v14M5 12h14",
  trash: "M5 7h14M9 7V5h6v2M8 7l1 12h6l1-12",
  upload: "M12 16V5M8 9l4-4 4 4M5 19h14",
  refresh:
    "M4 12a8 8 0 0 1 13.5-5.8M20 12a8 8 0 0 1-13.5 5.8M16 4v4h4M8 20v-4H4",
  external: "M10 5h9v9M19 5 10 14M5 9v10h10",
  home: "M4 11.5 12 4l8 7.5V20H4v-8.5ZM9 20v-6h6v6",
  document: "M7 3h7l5 5v13H7V3Zm7 0v5h5",
  chat: "M5 5h14v10H9l-4 4V5Z",
  settings:
    "M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7ZM4.5 12h2M17.5 12h2M6.5 6.5l1.4 1.4M16.1 16.1l1.4 1.4M6.5 17.5l1.4-1.4M16.1 7.9l1.4-1.4",
};

/**
 * Lightweight inline SVG icon set for the desktop design system.
 * Prefer these over ad-hoc Unicode glyphs for interactive UI.
 */
export function Icon({
  name,
  size = "md",
  title,
  className,
  ...rest
}: IconProps) {
  const labelled = Boolean(title);
  return (
    <svg
      className={cx("ui-icon", `ui-icon--${size}`, className)}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={labelled ? undefined : true}
      role={labelled ? "img" : undefined}
      aria-label={title}
      {...rest}
    >
      {title ? <title>{title}</title> : null}
      <path d={PATHS[name]} />
    </svg>
  );
}
