# Browser Capability

# Purpose

This document defines Memovi's Browser Capability: structured access to web
resources implemented on the Capability Framework and invoked only through the
Capability Execution Engine.

# Scope

It covers architecture, the browser provider abstraction, the operation
lifecycle, the permission and safety model, download integration with the
Filesystem Capability, structured result philosophy, errors, desktop
presentation, and auditing.

It does not define headless browser automation product features, multi-step
scraping planners, or desktop WebView control.

# Relationship to ARCHITECTURE.md

[`../ARCHITECTURE.md`](../ARCHITECTURE.md),
[`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md), and
[`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md) establish that environment
actions belong to Automation capabilities. This document describes the production
Browser Capability in `memovi_automation.browser`.

# Architecture

```text
Conversation
    ↓
Intelligence
    ↓
Capability Execution Engine
    ↓
Browser Capability
    ↓
Browser Provider (private)
    ↓
Structured Result
```

Key rules:

* Intelligence never issues browser-specific commands or DOM APIs.
* Desktop never calls browser/network APIs directly.
* The Browser Capability may use urllib, an HTTP client, or a headless engine;
  that choice is an implementation detail and must not leak into results.
* Downloads persist under Filesystem Capability roots via shared path safety.
* Production composition registers Browser on the Capability Registry and seeds
  an Ask Every Time permission mode.

Capability id: `browser`

Package path: `packages/automation/src/memovi_automation/browser/`

# Browser Abstraction

| Type | Role |
| --- | --- |
| `BrowserCapability` | Capability Framework adapter (`metadata` + `execute`) |
| `BrowserProvider` | Private protocol for fetch / search / download bytes |
| `HttpBrowserProvider` | Default stdlib HTTP implementation |
| `BrowserCapabilityConfig` | Timeouts, size caps, download roots, user agent |

Callers never receive `BrowserProvider`, raw sockets, response objects, or HTML
parser internals.

# Operation Lifecycle

1. **Submit** — client or Intelligence submits
   `CapabilityExecutionRequest(capability_id="browser", arguments={operation, …})`.
2. **Authorize** — engine resolves Allow / Ask Every Time / Deny.
3. **Approve** (when required) — desktop shows preview (especially downloads).
4. **Execute** — engine grants declared Browser permissions into
   `CapabilityContext`, then invokes the capability.
5. **Validate** — capability checks per-operation permission, validates URLs,
   and rejects malformed / unsupported schemes.
6. **Run** — private provider performs network work with timeout + cancellation.
7. **Normalize** — structured result is returned (`NavigationResult`,
   `ExtractedContent`, `SearchResults`, `DownloadResult`, …).
8. **Audit** — engine records workspace, URL (redacted), operation, timestamp,
   duration, and result summary.

# Supported Operations

| Operation | Permission | Result shape |
| --- | --- | --- |
| `open_url` | `browser.read` | `NavigationResult` (title, redirects, status) |
| `read_page` | `browser.read` | `BrowserPage` (readable content + links + metadata) |
| `extract_content` | `browser.read` | `ExtractedContent` |
| `extract_links` | `browser.read` | Link list |
| `extract_metadata` | `browser.read` | `PageMetadata` |
| `search_web` | `browser.search` | `SearchResults` |
| `download_file` | `browser.download` | `DownloadResult` |

# Structured Browser APIs

Callers receive normalized dictionaries, not browser engine objects:

* `NavigationResult` — url, final_url, status_code, title, redirected, duration
* `BrowserPage` — navigation fields + content + links + page_metadata
* `ExtractedContent` — title + readable content
* `PageMetadata` — title, content_type, status_code, page_metadata map
* `SearchResults` — query + results[{title, url, snippet}] + result_count
* `DownloadResult` — destination, bytes_written, sha256, content_type

Do not expose:

* Raw `urllib` / HTTP response objects
* Browser automation handles (Playwright/Puppeteer pages)
* Unparsed HTML dumps as the primary contract
* Credentials or sensitive query parameters in audit/UI payloads

# Permission Model

| Permission | Role |
| --- | --- |
| `browser.read` | Open/read pages and extract content/links/metadata |
| `browser.search` | Perform web search |
| `browser.download` | Download files into workspace roots |

Engine-level modes still apply to the whole capability:

* Allow
* Ask Every Time (default)
* Deny

Downloads should remain behind Ask Every Time in production so users confirm
before bytes are written.

# Safety

* Only `http` and `https` URLs are accepted; other schemes are rejected.
* Malformed URLs raise `invalid_url`.
* Download destinations must resolve under `BrowserCapabilityConfig.download_roots`
  (`MEMOVI_BROWSER_DOWNLOAD_ROOTS`, falling back to filesystem roots) using the
  same path-safety rules as the Filesystem Capability.
* Response and download sizes are capped.
* Timeouts and cancellation stop in-flight network reads.
* Sensitive query parameters are redacted in audit arguments and returned URLs.

# Download Lifecycle

1. User/Intelligence submits `download_file` with `url` + `destination`.
2. Engine pauses at Ask Every Time (default) until desktop approves.
3. Capability validates URL and resolves destination under download roots.
4. A staging file (`*.memovi-partial`) is created under the same root.
5. Provider streams bytes with progress callbacks (`bytes_received`, `progress`).
6. On success, staging is atomically replaced onto the final destination; SHA-256
   is computed.
7. On cancel or failure, staging is deleted so no partial final file remains.
8. `DownloadResult` is returned; audit records URL, destination, size, hash.

Integrity verification uses SHA-256 of the downloaded payload. Overwrite requires
an explicit `overwrite: true` argument; otherwise an existing destination fails
with `destination_exists`.

# Errors

Normalized codes include:

| Code | Meaning |
| --- | --- |
| `permission_denied` | Missing read/search/download permission or engine deny |
| `invalid_url` | Missing, malformed, or unsupported scheme |
| `invalid_query` | Missing search query |
| `invalid_destination` | Destination outside filesystem/download roots |
| `network_unavailable` | Host unreachable / network failure |
| `download_failed` | HTTP failure or filesystem write failure |
| `download_too_large` | Payload exceeds configured cap |
| `timeout` | Request exceeded timeout |
| `unsupported_content` | Non-HTML where a page read was required |
| `destination_exists` | Download target exists and overwrite is false |
| `unsupported_operation` | Unknown operation name |

Raw browser/HTTP exceptions are never returned to clients.

# Desktop

Desktop owns presentation only:

* Navigation / download progress
* Search result lists
* Download confirmation prompts
* Friendly error messages
* Cancel while executing

No browser business logic belongs in the desktop client.

# Auditing

Every status transition appends an audit entry including:

* Workspace
* URL (sensitive query params redacted)
* Operation
* Timestamp
* Duration
* Result summary (destination/sha256/result_count when available)

# Configuration

| Setting / env | Role |
| --- | --- |
| `MEMOVI_BROWSER_DOWNLOAD_ROOTS` | Allowed download roots |
| Fallback | Filesystem capability roots |
| `default_timeout_seconds` / `max_timeout_seconds` | Execution bounds |
| `max_response_bytes` | Page/body capture cap |
| `max_download_bytes` | Download size cap |
| `default_search_limit` / `max_search_limit` | Search bounds |

# Related Documents

* [`CAPABILITY_FRAMEWORK.md`](CAPABILITY_FRAMEWORK.md)
* [`CAPABILITY_EXECUTION.md`](CAPABILITY_EXECUTION.md)
* [`FILESYSTEM_CAPABILITY.md`](FILESYSTEM_CAPABILITY.md)
* [`TERMINAL_CAPABILITY.md`](TERMINAL_CAPABILITY.md)
* [`GIT_CAPABILITY.md`](GIT_CAPABILITY.md)
* [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
* [`../STATUS.md`](../STATUS.md)
* [`../ROADMAP.md`](../ROADMAP.md)
