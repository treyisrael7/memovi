import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiRequestError } from "../api/client";
import type { AvailableModel, CapabilityMetadata } from "../api/types";
import type { SettingsSectionId } from "../navigation/pages";
import { SettingsPage } from "./SettingsPage";

const listCapabilities = vi.fn();
const setCapabilityPermissionMode = vi.fn();
const showToast = vi.fn();

vi.mock("../api/capabilities", () => ({
  listCapabilities: (...args: unknown[]) => listCapabilities(...args),
  setCapabilityPermissionMode: (...args: unknown[]) =>
    setCapabilityPermissionMode(...args),
}));

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

const filesystemCapability: CapabilityMetadata = {
  id: "filesystem",
  description: "Read and write local files",
  permissions: ["filesystem.read"],
  parameters: [],
  permission_mode: "ask_every_time",
};

const appState = {
  settingsSection: "general" as SettingsSectionId,
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
  activeWorkspace: {
    id: "ws-1",
    name: "Test",
    role: "owner" as string | null,
  },
};

vi.mock("../state/AppStateContext", () => ({
  useAppState: () => appState,
}));

vi.mock("./ui/ToastContext", () => ({
  useToast: () => ({ showToast }),
}));

describe("SettingsPage provider setup", () => {
  beforeEach(() => {
    appState.settingsSection = "general";
    appState.availableModels = fakeModels;
    appState.connection.status = "connected";
    appState.activeWorkspace = {
      id: "ws-1",
      name: "Test",
      role: "owner",
    };
    appState.setSettingsSection.mockReset();
    showToast.mockReset();
    listCapabilities.mockReset();
    setCapabilityPermissionMode.mockReset();
    listCapabilities.mockResolvedValue({
      items: [filesystemCapability],
      count: 1,
    });
    setCapabilityPermissionMode.mockResolvedValue({
      capability_id: "filesystem",
      permission_mode: "always_allow",
    });
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

    expect(screen.getByText("Client origin")).toBeInTheDocument();
    expect(screen.getByText("http://127.0.0.1:1420")).toBeInTheDocument();
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

describe("SettingsPage capability policies", () => {
  beforeEach(() => {
    appState.settingsSection = "capabilities";
    appState.connection.status = "connected";
    appState.activeWorkspace = {
      id: "ws-1",
      name: "Test",
      role: "owner",
    };
    showToast.mockReset();
    listCapabilities.mockReset();
    setCapabilityPermissionMode.mockReset();
    listCapabilities.mockResolvedValue({
      items: [filesystemCapability],
      count: 1,
    });
    setCapabilityPermissionMode.mockResolvedValue({
      capability_id: "filesystem",
      permission_mode: "always_allow",
    });
  });

  it("loads permission modes and saves a change through the API client", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    expect(await screen.findByText("filesystem")).toBeInTheDocument();
    expect(listCapabilities).toHaveBeenCalledWith("ws-1");
    const modeSelect = screen.getByRole("combobox");
    expect(modeSelect).toHaveValue("ask_every_time");
    expect(modeSelect).not.toBeDisabled();

    await user.selectOptions(modeSelect, "always_allow");

    await waitFor(() => {
      expect(setCapabilityPermissionMode).toHaveBeenCalledWith(
        "ws-1",
        "filesystem",
        "always_allow",
      );
    });
    expect(modeSelect).toHaveValue("always_allow");
  });

  it("keeps the previous mode when the permission update fails", async () => {
    const user = userEvent.setup();
    setCapabilityPermissionMode.mockRejectedValue(
      new ApiRequestError("Only workspace owners can change capability policies.", {
        status: 403,
        kind: "http",
      }),
    );
    render(<SettingsPage />);

    const modeSelect = await screen.findByRole("combobox");
    await user.selectOptions(modeSelect, "deny");

    await waitFor(() => {
      expect(setCapabilityPermissionMode).toHaveBeenCalledWith(
        "ws-1",
        "filesystem",
        "deny",
      );
    });
    expect(modeSelect).toHaveValue("ask_every_time");
    expect(showToast).toHaveBeenCalledWith(
      "Only workspace owners can change capability policies.",
      "bad",
    );
  });

  it("makes permission controls read-only for workspace members", async () => {
    const user = userEvent.setup();
    appState.activeWorkspace = {
      id: "ws-1",
      name: "Test",
      role: "member",
    };
    render(<SettingsPage />);

    expect(
      await screen.findByText(/read-only for members/i),
    ).toBeInTheDocument();
    const modeSelect = screen.getByRole("combobox");
    expect(modeSelect).toHaveValue("ask_every_time");
    expect(modeSelect).toBeDisabled();

    await user.selectOptions(modeSelect, "deny");
    expect(setCapabilityPermissionMode).not.toHaveBeenCalled();
  });
});
