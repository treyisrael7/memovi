import type { CSSProperties } from "react";

import { cx } from "./utils";

export interface TagChipItem {
  id: string;
  name: string;
  color?: string | null;
}

export interface TagChipsProps {
  tags: ReadonlyArray<TagChipItem>;
  selectedIds?: ReadonlySet<string> | ReadonlyArray<string>;
  onToggle?: (tagId: string) => void;
  className?: string;
  size?: "sm" | "md";
}

function isSelected(
  selectedIds: TagChipsProps["selectedIds"],
  id: string,
): boolean {
  if (!selectedIds) return false;
  if (selectedIds instanceof Set) return selectedIds.has(id);
  return (selectedIds as ReadonlyArray<string>).includes(id);
}

export function TagChips({
  tags,
  selectedIds,
  onToggle,
  className,
  size = "md",
}: TagChipsProps) {
  const interactive = typeof onToggle === "function";

  return (
    <div className={cx("tag-chips", className)} role={interactive ? "group" : undefined}>
      {tags.map((tag) => {
        const selected = isSelected(selectedIds, tag.id);
        const style = tag.color
          ? ({
              "--tag-chip-color": tag.color,
            } as CSSProperties)
          : undefined;
        const classNames = cx(
          "tag-chip",
          size === "sm" && "tag-chip--sm",
          selected && "tag-chip--selected",
          interactive && "tag-chip--interactive",
        );

        if (interactive) {
          return (
            <button
              key={tag.id}
              type="button"
              className={classNames}
              style={style}
              data-selected={selected}
              aria-pressed={selected}
              onClick={() => onToggle(tag.id)}
            >
              <span className="tag-chip__swatch" aria-hidden />
              {tag.name}
            </button>
          );
        }

        return (
          <span key={tag.id} className={classNames} style={style}>
            <span className="tag-chip__swatch" aria-hidden />
            {tag.name}
          </span>
        );
      })}
    </div>
  );
}
