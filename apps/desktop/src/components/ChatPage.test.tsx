import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { AvailableModel } from "../api/types";
import { ChatPage } from "./ChatPage";

const listConversations = vi.fn();
const listMessages = vi.fn();
const listPendingExecutions = vi.fn();
const listConversationExecutions = vi.fn();
const openSettings = vi.fn();

vi.mock("../api/conversations", () => ({
  createConversation: vi.fn(),
  deleteConversation: vi.fn(),
  listConversations: (...args: unknown[]) => listConversations(...args),
  listMessages: (...args: unknown[]) => listMessages(...args),
  renameConversation: vi.fn(),
  streamMessage: vi.fn(),
}));

vi.mock("../api/capabilities", () => ({
  approveCapabilityExecution: vi.fn(),
  cancelCapabilityExecution: vi.fn(),
  listConversationExecutions: (...args: unknown[]) =>
    listConversationExecutions(...args),
  listPendingExecutions: (...args: unknown[]) => listPendingExecutions(...args),
  submitCapabilityExecution: vi.fn(),
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
  activeWorkspace: { id: "ws-1", name: "Test" },
  activeModel: {
    provider: "fake",
    model: "fake-reasoning-v1",
    label: "fake/fake-reasoning-v1",
  } as { provider: string; model: string; label: string } | null,
  availableModels: fakeModels as AvailableModel[],
  connection: { status: "connected" as string },
  chatSeed: null,
  clearChatSeed: vi.fn(),
  openSettings,
};

vi.mock("../state/AppStateContext", () => ({
  useAppState: () => appState,
}));

describe("ChatPage provider setup", () => {
  beforeEach(() => {
    appState.connection.status = "connected";
    appState.availableModels = fakeModels;
    appState.activeModel = {
      provider: "fake",
      model: "fake-reasoning-v1",
      label: "fake/fake-reasoning-v1",
    };
    openSettings.mockReset();
    listConversations.mockResolvedValue({
      conversations: [
        {
          conversation_id: "conv-1",
          title: "Demo chat",
          created_at: "2026-01-01T00:00:00.000Z",
          updated_at: "2026-01-01T00:00:00.000Z",
          message_count: 0,
        },
      ],
    });
    listMessages.mockResolvedValue({ messages: [] });
    listPendingExecutions.mockResolvedValue({ items: [] });
    listConversationExecutions.mockResolvedValue({ items: [] });
  });

  it("adds a configure CTA for fake-only without blocking chat", async () => {
    const user = userEvent.setup();
    render(<ChatPage />);

    expect(
      await screen.findByText(/AI provider not configured/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Configure an AI provider/i }),
    ).toBeInTheDocument();
    expect((await screen.findAllByText(/Demo chat/i)).length).toBeGreaterThan(
      0,
    );

    await user.click(
      screen.getByRole("button", { name: /Configure an AI provider/i }),
    );
    expect(openSettings).toHaveBeenCalledWith("diagnostics");
  });

  it("does not show provider-unconfigured copy when a real model is available", async () => {
    appState.availableModels = realModels;
    appState.activeModel = {
      provider: "openai",
      model: "gpt-4o-mini",
      label: "openai/gpt-4o-mini",
    };
    render(<ChatPage />);

    expect((await screen.findAllByText(/Demo chat/i)).length).toBeGreaterThan(
      0,
    );
    expect(
      screen.queryByText(/AI provider not configured/i),
    ).not.toBeInTheDocument();
  });

  it("does not say the provider is unconfigured when the backend is down", () => {
    appState.connection.status = "disconnected";
    render(<ChatPage />);

    expect(
      screen.queryByText(/AI provider not configured/i),
    ).not.toBeInTheDocument();
  });
});
