import { cx } from "./utils";

export interface BreadcrumbItem {
  id: string;
  label: string;
  onSelect?: () => void;
}

export interface BreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
}

/** Hierarchical location trail. Last item is the current page. */
export function Breadcrumb({ items, className }: BreadcrumbProps) {
  return (
    <nav className={cx("ui-breadcrumb", className)} aria-label="Breadcrumb">
      <ol className="ui-breadcrumb__list">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={item.id} className="ui-breadcrumb__item">
              {isLast || !item.onSelect ? (
                <span aria-current={isLast ? "page" : undefined}>
                  {item.label}
                </span>
              ) : (
                <button
                  type="button"
                  className="ui-breadcrumb__link"
                  onClick={item.onSelect}
                >
                  {item.label}
                </button>
              )}
              {!isLast ? (
                <span className="ui-breadcrumb__sep" aria-hidden="true">
                  /
                </span>
              ) : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
