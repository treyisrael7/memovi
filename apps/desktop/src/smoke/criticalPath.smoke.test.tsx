/**
 * Critical-path desktop smoke tests.
 *
 * These exercise the flagship React shell against an in-memory API stub.
 * They intentionally avoid pixel assertions and full Tauri packaging.
 *
 * Expected runtime: under 30 seconds locally / in CI.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../api/config", async () => {
  const actual =
    await vi.importActual<typeof import("../api/config")>("../api/config");
  return {
    ...actual,
    CONNECTION_POLL_INTERVAL_MS: 60_000,
  };
});

import App from "../App";
import { createMockBackend } from "../test/mockBackend";

describe("desktop critical path smoke", () => {
  const backend = createMockBackend();

  beforeEach(() => {
    backend.install();
  });

  afterEach(() => {
    backend.uninstall();
  });

  it("covers startup → auth → workspace → documents → search → chat → workflows → settings → shutdown", async () => {
    const user = userEvent.setup();
    const { unmount } = render(<App />);

    // Startup → auth gate (session restore is often too fast to assert)
    expect(
      await screen.findByRole("heading", { name: /Sign in/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Memovi/i)).toBeInTheDocument();

    // Authentication
    await user.type(screen.getByLabelText(/^Email$/i), "smoke@memovi.test");
    await user.type(screen.getByLabelText(/^Password$/i), "password123");
    await user.click(screen.getByRole("button", { name: /^Sign in$/i }));

    // Workspace + shell loaded
    await waitFor(() => {
      expect(
        screen.getByRole("navigation", { name: /Primary/i }),
      ).toBeInTheDocument();
    });
    expect(
      await screen.findByText(/Workspace:\s*Default Workspace/i),
    ).toBeInTheDocument();

    // Documents + processing status
    await user.click(screen.getByRole("button", { name: /^Documents$/i }));
    expect(
      await screen.findByRole("heading", { name: /^Documents$/i }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "notes.txt" }),
    ).toBeInTheDocument();
    expect(
      (await screen.findAllByText(/Completed/i)).length,
    ).toBeGreaterThan(0);
    expect((await screen.findAllByText(/Indexed/i)).length).toBeGreaterThan(0);

    // Document upload
    const fileInput = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    expect(fileInput).toBeTruthy();
    const file = new File(["hello smoke"], "uploaded.txt", {
      type: "text/plain",
    });
    await user.upload(fileInput, file);
    expect(
      await screen.findByText(/Uploaded — queued for processing/i),
    ).toBeInTheDocument();
    expect((await screen.findAllByText("uploaded.txt")).length).toBeGreaterThan(
      0,
    );
    expect(await screen.findByText(/^Queued$/i)).toBeInTheDocument();

    // Search
    await user.click(screen.getByRole("button", { name: /^Search$/i }));
    const searchBox = await screen.findByPlaceholderText(
      /Search documents and knowledge/i,
    );
    await user.type(searchBox, "smoke{enter}");
    expect(
      await screen.findByText(/Critical path search result/i),
    ).toBeInTheDocument();

    // Conversation
    await user.click(screen.getByRole("button", { name: /^Conversations$/i }));
    expect(
      await screen.findByRole("complementary", { name: /Conversations/i }),
    ).toBeInTheDocument();
    expect(
      (await screen.findAllByText(/Smoke conversation/i)).length,
    ).toBeGreaterThan(0);
    expect(
      await screen.findByText(/Hello from smoke stub/i),
    ).toBeInTheDocument();

    // Workflow execution
    await user.click(screen.getByRole("button", { name: /^Workflows$/i }));
    expect(
      (await screen.findAllByText(/List Directory/i)).length,
    ).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: /Configure & Run/i }));
    await user.type(
      await screen.findByLabelText(/source_folder|Folder/i),
      "/tmp",
    );
    await user.click(screen.getByRole("button", { name: /^Run Workflow$/i }));
    await waitFor(() => {
      expect(backend.calls().some((call) => call.includes("/execute"))).toBe(
        true,
      );
    });

    // Settings persistence (theme + model)
    await user.click(screen.getByRole("button", { name: /^Settings$/i }));
    expect(
      await screen.findByRole("heading", { name: /Model/i }),
    ).toBeInTheDocument();
    const theme = screen.getByLabelText(/^Theme$/i);
    await user.selectOptions(theme, "dark");
    expect(window.localStorage.getItem("memovi.desktop.theme")).toBe("dark");
    await waitFor(() => {
      expect(
        window.localStorage.getItem("memovi.desktop.activeModel.user-smoke-1"),
      ).toBe("fake::fake-model");
    });

    // Shutdown: sign out returns to auth gate, then unmount (app close)
    await user.click(screen.getByRole("button", { name: /^Account$/i }));
    await user.click(screen.getByRole("button", { name: /^Sign out$/i }));
    // Confirm dialog
    const dialog = await screen.findByRole("alertdialog");
    await user.click(
      within(dialog).getByRole("button", { name: /^Sign out$/i }),
    );
    expect(
      await screen.findByRole("heading", { name: /Sign in/i }),
    ).toBeInTheDocument();
    expect(backend.isAuthenticated()).toBe(false);

    unmount();
  });
});
