/**
 * Presentation helper for connected-folder paths.
 * Full paths remain the source of truth; cards may show only the last segment.
 */
export function folderDisplayName(path: string): string {
  const trimmed = path.trim().replace(/[\\/]+$/, "");
  if (!trimmed) {
    return path.trim();
  }
  const segments = trimmed
    .split(/[\\/]/)
    .filter((segment) => segment.length > 0);
  return segments[segments.length - 1] ?? trimmed;
}
