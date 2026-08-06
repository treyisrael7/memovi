import type { ButtonHTMLAttributes, ReactNode } from "react";

import { LoadingSpinner } from "./LoadingSpinner";
import { cx } from "./utils";

export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
export type ButtonSize = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  busy?: boolean;
  children: ReactNode;
}

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: "primary-button",
  secondary: "retry-button",
  danger: "danger-button",
  ghost: "ui-button--ghost",
};

/** Primary interactive control. Prefer this over raw button classNames. */
export function Button({
  variant = "primary",
  size = "md",
  busy = false,
  disabled,
  className,
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cx(
        "ui-button",
        VARIANT_CLASS[variant],
        size === "sm" && "ui-button--sm",
        className,
      )}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy ? <LoadingSpinner size="sm" label={undefined} /> : null}
      <span className="ui-button__label">{children}</span>
    </button>
  );
}
