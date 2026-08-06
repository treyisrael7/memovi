import { useEffect, useId, useRef, type ReactNode } from "react";

import { cx } from "./utils";

export interface ModalProps {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  onClose: () => void;
  busy?: boolean;
  className?: string;
  size?: "sm" | "md" | "lg";
  /** Use alertdialog for confirmations that interrupt the user. */
  role?: "dialog" | "alertdialog";
}

/** Focus-trapping modal dialog. Escape and overlay click dismiss when not busy. */
export function Modal({
  title,
  children,
  footer,
  onClose,
  busy = false,
  className,
  size = "md",
  role = "dialog",
}: ModalProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const dialog = dialogRef.current;
    const focusable = dialog?.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    focusable?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !busy) {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !dialog) return;

      const nodes = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (nodes.length === 0) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [busy, onClose]);

  return (
    <div
      className="dialog-overlay"
      role="presentation"
      onClick={() => !busy && onClose()}
    >
      <div
        ref={dialogRef}
        className={cx("dialog", "ui-modal", `ui-modal--${size}`, className)}
        role={role}
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id={titleId}>{title}</h2>
        <div className="ui-modal__body">{children}</div>
        {footer ? <div className="dialog-actions">{footer}</div> : null}
      </div>
    </div>
  );
}
