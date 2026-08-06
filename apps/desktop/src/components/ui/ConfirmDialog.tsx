import { Button } from "./Button";
import { Modal } from "./Modal";

export interface ConfirmationDialogProps {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "default" | "danger";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Consistent modal confirmation used for destructive or high-stakes actions. */
export function ConfirmationDialog({
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "default",
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmationDialogProps) {
  return (
    <Modal
      title={title}
      busy={busy}
      onClose={onCancel}
      role="alertdialog"
      footer={
        <>
          <Button variant="secondary" onClick={onCancel} disabled={busy}>
            {cancelLabel}
          </Button>
          <Button
            variant={tone === "danger" ? "danger" : "primary"}
            onClick={onConfirm}
            busy={busy}
          >
            {busy ? "Working…" : confirmLabel}
          </Button>
        </>
      }
    >
      {description ? <p className="dialog-description">{description}</p> : null}
    </Modal>
  );
}

/** @deprecated Prefer ConfirmationDialog — kept for existing page imports. */
export const ConfirmDialog = ConfirmationDialog;
