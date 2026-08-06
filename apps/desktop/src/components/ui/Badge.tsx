import { cx } from "./utils";

export type BadgeTone = "ok" | "warn" | "bad" | "idle" | "accent" | "neutral";

export interface BadgeProps {
  label: string;
  tone?: BadgeTone;
  className?: string;
}

/** Compact label pill for status and metadata. */
export function Badge({ label, tone = "neutral", className }: BadgeProps) {
  return (
    <span className={cx("status-badge", "ui-badge", className)} data-tone={tone}>
      {label}
    </span>
  );
}
