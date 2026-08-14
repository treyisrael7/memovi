import {
  connectedProviderStatusLabel,
  OPENAI_BACKEND_ENV_INSTRUCTIONS,
  PROVIDER_SETUP_RESTART_NOTE,
  PROVIDER_SETUP_STEPS,
  type ProviderSetupKind,
} from "./gettingStarted";
import type { AvailableModel } from "../api/types";
import { Button } from "./ui/Button";

export function ProviderSetupSteps() {
  return (
    <ol className="provider-setup-steps">
      {PROVIDER_SETUP_STEPS.map((step) => (
        <li key={step}>{step}</li>
      ))}
    </ol>
  );
}

export function ProviderBackendEnvInstructions() {
  return (
    <div className="provider-setup-env">
      <p className="muted">Required backend configuration:</p>
      <pre>
        <code>{OPENAI_BACKEND_ENV_INSTRUCTIONS}</code>
      </pre>
      <p>{PROVIDER_SETUP_RESTART_NOTE}</p>
    </div>
  );
}

export function ProviderSetupCard({
  kind,
  title,
  description,
  onOpenDiagnostics,
  onViewInstructions,
}: {
  kind: Extract<ProviderSetupKind, "none" | "fake_only">;
  title: string;
  description: string;
  onOpenDiagnostics: () => void;
  onViewInstructions?: () => void;
}) {
  return (
    <section
      className="provider-setup-card"
      aria-labelledby="provider-setup-heading"
      data-kind={kind}
    >
      <h2 id="provider-setup-heading">{title}</h2>
      <p>{description}</p>
      {kind === "fake_only" ? (
        <>
          <p className="muted">
            Memovi is working. Chat can still use the demo model. Configure a
            real provider in the backend environment — not in this desktop
            window.
          </p>
          <ProviderSetupSteps />
        </>
      ) : null}
      <div className="provider-setup-actions">
        <Button onClick={onOpenDiagnostics}>Open Diagnostics</Button>
        {onViewInstructions ? (
          <Button variant="secondary" onClick={onViewInstructions}>
            View configuration instructions
          </Button>
        ) : null}
      </div>
    </section>
  );
}

export function ProviderConnectedStatus({
  models,
}: {
  models: AvailableModel[];
}) {
  const label = connectedProviderStatusLabel(models);
  if (!label) {
    return null;
  }
  return (
    <p className="provider-connected-status" role="status">
      {label}
    </p>
  );
}
