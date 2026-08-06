import type { InputHTMLAttributes } from "react";

import { Icon } from "./Icon";
import { cx } from "./utils";

export interface SearchInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "size"> {
  label?: string;
}

/** Search field with leading icon and type=search semantics. */
export function SearchInput({
  label = "Search",
  className,
  id,
  ...rest
}: SearchInputProps) {
  const inputId = id ?? "search-input";
  return (
    <label className={cx("ui-search", className)}>
      <span className="visually-hidden">{label}</span>
      <Icon name="search" size="sm" className="ui-search__icon" />
      <input
        id={inputId}
        type="search"
        className="ui-search__input"
        enterKeyHint="search"
        {...rest}
      />
    </label>
  );
}
