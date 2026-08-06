import type { InputHTMLAttributes } from "react";

import { cx } from "./utils";

export interface TextInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string;
  hint?: string;
  error?: string;
}

/** Single-line text field with optional label and error message. */
export function TextInput({
  label,
  hint,
  error,
  id,
  className,
  disabled,
  ...rest
}: TextInputProps) {
  const inputId = id ?? rest.name;
  const describedBy = error
    ? `${inputId}-error`
    : hint
      ? `${inputId}-hint`
      : undefined;

  return (
    <label className={cx("ui-field", className)}>
      {label ? <span className="ui-field__label">{label}</span> : null}
      <input
        id={inputId}
        className={cx("ui-input", error && "ui-input--error")}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        {...rest}
      />
      {error ? (
        <span id={`${inputId}-error`} className="ui-field__error" role="alert">
          {error}
        </span>
      ) : hint ? (
        <span id={`${inputId}-hint`} className="ui-field__hint">
          {hint}
        </span>
      ) : null}
    </label>
  );
}
