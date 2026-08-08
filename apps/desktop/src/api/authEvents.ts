/**
 * Lightweight bridge so the shared HTTP client can notify the auth layer when
 * the backend rejects a session, without importing React state into transport.
 */

type UnauthorizedListener = () => void;

let unauthorizedListener: UnauthorizedListener | null = null;

export function onUnauthorized(listener: UnauthorizedListener): () => void {
  unauthorizedListener = listener;
  return () => {
    if (unauthorizedListener === listener) {
      unauthorizedListener = null;
    }
  };
}

export function notifyUnauthorized(): void {
  unauthorizedListener?.();
}

/**
 * 401s on these paths are expected credential/session-check outcomes, not
 * mid-session expiry events that should kick the user out of the shell.
 */
export function shouldSuppressUnauthorizedNotify(path: string): boolean {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return (
    normalized === "/auth/login" ||
    normalized === "/auth/register" ||
    normalized === "/auth/me" ||
    normalized === "/auth/logout"
  );
}
