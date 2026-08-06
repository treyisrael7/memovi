import { cx } from "./utils";

export type SpinnerSize = "sm" | "md" | "lg";

export interface LoadingSpinnerProps {
  size?: SpinnerSize;
  label?: string;
  className?: string;
}

/** Indeterminate spinner. Pair with LoadingState for labeled loading UX. */
export function LoadingSpinner({
  size = "md",
  label,
  className,
}: LoadingSpinnerProps) {
  return (
    <span
      className={cx("loading-spinner", `ui-spinner--${size}`, className)}
      role={label ? "status" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    />
  );
}
