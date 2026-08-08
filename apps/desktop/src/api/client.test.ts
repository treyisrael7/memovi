import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import { API_BASE_URL } from "./config";
import { ApiRequestError, apiFetch } from "./client";

describe("apiFetch", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ ok: true }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("calls the configured API base with credentials", async () => {
    await apiFetch<{ ok: boolean }>("/health");
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/health`,
      expect.objectContaining({
        credentials: "include",
      }),
    );
  });

  it("maps network failures to ApiRequestError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    await expect(apiFetch("/health")).rejects.toBeInstanceOf(ApiRequestError);
  });

  it("surfaces HTTP error details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: "Nope" }), {
            status: 422,
            headers: { "Content-Type": "application/json" },
          }),
      ),
    );
    await expect(
      apiFetch("/auth/login", { method: "POST" }),
    ).rejects.toMatchObject({
      status: 422,
      message: "Nope",
    });
  });
});
