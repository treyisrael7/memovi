import {
  useId,
  useRef,
  useState,
  type ChangeEvent,
  type ReactNode,
} from "react";

import { pickDirectory } from "../../native/dialog";
import { Button } from "./Button";
import { cx } from "./utils";

interface FilePickerBaseProps {
  label?: string;
  disabled?: boolean;
  buttonLabel?: string;
  children?: ReactNode;
  className?: string;
}

export interface FilePickerFilesProps extends FilePickerBaseProps {
  mode?: "files";
  accept?: string;
  multiple?: boolean;
  onFilesSelected: (files: FileList) => void;
}

export interface FilePickerDirectoryProps extends FilePickerBaseProps {
  mode: "directory";
  dialogTitle?: string;
  defaultPath?: string;
  onDirectorySelected: (path: string) => void;
}

export type FilePickerProps = FilePickerFilesProps | FilePickerDirectoryProps;

/** Hidden file input or native OS folder dialog, triggered by a design-system button. */
export function FilePicker(props: FilePickerProps) {
  if (props.mode === "directory") {
    return <DirectoryPicker {...props} />;
  }
  return <FilesPicker {...props} />;
}

function FilesPicker({
  label = "Choose files",
  accept,
  multiple = true,
  disabled = false,
  buttonLabel = "Browse files",
  onFilesSelected,
  children,
  className,
}: FilePickerFilesProps) {
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

function DirectoryPicker({
  label = "Choose folder",
  disabled = false,
  buttonLabel = "Browse...",
  dialogTitle = "Select folder",
  defaultPath,
  onDirectorySelected,
  children,
  className,
}: FilePickerDirectoryProps) {
  const [isPicking, setIsPicking] = useState(false);

  async function handleBrowse() {
    if (disabled || isPicking) return;
    setIsPicking(true);
    try {
      const selected = await pickDirectory({
        title: dialogTitle,
        defaultPath: defaultPath?.trim() || undefined,
      });
      if (selected) {
        onDirectorySelected(selected);
      }
    } finally {
      setIsPicking(false);
    }
  }

  return (
    <div className={cx("ui-file-picker", className)}>
      {children ?? (
        <Button
          variant="secondary"
          disabled={disabled || isPicking}
          onClick={() => void handleBrowse()}
        >
          {buttonLabel}
        </Button>
      )}
      <span className="visually-hidden">{label}</span>
    </div>
  );
}
