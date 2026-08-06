import type { TextareaHTMLAttributes } from "react";

import { cx } from "./utils";

export interface TextAreaProps
  extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
}

/** Multi-line text field with optional label and error message. */
export function TextArea({
  label,
  hint,
  error,
  id,
  className,
  ...rest
}: TextAreaProps) {
  const inputId = id ?? rest.name;
  const describedBy = error
    ? `${inputId}-error`
    : hint
      ? `${inputId}-hint`
      : undefined;

  return (
    <label className={cx("ui-field", className)}>
      {label ? <span className="ui-field__label">{label}</span> : null}
      <textarea
        id={inputId}
        className={cx("ui-textarea", error && "ui-input--error")}
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
