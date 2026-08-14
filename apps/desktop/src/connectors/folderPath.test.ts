import { describe, expect, it } from "vitest";

import { folderDisplayName } from "./folderPath";

describe("folderDisplayName", () => {
  it("returns the last Windows path segment", () => {
    expect(folderDisplayName("C:\\Users\\you\\Documents\\notes")).toBe("notes");
  });

  it("returns the last POSIX path segment", () => {
    expect(folderDisplayName("/home/you/vaults/research")).toBe("research");
  });

  it("strips a trailing separator", () => {
    expect(folderDisplayName("C:\\Users\\you\\notes\\")).toBe("notes");
    expect(folderDisplayName("/home/you/notes/")).toBe("notes");
  });

  it("preserves a drive or root when there is no folder name", () => {
    expect(folderDisplayName("C:\\")).toBe("C:");
    expect(folderDisplayName("/")).toBe("/");
  });
});
