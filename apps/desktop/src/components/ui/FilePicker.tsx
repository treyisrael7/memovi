import { useId, useRef, type ChangeEvent, type ReactNode } from "react";

import { Button } from "./Button";
import { cx } from "./utils";

export interface FilePickerProps {
  label?: string;
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
  buttonLabel?: string;
  onFilesSelected: (files: FileList) => void;
  children?: ReactNode;
  className?: string;
}

/** Hidden file input triggered by a design-system button. */
export function FilePicker({
  label = "Choose files",
  accept,
  multiple = true,
  disabled = false,
  buttonLabel = "Browse files",
  onFilesSelected,
  children,
  className,
}: FilePickerProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const inputId = useId();

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files && event.target.files.length > 0) {
      onFilesSelected(event.target.files);
      event.target.value = "";
    }
  }

  return (
    <div className={cx("ui-file-picker", className)}>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        className="visually-hidden"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        onChange={handleChange}
      />
      {children ?? (
        <Button
          variant="secondary"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          aria-controls={inputId}
        >
          {buttonLabel}
        </Button>
      )}
      <span className="visually-hidden">{label}</span>
    </div>
  );
}
