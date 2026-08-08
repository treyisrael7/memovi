import { apiFetch } from "./client";

export interface AuthUser {
  id: string;
  email: string;
  created_at: string;
}

export interface AuthCredentials {
  email: string;
  password: string;
}

export async function registerUser(
  credentials: AuthCredentials,
): Promise<AuthUser> {
  return apiFetch<AuthUser>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
}

export async function loginUser(
  credentials: AuthCredentials,
): Promise<AuthUser> {
  return apiFetch<AuthUser>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
}

export async function logoutUser(): Promise<void> {
  await apiFetch<void>("/auth/logout", { method: "POST" });
}

/** Restores the current session from the HttpOnly cookie, if any. */
export async function getCurrentUser(): Promise<AuthUser> {
  return apiFetch<AuthUser>("/auth/me");
}
