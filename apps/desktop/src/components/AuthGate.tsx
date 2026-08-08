import { useState, type FormEvent } from "react";

import { useAppState } from "../state/AppStateContext";
import { formatAuthError } from "../state/sessionPreferences";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";
import { LoadingState } from "./ui/LoadingState";
import { TextInput } from "./ui/TextInput";

type AuthMode = "login" | "register";

export function AuthGate() {
  const { authStatus, connection, login, register } = useAppState();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (authStatus === "checking") {
    return (
      <div className="auth-gate">
        <div className="auth-gate__panel">
          <div className="auth-gate__brand">
            <span className="auth-gate__name">Memovi</span>
            <span className="auth-gate__tag">Knowledge OS</span>
          </div>
          <LoadingState label="Restoring your session…" />
        </div>
      </div>
    );
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail || password.length < 8) {
      setError("Enter a valid email and a password of at least 8 characters.");
      return;
    }
    if (mode === "register" && password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setBusy(true);
    try {
      if (mode === "login") {
        await login({ email: trimmedEmail, password });
      } else {
        await register({ email: trimmedEmail, password });
      }
    } catch (err) {
      setError(formatAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  const backendHint =
    connection.status === "disconnected"
      ? "Backend is unreachable. Start it with `task backend`, then sign in."
      : connection.status === "degraded"
        ? "Backend is reachable but some dependencies are not ready."
        : null;

  return (
    <div className="auth-gate">
      <div className="auth-gate__panel">
        <div className="auth-gate__brand">
          <span className="auth-gate__name">Memovi</span>
          <span className="auth-gate__tag">Knowledge OS</span>
        </div>
        <h1 className="auth-gate__title">
          {mode === "login" ? "Sign in" : "Create your account"}
        </h1>
        <p className="auth-gate__lede">
          {mode === "login"
            ? "Continue to your knowledge workspace."
            : "Register on this Memovi instance to own your knowledge."}
        </p>

        {backendHint ? <Alert tone="warn">{backendHint}</Alert> : null}
        {error ? <Alert tone="bad">{error}</Alert> : null}

        <form className="auth-gate__form" onSubmit={(event) => void handleSubmit(event)}>
          <TextInput
            label="Email"
            name="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={busy}
            required
          />
          <TextInput
            label="Password"
            name="password"
            type="password"
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={busy}
            hint={mode === "register" ? "At least 8 characters." : undefined}
            required
            minLength={8}
          />
          {mode === "register" ? (
            <TextInput
              label="Confirm password"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              disabled={busy}
              required
              minLength={8}
            />
          ) : null}
          <Button type="submit" busy={busy} className="auth-gate__submit">
            {busy
              ? mode === "login"
                ? "Signing in…"
                : "Creating account…"
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </Button>
        </form>

        <p className="auth-gate__switch">
          {mode === "login" ? (
            <>
              New here?{" "}
              <button
                type="button"
                className="auth-gate__link"
                onClick={() => {
                  setMode("register");
                  setError(null);
                }}
                disabled={busy}
              >
                Create an account
              </button>
            </>
          ) : (
            <>
              Already registered?{" "}
              <button
                type="button"
                className="auth-gate__link"
                onClick={() => {
                  setMode("login");
                  setError(null);
                  setConfirmPassword("");
                }}
                disabled={busy}
              >
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
