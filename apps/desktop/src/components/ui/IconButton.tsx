import type { ButtonHTMLAttributes } from "react";

import { Icon, type IconName, type IconSize } from "./Icon";
import { cx } from "./utils";

export interface IconButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  icon: IconName;
  label: string;
  size?: IconSize;
  variant?: "ghost" | "secondary";
}

/** Icon-only button with a required accessible label. */
export function IconButton({
  icon,
  label,
  size = "md",
  variant = "ghost",
  className,
  type = "button",
  ...rest
}: IconButtonProps) {
  return (
    <button
      type={type}
      className={cx(
        "ui-icon-button",
        variant === "secondary" && "retry-button",
        className,
      )}
      aria-label={label}
      title={label}
      {...rest}
    >
      <Icon name={icon} size={size} />
    </button>
  );
}
