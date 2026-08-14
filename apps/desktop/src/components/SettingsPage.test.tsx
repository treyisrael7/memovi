import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { AvailableModel } from "../api/types";
import { SettingsPage } from "./SettingsPage";

const fakeModels: AvailableModel[] = [
  {
    provider: "fake",
    model: "fake-reasoning-v1",
    label: "fake/fake-reasoning-v1",
  },
];

const realModels: AvailableModel[] = [
  { provider: "openai", model: "gpt-4o-mini", label: "openai/gpt-4o-mini" },
];

const appState = {
  settingsSection: "general" as "general" | "diagnostics",
  setSettingsSection: vi.fn(),
  availableModels: fakeModels as AvailableModel[],
  activeModel: {
    provider: "fake",
    model: "fake-reasoning-v1",
    label: "fake/fake-reasoning-v1",
  },
  setActiveModel: vi.fn(),
  theme: "light" as const,
  setTheme: vi.fn(),
  connection: {
    status: "connected" as string,
    environment: "local",
    lastCheckedAt: new Date(0).toISOString(),
    error: null as string | null,
    components: [] as Array<{ name: string; status: string; detail?: string }>,
  },
  isRefreshing: false,
  refreshConnection: vi.fn(),
  user: { id: "user-1", email: "dev@memovi.test" },
  logout: vi.fn(),
};

vi.mock("../state/AppStateContext", () => ({
  useAppState: () => appState,
}));

vi.mock("./ui/ToastContext", () => ({
  useToast: () => ({ showToast: vi.fn() }),
}));

describe("SettingsPage provider setup", () => {
  beforeEach(() => {
    appState.settingsSection = "general";
    appState.availableModels = fakeModels;
    appState.connection.status = "connected";
    appState.setSettingsSection.mockReset();
  });

  it("shows setup instructions next to the model selector when only fake is available", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    expect(screen.getByLabelText(/^Active model$/i)).toBeInTheDocument();
    expect(screen.getByText(/built-in demo model/i)).toBeInTheDocument();
    expect(screen.getByText(/Restart the Memovi API/i)).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /^Open Diagnostics$/i }),
    );
    expect(appState.setSettingsSection).toHaveBeenCalledWith("diagnostics");
  });

  it("shows OpenAI connected when a non-fake model is registered", () => {
    appState.availableModels = realModels;
    appState.activeModel = {
      provider: "openai",
      model: "gpt-4o-mini",
      label: "openai/gpt-4o-mini",
    };
    render(<SettingsPage />);

    expect(screen.getByText("OpenAI connected")).toBeInTheDocument();
    expect(screen.queryByText(/built-in demo model/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/^Active model$/i)).toBeInTheDocument();
  });

  it("shows backend env placeholders in Diagnostics without secret values", async () => {
    const user = userEvent.setup();
    appState.settingsSection = "diagnostics";
    render(<SettingsPage />);

    expect(
      screen.getByText(/Required backend configuration/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/OPENAI_API_KEY=<your key>/)).toBeInTheDocument();
    expect(
      screen.getByText(/INTELLIGENCE_PROVIDER=openai/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Restart the Memovi API after changing these values/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/sk-/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^General$/i }));
    expect(appState.setSettingsSection).toHaveBeenCalledWith("general");
  });
});
