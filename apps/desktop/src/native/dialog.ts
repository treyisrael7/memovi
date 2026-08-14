/**
 * Native OS dialogs for the desktop shell.
 *
 * Product pages should go through FilePicker rather than calling this module
 * directly, so folder/file picking stays in one UI component.
 */

export type PickDirectoryOptions = {
  title?: string;
  defaultPath?: string;
};

/**
 * Open the operating-system folder picker.
 *
 * Returns the selected absolute path, or null when the user cancels or the
 * dialog is unavailable (for example, running the Vite UI outside Tauri).
 */
export async function pickDirectory(
  options: PickDirectoryOptions = {},
): Promise<string | null> {
  try {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const selected = await open({
      directory: true,
      multiple: false,
      title: options.title,
      defaultPath: options.defaultPath,
    });
    if (typeof selected === "string" && selected.trim().length > 0) {
      return selected;
    }
    return null;
  } catch {
    return null;
  }
}
