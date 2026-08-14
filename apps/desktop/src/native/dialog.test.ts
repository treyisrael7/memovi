import { beforeEach, describe, expect, it, vi } from "vitest";

const open = vi.fn();

vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: (...args: unknown[]) => open(...args),
}));

describe("pickDirectory", () => {
  beforeEach(() => {
    open.mockReset();
    vi.resetModules();
  });

  it("returns the selected folder path", async () => {
    open.mockResolvedValue("C:\\Users\\you\\notes");
    const { pickDirectory } = await import("./dialog");

    await expect(pickDirectory({ title: "Select folder" })).resolves.toBe(
      "C:\\Users\\you\\notes",
    );
    expect(open).toHaveBeenCalledWith({
      directory: true,
      multiple: false,
      title: "Select folder",
      defaultPath: undefined,
    });
  });

  it("returns null when the user cancels", async () => {
    open.mockResolvedValue(null);
    const { pickDirectory } = await import("./dialog");

    await expect(pickDirectory()).resolves.toBeNull();
  });

  it("returns null when the dialog is unavailable", async () => {
    open.mockRejectedValue(new Error("not in tauri"));
    const { pickDirectory } = await import("./dialog");

    await expect(pickDirectory()).resolves.toBeNull();
  });
});
