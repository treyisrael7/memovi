import type { ButtonHTMLAttributes } from "react";

import { cx } from "./utils";

export interface ToggleProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onChange"> {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label: string;
  hideLabel?: boolean;
}

/** On/off switch with an accessible pressed state. */
export function Toggle({
  checked,
  onCheckedChange,
  label,
  hideLabel = false,
  className,
  disabled,
  ...rest
}: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={hideLabel ? label : undefined}
      className={cx("ui-toggle", className)}
      data-checked={checked}
      disabled={disabled}
      onClick={() => onCheckedChange(!checked)}
      {...rest}
    >
      <span className="ui-toggle__track" aria-hidden="true">
        <span className="ui-toggle__thumb" />
      </span>
      {hideLabel ? null : <span className="ui-toggle__label">{label}</span>}
    </button>
  );
}
