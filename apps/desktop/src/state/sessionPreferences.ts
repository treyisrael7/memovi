import type { AuthUser } from "../api/auth";
import type { PageId } from "../navigation/pages";
import { getPage } from "../navigation/pages";

const THEME_STORAGE_KEY = "memovi.desktop.theme";
const PAGE_STORAGE_PREFIX = "memovi.desktop.lastPage.";
const WORKSPACE_STORAGE_PREFIX = "memovi.desktop.activeWorkspace.";

export type ThemeMode = "light" | "dark";

export function readStoredTheme(): ThemeMode {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") {
      return stored;
    }
  } catch {
    // Ignore storage failures (private mode, quota, etc.).
  }
  return "light";
}

export function writeStoredTheme(theme: ThemeMode): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Ignore storage failures (private mode, quota, etc.).
  }
}

export function readStoredPage(userId: string): PageId | null {
  try {
    const stored = window.localStorage.getItem(`${PAGE_STORAGE_PREFIX}${userId}`);
    if (!stored) return null;
    getPage(stored as PageId);
    return stored as PageId;
  } catch {
    return null;
  }
}

export function writeStoredPage(userId: string, page: PageId): void {
  try {
    window.localStorage.setItem(`${PAGE_STORAGE_PREFIX}${userId}`, page);
  } catch {
    // Ignore storage failures.
  }
}

export function readStoredWorkspaceId(userId: string): string | null {
  try {
    return window.localStorage.getItem(`${WORKSPACE_STORAGE_PREFIX}${userId}`);
  } catch {
    return null;
  }
}

export function writeStoredWorkspaceId(
  userId: string,
  workspaceId: string,
): void {
  try {
    window.localStorage.setItem(
      `${WORKSPACE_STORAGE_PREFIX}${userId}`,
      workspaceId,
    );
  } catch {
    // Ignore storage failures.
  }
}

/** Friendly copy for auth API failures shown on login/register forms. */
export function formatAuthError(error: unknown): string {
  if (
    error &&
    typeof error === "object" &&
    "kind" in error &&
    (error as { kind?: string }).kind === "network"
  ) {
    return "Cannot reach the Memovi backend. Start it with `task backend`, then retry.";
  }
  if (
    error &&
    typeof error === "object" &&
    "status" in error &&
    "message" in error
  ) {
    const status = (error as { status: number | null }).status;
    const message = String((error as { message: string }).message);
    if (status === 401) {
      return "Email address or password is incorrect.";
    }
    if (status === 409) {
      return "That email is already registered. Try signing in instead.";
    }
    if (status === 422) {
      return message || "Please check your email and password.";
    }
    return message;
  }
  return "Something went wrong. Please try again.";
}

export type { AuthUser };
