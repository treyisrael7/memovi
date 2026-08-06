import type { ReactNode } from "react";

import { cx } from "./utils";

export type AlertTone = "ok" | "warn" | "bad" | "info";

export interface AlertProps {
  tone?: AlertTone;
  children: ReactNode;
  className?: string;
  role?: "alert" | "status";
}

/** Inline banner for page-level feedback (errors, warnings, success). */
export function Alert({
  tone = "info",
  children,
  className,
  role,
}: AlertProps) {
  const resolvedRole =
    role ?? (tone === "bad" ? "alert" : tone === "warn" ? "status" : "status");
  const dataTone = tone === "info" ? "ok" : tone;

  return (
    <div
      className={cx("banner", "ui-alert", className)}
      data-tone={dataTone}
      role={resolvedRole}
    >
      {children}
    </div>
  );
}
