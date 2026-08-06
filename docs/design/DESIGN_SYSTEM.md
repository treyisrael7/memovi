# Memovi Design System

The official visual language and interaction model for the Memovi desktop client
(`apps/desktop`).

This system exists so every screen feels like the same product, and so new
features are assembled from reusable primitives instead of page-specific UI.

Backend behavior is out of scope. Clients remain presentation-only over the
platform API.

---

## Design principles

1. **Consistency over novelty** — prefer shared components and tokens to custom
   one-off styling.
2. **Knowledge OS, not chatbot chrome** — calm, dense, operational surfaces that
   support documents, search, knowledge, automation, and settings.
3. **Clarity over decoration** — hierarchy comes from typography, spacing, and
   tone; avoid ornamental cards and competing accents.
4. **Accessible by default** — keyboard paths, focus visibility, labels, and
   contrast are part of the component contract.
5. **Themeable** — light and dark themes share the same semantic tokens.
6. **Composable** — pages should compose layout + input + feedback primitives
   rather than inventing parallel patterns.

---

## Where things live

| Concern | Path |
| --- | --- |
| Design tokens + base reset | `apps/desktop/src/styles/theme.css` |
| Design-system component styles | `apps/desktop/src/styles/components.css` |
| Shell / page layout styles | `apps/desktop/src/styles/shell.css` |
| React primitives | `apps/desktop/src/components/ui/` |
| Public UI barrel | `apps/desktop/src/components/ui/index.ts` |
| Application chrome | `apps/desktop/src/components/Shell.tsx` and peers |

Import styles from `App.tsx` in this order: `theme.css` → `shell.css` →
`components.css`.

Prefer:

```ts
import { Button, EmptyState, PageLayout } from "./ui";
```

---

## Design tokens

Tokens are CSS custom properties. Use semantic names; avoid hardcoding colors,
spacing, radii, shadows, durations, or z-index values in new UI.

### Color (semantic)

| Token | Purpose |
| --- | --- |
| `--color-bg-app` | App canvas |
| `--color-bg-panel` | Raised surfaces |
| `--color-bg-subtle` | Quiet secondary surfaces |
| `--color-bg-sidebar*` | Navigation chrome |
| `--color-border` / `--color-border-strong` | Dividers and control borders |
| `--color-text` / `--color-text-muted` | Body and secondary text |
| `--color-accent*` | Brand / primary actions |
| `--color-status-ok/warn/bad/idle` | Status and feedback |
| `--color-focus-ring` | Keyboard focus outline |
| `--color-overlay` | Modal scrim |

Light and dark themes map onto the same names via `[data-theme="light|dark"]`.
Legacy aliases (`--bg-app`, `--accent`, …) remain for existing shell CSS.

### Typography

| Token | Purpose |
| --- | --- |
| `--font-sans` / `--font-mono` | Font stacks |
| `--text-xs` … `--text-2xl` | Type scale |
| `--leading-*` | Line height |
| `--weight-*` | Font weight |

### Spacing, radius, shadow, motion, z-index, icons

| Family | Examples |
| --- | --- |
| Spacing | `--space-1` … `--space-12` (4px base) |
| Radius | `--radius-sm` … `--radius-full` |
| Shadow | `--shadow-sm/md/lg` |
| Motion | `--duration-fast/normal/slow`, `--ease-standard` |
| Layers | `--z-sticky`, `--z-dropdown`, `--z-overlay`, `--z-modal`, `--z-toast`, `--z-tooltip` |
| Icons | `--icon-sm/md/lg` |

`prefers-reduced-motion` collapses non-essential animation.

---

## Component library

### Layout

| Component | Use for |
| --- | --- |
| `PageLayout` | Standard page header + body |
| `Sidebar` / `SidebarLayout` | App chrome sidebar frame |
| `TopBar` / `TopBarLayout` | App chrome top bar frame |
| `InspectorPanel` | Detail / inspector pane beside a list |
| `SectionHeader` | In-page section titles |

### Inputs

| Component | Use for |
| --- | --- |
| `Button` | Primary / secondary / danger / ghost actions |
| `IconButton` | Icon-only actions (requires `label`) |
| `TextInput` | Single-line fields |
| `SearchInput` | Search fields |
| `TextArea` | Multi-line fields |
| `Dropdown` | Native select |
| `Checkbox` | Binary options |
| `Toggle` | On/off switches |
| `FilePicker` | File selection trigger |

### Feedback

| Component | Use for |
| --- | --- |
| `LoadingSpinner` / `LoadingState` | Indeterminate loading |
| `Skeleton` | Content placeholders |
| `ProgressBar` | Determinate progress |
| `Toast` / `ToastProvider` / `useToast` | Transient success/error notices |
| `Alert` | Inline page banners |
| `Badge` / `StatusBadge` | Status and metadata pills |
| `EmptyState` | Empty / unavailable regions |

### Display

| Component | Use for |
| --- | --- |
| `Card` | Grouped interactive surfaces |
| `Table` | Tabular data |
| `List` / `ListItem` | Vertical collections |
| `Tabs` / `TabPanel` | Peer view switching |
| `Modal` | General dialogs |
| `ConfirmationDialog` | Destructive / high-stakes confirms |
| `Tooltip` | Short hover/focus hints |
| `Icon` | Inline SVG icon set |

### Navigation

| Component | Use for |
| --- | --- |
| `Breadcrumb` | Hierarchical location |
| `NavigationItem` | Primary/secondary nav items |
| `ContextMenu` | Right-click actions |

`ConfirmDialog` remains as a compatibility alias of `ConfirmationDialog`.

---

## Interaction guidelines

### Loading

- Use `LoadingState` for labeled page/panel loading.
- Use `Skeleton` when preserving layout shape matters.
- Use `Button` `busy` for in-control wait states.
- Do not invent ad-hoc “Loading…” muted paragraphs.

### Empty

- Use `EmptyState` with a short title and optional description/action.
- Empty copy should tell the user what is missing and what to do next.

### Errors

- Use `Alert tone="bad"` for page-level failures.
- Use `useToast(..., "bad")` for action failures that should not block the page.
- Prefer user-facing operational messages; never expose secrets or provider
  internals.

### Confirmation

- Use `ConfirmationDialog` for destructive or irreversible actions.
- Escape and overlay click dismiss when not busy.
- Focus is trapped inside the dialog.

### Success

- Prefer toast notifications for completed actions (`tone="ok"`).
- Do not invent custom success banners when a toast is enough.

### Keyboard

| Pattern | Expectation |
| --- | --- |
| Chat composer | Enter sends; Shift+Enter inserts a newline |
| Dialogs | Escape cancels when idle; Tab cycles focus |
| Tables / lists | Enter/Space activate interactive rows |
| Tabs | Click / focusable tab buttons with `aria-selected` |
| Context menu | Escape dismisses |

### Focus

- `:focus-visible` uses `--color-focus-ring`.
- Do not remove focus outlines.
- Icon-only controls must expose an accessible name (`IconButton` enforces this).

### Scroll

- Shell main content scrolls; chat uses a dedicated non-padded content region.
- Inspector and list panes scroll independently within their regions.
- Prefer contained overflow over nested body scrollbars.

### Theme

- Theme is light/dark via `data-theme` on `<html>`.
- Preference persists in `localStorage` (`memovi.desktop.theme`).
- Sidebar toggle and Settings → Appearance share the same state.

---

## Accessibility expectations

- Interactive controls are reachable by keyboard.
- Focus is always visible for keyboard users.
- Buttons, switches, tabs, dialogs, and progress use appropriate roles/ARIA.
- Color is never the only status signal; pair with text labels (`Badge`,
  `Alert`, status copy).
- Contrast should remain readable in both themes against semantic surfaces.
- Decorative icons are `aria-hidden`; informative icons provide a title/label.
- Screen-reader live regions are used for toasts and polite loading status.

Accessibility is part of the design system, not an afterthought for individual
pages.

---

## Building a new page

1. Register the page in `navigation/pages.ts` only when it is real, not a
   placeholder.
2. Compose with `PageLayout` / `SectionHeader` / `InspectorPanel` as needed.
3. Use `Button`, form controls, `EmptyState`, `LoadingState`, `Alert`, and
   `ConfirmationDialog` instead of raw classNames.
4. Read tokens from CSS variables; do not hardcode theme values.
5. Keep domain logic in the API client / backend — UI stays presentational.

---

## Related documents

- [`../architecture/DESKTOP_CLIENT.md`](../architecture/DESKTOP_CLIENT.md) —
  desktop shell architecture and API boundaries
- [`../PRODUCT_VISION.md`](../PRODUCT_VISION.md) — product identity
- [`../STATUS.md`](../STATUS.md) — milestone progress
