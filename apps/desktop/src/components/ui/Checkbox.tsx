import type { InputHTMLAttributes } from "react";

import { cx } from "./utils";

export interface CheckboxProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: string;
}

/** Accessible checkbox with visible label. */
export function Checkbox({ label, className, id, ...rest }: CheckboxProps) {
  const inputId = id ?? rest.name;
  return (
    <label className={cx("ui-checkbox", className)}>
      <input id={inputId} type="checkbox" className="ui-checkbox__input" {...rest} />
      <span className="ui-checkbox__label">{label}</span>
    </label>
  );
}
