import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { cx } from "./utils";

export interface ContextMenuItem {
  id: string;
  label: string;
  danger?: boolean;
  disabled?: boolean;
  onSelect: () => void;
}

export interface ContextMenuProps {
  items: ContextMenuItem[];
  children: ReactNode;
  className?: string;
}

/** Right-click / long-press context menu with keyboard Escape dismiss. */
export function ContextMenu({ items, children, className }: ContextMenuProps) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const rootRef = useRef<HTMLDivElement | null>(null);
  const menuRef = useRef<HTMLUListElement | null>(null);

  useEffect(() => {
    if (!open) return;

    function handlePointer(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    window.addEventListener("mousedown", handlePointer);
    window.addEventListener("keydown", handleKey);
    menuRef.current?.querySelector<HTMLElement>("button")?.focus();

    return () => {
      window.removeEventListener("mousedown", handlePointer);
      window.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  return (
    <div
      ref={rootRef}
      className={cx("ui-context-root", className)}
      onContextMenu={(event) => {
        event.preventDefault();
        setPosition({ x: event.clientX, y: event.clientY });
        setOpen(true);
      }}
    >
      {children}
      {open ? (
        <ul
          ref={menuRef}
          className="ui-context-menu"
          role="menu"
          style={{ top: position.y, left: position.x }}
        >
          {items.map((item) => (
            <li key={item.id} role="none">
              <button
                type="button"
                role="menuitem"
                className={cx(
                  "ui-context-menu__item",
                  item.danger && "ui-context-menu__item--danger",
                )}
                disabled={item.disabled}
                onClick={() => {
                  item.onSelect();
                  setOpen(false);
                }}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
