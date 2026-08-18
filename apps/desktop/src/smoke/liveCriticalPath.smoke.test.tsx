/**
 * Live critical-path smoke: desktop React shell against a real FastAPI process.
 *
 * Requires MEMOVI_LIVE_API=1 plus Postgres, MinIO, and the API with fake
 * intelligence/embedding providers. Does not launch the native Tauri window.
 *
 * Expected runtime: under 90 seconds when infrastructure is already up.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "../App";
import { API_BASE_URL, DEFAULT_WORKSPACE_ID } from "../api/config";
import { listKnowledge } from "../api/memory";
import { searchKnowledge } from "../api/search";
import { installLiveApiCookieBridge } from "../test/liveApiCookies";

const LIVE_ENABLED = isLiveApiEnabled();
const LIVE_TIMEOUT_MS = 90_000;
const STEP_TIMEOUT_MS = 35_000;
const SEARCH_RETRY_MS = 250;

function randomLetters(length: number): string {
  const alphabet = "abcdefghijklmnopqrstuvwxyz";
  let output = "";
  for (let index = 0; index < length; index += 1) {
    output += alphabet[Math.floor(Math.random() * alphabet.length)] ?? "x";
  }
  return output;
}

// Letter-only token so Postgres english FTS does not split on digits.
const UNIQUE_PHRASE = `quorzivelt${randomLetters(8)}`;
const DOCUMENT_NAME = "live-smoke.txt";
const DOCUMENT_BODY = [
  "Memovi live smoke document.",
  "",
  `The lattice token ${UNIQUE_PHRASE} is unique to this run.`,
].join("\n");

function isLiveApiEnabled(): boolean {
  const env = (
    globalThis as { process?: { env?: Record<string, string | undefined> } }
  ).process?.env;
  return env?.MEMOVI_LIVE_API === "1";
}

function failLive(step: string, detail?: string): never {
  throw new Error(
    detail ? `Live smoke: ${step}. ${detail}` : `Live smoke: ${step}.`,
  );
}

async function waitForVisibleText(
  pattern: RegExp,
  timeout: number = STEP_TIMEOUT_MS,
): Promise<void> {
  await waitFor(
    () => {
      expect(screen.getAllByText(pattern).length).toBeGreaterThan(0);
    },
    { timeout },
  );
}

async function assertApiReachable(): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/health`, {
      headers: { Accept: "application/json" },
    });
  } catch (error) {
    failLive(
      "API unavailable",
      error instanceof Error ? error.message : String(error),
    );
  }
  if (!response.ok) {
    failLive("API unavailable", `/health returned HTTP ${response.status}`);
  }
}

async function waitForSearchHit(phrase: string): Promise<string> {
  const deadline = Date.now() + STEP_TIMEOUT_MS;
  let lastDetail = "no search attempt completed";
  let knowledgeCount = 0;
  while (Date.now() < deadline) {
    try {
      const knowledge = await listKnowledge(DEFAULT_WORKSPACE_ID);
      knowledgeCount = knowledge.count ?? knowledge.items.length;
    } catch (error) {
      lastDetail = error instanceof Error ? error.message : String(error);
    }
    try {
      const payload = await searchKnowledge(DEFAULT_WORKSPACE_ID, {
        q: phrase,
        mode: "keyword",
      });
      const hit = payload.results.find((result) => result.text.includes(phrase));
      if (hit) {
        return hit.document_id;
      }
      lastDetail = `keyword search returned ${payload.count} result(s) without ${phrase}`;
    } catch (error) {
      lastDetail = error instanceof Error ? error.message : String(error);
    }
    await new Promise((resolve) => {
      window.setTimeout(resolve, SEARCH_RETRY_MS);
    });
  }
  failLive(
    "search never returned unique phrase",
    `${lastDetail}. knowledge items=${knowledgeCount}`,
  );
}

describe.skipIf(!LIVE_ENABLED)("desktop live critical path", () => {
  let uninstallCookies: (() => void) | undefined;

  beforeEach(() => {
    expect(window.location.origin).toBe("http://127.0.0.1:1420");
    uninstallCookies = installLiveApiCookieBridge();
  });

  afterEach(() => {
    uninstallCookies?.();
    uninstallCookies = undefined;
  });

  it(
    "registers, uploads, waits for processing and search, chats, and opens a citation",
    async () => {
      await assertApiReachable();

      const user = userEvent.setup();
      const email = `live-smoke-${Date.now()}-${Math.random()
        .toString(36)
        .slice(2, 8)}@memovi.test`;
      const password = "password123";
      const { unmount } = render(<App />);

      expect(
        await screen.findByRole("heading", { name: /Sign in/i }),
      ).toBeInTheDocument();

      await user.click(
        screen.getByRole("button", { name: /Create an account/i }),
      );
      expect(
        await screen.findByRole("heading", { name: /Create your account/i }),
      ).toBeInTheDocument();

      await user.type(screen.getByLabelText(/^Email$/i), email);
      // Register Password includes the "At least 8 characters" hint inside the
      // <label>, so the accessible name is not exactly "Password".
      await user.type(screen.getByLabelText(/^Password/i), password);
      await user.type(screen.getByLabelText(/^Confirm password$/i), password);
      await user.click(
        screen.getByRole("button", { name: /^Create account$/i }),
      );

      try {
        await waitFor(() => {
          expect(
            screen.getByRole("navigation", { name: /Primary/i }),
          ).toBeInTheDocument();
        });
      } catch {
        const authError = screen.queryByRole("alert");
        failLive(
          "registration failed",
          authError?.textContent?.trim() ||
            "shell did not reach the authenticated workspace",
        );
      }

      await user.click(screen.getByRole("button", { name: /^Documents$/i }));
      expect(
        await screen.findByRole("heading", { name: /^Documents$/i }),
      ).toBeInTheDocument();

      try {
        await waitFor(() => {
          expect(
            screen.getByRole("button", { name: /^Choose files$/i }),
          ).toBeEnabled();
        });
      } catch {
        failLive(
          "upload failed",
          "Documents file picker stayed disabled — backend connection or workspace was not ready",
        );
      }

      const fileInput = [
        ...document.querySelectorAll('input[type="file"]'),
      ].find((input) => !(input as HTMLInputElement).disabled) as
        HTMLInputElement | undefined;
      if (!fileInput) {
        failLive("upload failed", "no enabled file input was rendered");
      }
      const file = new File([DOCUMENT_BODY], DOCUMENT_NAME, {
        type: "text/plain",
      });
      await user.upload(fileInput, file);

      try {
        expect(
          await screen.findByText(
            /Uploaded — queued for processing/i,
            undefined,
            {
              timeout: 15_000,
            },
          ),
        ).toBeInTheDocument();
      } catch {
        const failed =
          screen.queryByText(/failed to upload/i)?.textContent?.trim() ||
          screen.queryByText(/^Failed:/i)?.textContent?.trim();
        failLive(
          "upload failed",
          failed ||
            `upload confirmation never appeared. UI: ${document.body.textContent?.slice(0, 400) ?? ""}`,
        );
      }

      try {
        await waitFor(
          () => {
            expect(screen.getAllByText(/^Ready$/i).length).toBeGreaterThan(0);
          },
          { timeout: STEP_TIMEOUT_MS },
        );
      } catch {
        const failed = screen.queryAllByText(/^Failed$/i);
        failLive(
          "document never became Ready",
          failed.length > 0
            ? "processing status is Failed"
            : "processing status did not reach completed/Ready",
        );
      }

      const uploadedDocumentId = await waitForSearchHit(UNIQUE_PHRASE);

      await user.click(screen.getByRole("button", { name: /^Search$/i }));
      const searchBox = await screen.findByPlaceholderText(
        /Search documents and knowledge/i,
      );
      await user.clear(searchBox);
      await user.type(searchBox, `${UNIQUE_PHRASE}{enter}`);
      try {
        expect(
          await screen.findByText(new RegExp(UNIQUE_PHRASE), undefined, {
            timeout: 15_000,
          }),
        ).toBeInTheDocument();
      } catch {
        failLive(
          "search never returned unique phrase",
          "Search page did not render the indexed snippet",
        );
      }

      await user.click(
        screen.getByRole("button", { name: /^Conversations$/i }),
      );
      expect(
        await screen.findByRole("complementary", { name: /Conversations/i }),
      ).toBeInTheDocument();

      // Shared default workspace can already contain earlier live-smoke threads.
      await user.click(
        screen.getByRole("button", { name: /^New Conversation$/i }),
      );
      try {
        expect(
          await screen.findByText(/Ask a question below/i, undefined, {
            timeout: 15_000,
          }),
        ).toBeInTheDocument();
      } catch {
        failLive(
          "chat did not produce SSE response",
          "could not start a new conversation",
        );
      }

      const composer = await screen.findByPlaceholderText(/Ask Memovi/i);
      const question = `What is ${UNIQUE_PHRASE}?`;
      await user.type(composer, question);
      const sendButton = screen.getByRole("button", { name: /^Send$/i });
      try {
        await waitFor(() => {
          expect(sendButton).toBeEnabled();
        });
      } catch {
        failLive(
          "chat did not produce SSE response",
          "Send stayed disabled — backend connection was not ready for conversations",
        );
      }
      await user.click(sendButton);

      try {
        await waitFor(
          () => {
            const matched = [
              ...document.querySelectorAll(
                '[data-role="assistant"] .message-body',
              ),
            ].some((node) => {
              const text = node.textContent ?? "";
              return /Answer for/i.test(text) && text.includes(UNIQUE_PHRASE);
            });
            expect(matched).toBe(true);
          },
          { timeout: STEP_TIMEOUT_MS },
        );
      } catch {
        const alerts = screen
          .queryAllByRole("alert")
          .map((node) => node.textContent?.trim())
          .filter((text): text is string => Boolean(text));
        const failedMessages = [
          ...document.querySelectorAll('[data-failed="true"] .message-body'),
        ]
          .map((node) => node.textContent?.trim())
          .filter((text): text is string => Boolean(text));
        const assistantPreview = [
          ...document.querySelectorAll(".message-body"),
        ]
          .map((node) => node.textContent?.trim())
          .filter((text): text is string => Boolean(text))
          .slice(-3)
          .join(" | ");
        failLive(
          "chat did not produce SSE response",
          alerts[0] ||
            failedMessages[0] ||
            assistantPreview ||
            "fake reasoning answer never appeared",
        );
      }

      let chips: HTMLElement[];
      try {
        await waitFor(
          () => {
            const assistants = [
              ...document.querySelectorAll('[data-role="assistant"]'),
            ];
            const latest = assistants.at(-1);
            expect(latest).toBeTruthy();
            const found = within(latest as HTMLElement).getAllByRole(
              "button",
              { name: /Open source:/i },
            );
            expect(found.length).toBeGreaterThan(0);
          },
          { timeout: STEP_TIMEOUT_MS },
        );
        const latest = [
          ...document.querySelectorAll('[data-role="assistant"]'),
        ].at(-1) as HTMLElement;
        chips = within(latest).getAllByRole("button", {
          name: /Open source:/i,
        });
      } catch {
        failLive(
          "citation missing",
          "no citation chip was rendered for the uploaded document",
        );
      }

      const citation = chips.find((chip) => {
        const name = chip.getAttribute("aria-label") ?? chip.textContent ?? "";
        return name.includes(uploadedDocumentId);
      });
      if (!citation) {
        const labels = chips
          .map((chip) => chip.getAttribute("aria-label") ?? chip.textContent ?? "")
          .join(", ");
        failLive(
          "citation missing",
          `no chip for uploaded document ${uploadedDocumentId}; chips were ${labels}`,
        );
      }
      await user.click(citation);

      try {
        expect(
          await screen.findByRole("heading", { name: /^Knowledge$/i }),
        ).toBeInTheDocument();
        await waitForVisibleText(new RegExp(UNIQUE_PHRASE));
      } catch {
        const headings = screen
          .queryAllByRole("heading")
          .map((node) => node.textContent?.trim())
          .filter((text): text is string => Boolean(text))
          .slice(0, 8)
          .join(" | ");
        failLive(
          "citation navigation failed",
          headings
            ? `visible headings: ${headings}`
            : "Knowledge/source view did not show the uploaded knowledge",
        );
      }

      unmount();
    },
    LIVE_TIMEOUT_MS,
  );
});
