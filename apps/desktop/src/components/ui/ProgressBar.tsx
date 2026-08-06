import { cx } from "./utils";

export interface ProgressBarProps {
  value: number;
  max?: number;
  label?: string;
  className?: string;
}

/** Determinate progress indicator (0–max). */
export function ProgressBar({
  value,
  max = 100,
  label,
  className,
}: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(value, max));
  const percent = max === 0 ? 0 : Math.round((clamped / max) * 100);

  return (
    <div className={cx("ui-progress", className)}>
      {label ? <span className="ui-progress__label">{label}</span> : null}
      <div
        className="ui-progress__track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={max}
        aria-valuenow={clamped}
        aria-label={label ?? "Progress"}
      >
        <div className="ui-progress__fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
