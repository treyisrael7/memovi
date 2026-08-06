import { cx } from "./utils";

export interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  radius?: "sm" | "md" | "lg" | "full";
  className?: string;
  lines?: number;
}

/** Placeholder shimmer for loading content regions. */
export function Skeleton({
  width = "100%",
  height = "1rem",
  radius = "md",
  className,
  lines,
}: SkeletonProps) {
  if (lines && lines > 1) {
    return (
      <div className={cx("ui-skeleton-stack", className)} aria-hidden="true">
        {Array.from({ length: lines }, (_, index) => (
          <span
            key={index}
            className={cx("ui-skeleton", `ui-skeleton--${radius}`)}
            style={{
              width: index === lines - 1 ? "70%" : width,
              height,
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <span
      className={cx("ui-skeleton", `ui-skeleton--${radius}`, className)}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}
