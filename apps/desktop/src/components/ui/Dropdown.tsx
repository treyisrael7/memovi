import type { SelectHTMLAttributes } from "react";

import { cx } from "./utils";

export interface DropdownOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface DropdownProps
  extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "children"> {
  label?: string;
  options: DropdownOption[];
  placeholder?: string;
}

/** Native select styled as a design-system dropdown. */
export function Dropdown({
  label,
  options,
  placeholder,
  id,
  className,
  ...rest
}: DropdownProps) {
  const selectId = id ?? rest.name;
  return (
    <label className={cx("ui-field", className)}>
      {label ? <span className="ui-field__label">{label}</span> : null}
      <select id={selectId} className="ui-select" {...rest}>
        {placeholder ? (
          <option value="" disabled={rest.required}>
            {placeholder}
          </option>
        ) : null}
        {options.map((option) => (
          <option
            key={option.value}
            value={option.value}
            disabled={option.disabled}
          >
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
