interface LoadingStateProps {
  label?: string;
}

/** Consistent loading treatment shared across pages. */
export function LoadingState({ label = "Loading…" }: LoadingStateProps) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="loading-spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
