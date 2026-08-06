import type { ReactNode, TableHTMLAttributes } from "react";

import { cx } from "./utils";

export interface TableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  width?: string;
  align?: "left" | "right" | "center";
}

export interface TableProps<T> extends TableHTMLAttributes<HTMLTableElement> {
  columns: TableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  selectedKey?: string | null;
}

/** Simple data table with keyboard-selectable rows. */
export function Table<T>({
  columns,
  rows,
  rowKey,
  emptyMessage = "No items",
  onRowClick,
  selectedKey,
  className,
  ...rest
}: TableProps<T>) {
  return (
    <div className="ui-table-wrap">
      <table className={cx("ui-table", className)} {...rest}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                style={column.width ? { width: column.width } : undefined}
                data-align={column.align ?? "left"}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="ui-table__empty">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row) => {
              const key = rowKey(row);
              const interactive = Boolean(onRowClick);
              return (
                <tr
                  key={key}
                  data-selected={selectedKey === key}
                  data-interactive={interactive || undefined}
                  tabIndex={interactive ? 0 : undefined}
                  onClick={interactive ? () => onRowClick?.(row) : undefined}
                  onKeyDown={
                    interactive
                      ? (event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            onRowClick?.(row);
                          }
                        }
                      : undefined
                  }
                >
                  {columns.map((column) => (
                    <td key={column.key} data-align={column.align ?? "left"}>
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
