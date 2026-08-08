import { describe, expect, it } from "vitest";

import { getPage, PAGES } from "../navigation/pages";
import {
  formatAuthError,
  readStoredTheme,
  writeStoredTheme,
  writeStoredPage,
  readStoredPage,
  writeStoredWorkspaceId,
  readStoredWorkspaceId,
} from "../state/sessionPreferences";
import { ApiRequestError } from "../api/client";

describe("navigation pages", () => {
  it("registers critical product surfaces", () => {
    const ids = PAGES.map((page) => page.id);
    expect(ids).toEqual(
      expect.arrayContaining([
        "chat",
        "documents",
        "search",
        "workflows",
        "settings",
      ]),
    );
  });

  it("resolves known pages and rejects unknown ids", () => {
    expect(getPage("search").label).toBe("Search");
    expect(() => getPage("missing" as never)).toThrow(/Unknown page/);
  });
});

describe("sessionPreferences", () => {
  it("persists theme and restores it", () => {
    expect(readStoredTheme()).toBe("light");
    writeStoredTheme("dark");
    expect(readStoredTheme()).toBe("dark");
  });

  it("persists last page and workspace per user", () => {
    writeStoredPage("user-1", "documents");
    writeStoredWorkspaceId("user-1", "ws-1");
    expect(readStoredPage("user-1")).toBe("documents");
    expect(readStoredWorkspaceId("user-1")).toBe("ws-1");
    expect(readStoredPage("user-2")).toBeNull();
  });

  it("formats auth errors for the login gate", () => {
    expect(
      formatAuthError(new ApiRequestError("nope", { kind: "network" })),
    ).toMatch(/Cannot reach the Memovi backend/);
    expect(
      formatAuthError(
        new ApiRequestError("bad", { kind: "http", status: 401 }),
      ),
    ).toMatch(/incorrect/i);
  });
});
