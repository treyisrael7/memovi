import { useAppState } from "../state/AppStateContext";
import { Button } from "./ui/Button";
import { Modal } from "./ui/Modal";

/** Shown when a protected API call returns 401 while the shell was authenticated. */
export function SessionExpiredDialog() {
  const { authStatus, acknowledgeSessionExpired } = useAppState();

  if (authStatus !== "session_expired") {
    return null;
  }

  return (
    <Modal
      title="Session expired"
      role="alertdialog"
      size="sm"
      onClose={acknowledgeSessionExpired}
      footer={
        <Button variant="primary" onClick={acknowledgeSessionExpired}>
          Sign in again
        </Button>
      }
    >
      <p className="dialog-description">
        Your Memovi session is no longer valid. Sign in again to continue
        working in your workspace.
      </p>
    </Modal>
  );
}
