import { LoadingSpinner } from "./LoadingSpinner";
import { cx } from "./utils";

interface LoadingStateProps {
  label?: string;
  className?: string;
}

/** Consistent loading treatment shared across pages. */
export function LoadingState({
  label = "Loading…",
  className,
}: LoadingStateProps) {
  return (
    <div className={cx("loading-state", className)} role="status" aria-live="polite">
      <LoadingSpinner size="md" />
      <span>{label}</span>
    </div>
  );
}
