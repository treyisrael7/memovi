import {
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { cx } from "./utils";

export interface TooltipProps {
  content: string;
  children: ReactNode;
  side?: "top" | "bottom";
  className?: string;
}

/** Hover/focus tooltip. Content is announced via aria-describedby. */
export function Tooltip({
  content,
  children,
  side = "top",
  className,
}: TooltipProps) {
  const [open, setOpen] = useState(false);
  const tooltipId = useId();
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
    };
  }, []);

  function show() {
    if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
    setOpen(true);
  }

  function hide() {
    timeoutRef.current = window.setTimeout(() => setOpen(false), 80);
  }

  return (
    <span
      className={cx("ui-tooltip", className)}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      <span aria-describedby={open ? tooltipId : undefined}>{children}</span>
      {open ? (
        <span
          id={tooltipId}
          role="tooltip"
          className="ui-tooltip__content"
          data-side={side}
        >
          {content}
        </span>
      ) : null}
    </span>
  );
}
