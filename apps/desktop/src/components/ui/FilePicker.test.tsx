import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../native/dialog", () => ({
  pickDirectory: vi.fn(),
}));

import { pickDirectory } from "../../native/dialog";
import { FilePicker } from "./FilePicker";

describe("FilePicker directory mode", () => {
  it("populates the callback with the selected folder path", async () => {
    const user = userEvent.setup();
    vi.mocked(pickDirectory).mockResolvedValue("/home/you/notes");
    const onDirectorySelected = vi.fn();

    render(
      <FilePicker
        mode="directory"
        defaultPath="/home/you"
        onDirectorySelected={onDirectorySelected}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Browse..." }));

    expect(pickDirectory).toHaveBeenCalledWith({
      title: "Select folder",
      defaultPath: "/home/you",
    });
    expect(onDirectorySelected).toHaveBeenCalledWith("/home/you/notes");
  });

  it("does not call the callback when the dialog is cancelled", async () => {
    const user = userEvent.setup();
    vi.mocked(pickDirectory).mockResolvedValue(null);
    const onDirectorySelected = vi.fn();

    render(
      <FilePicker mode="directory" onDirectorySelected={onDirectorySelected} />,
    );

    await user.click(screen.getByRole("button", { name: "Browse..." }));

    expect(onDirectorySelected).not.toHaveBeenCalled();
  });
});
