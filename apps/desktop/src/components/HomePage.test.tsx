import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { AvailableModel } from "../api/types";
import { HomePage } from "./HomePage";

const listFilesystemFolders = vi.fn();
const listDocuments = vi.fn();
const listConversations = vi.fn();
const openSettings = vi.fn();
const setActivePage = vi.fn();

vi.mock("../api/connectors", () => ({
  listFilesystemFolders: (...args: unknown[]) => listFilesystemFolders(...args),
}));

vi.mock("../api/documents", () => ({
  listDocuments: (...args: unknown[]) => listDocuments(...args),
}));

vi.mock("../api/conversations", () => ({
  listConversations: (...args: unknown[]) => listConversations(...args),
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

const appState = {
  connection: {
    status: "connected" as string,
    error: null as string | null,
  },
  authStatus: "authenticated",
  activeWorkspace: { id: "ws-1", name: "Test" },
  availableModels: fakeModels as AvailableModel[],
  activeModelLabel: "fake/fake-reasoning-v1",
  setActivePage,
  openSettings,
};

vi.mock("../state/AppStateContext", () => ({
  useAppState: () => appState,
}));

describe("HomePage provider setup", () => {
  beforeEach(() => {
    appState.connection.status = "connected";
    appState.connection.error = null;
    appState.availableModels = fakeModels;
    openSettings.mockReset();
    setActivePage.mockReset();
    listFilesystemFolders.mockResolvedValue({ items: [], count: 0 });
    listDocuments.mockResolvedValue({ items: [] });
    listConversations.mockResolvedValue({ conversations: [] });
  });

  it("shows fake-only setup guidance and opens Diagnostics", async () => {
    const user = userEvent.setup();
    render(<HomePage />);

    expect(
      await screen.findByRole("heading", { name: /Connect an AI provider/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/only the built-in demo model is available/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/INTELLIGENCE_PROVIDER=openai/i),
    ).toBeInTheDocument();

    const diagnosticsButtons = screen.getAllByRole("button", {
      name: /^Open Diagnostics$/i,
    });
    expect(diagnosticsButtons.length).toBeGreaterThan(0);
    await user.click(diagnosticsButtons[0]);
    expect(openSettings).toHaveBeenCalledWith("diagnostics");
  });

  it("does not say the provider is unconfigured when the backend is down", () => {
    appState.connection.status = "disconnected";
    appState.connection.error = "Cannot reach the Memovi backend.";
    render(<HomePage />);

    expect(
      screen.queryByRole("heading", { name: /Connect an AI provider/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/Cannot reach the Memovi backend/i),
    ).toBeInTheDocument();
  });

  it("hides the fake-only card when a real provider is registered", () => {
    appState.availableModels = realModels;
    render(<HomePage />);

    expect(
      screen.queryByRole("heading", { name: /Connect an AI provider/i }),
    ).not.toBeInTheDocument();
  });
});
