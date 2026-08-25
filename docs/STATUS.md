# Memovi Status

Living implementation tracker for Memovi as a desktop-first knowledge operating
system on a reusable backend platform. Last reviewed: 2026-08-17 (status
reconciliation against shipped V1).

* [`README.md`](../README.md) — public 0.1.0 pre-alpha / public-development entry
* [`ARCHITECTURE.md`](ARCHITECTURE.md) — current V1 vs future / V2
* [`ROADMAP.md`](ROADMAP.md) — remaining V1 is **release hardening**, not core build
* [`ROADMAP_V2.md`](ROADMAP_V2.md) — deferred capabilities
* Historical milestones below are preserved. **Current V1** is the snapshot in
  the next section, not an early “Remaining” list inside Milestone 0–6.

---

# Current V1 (2026-08-17)

Memovi is **0.1.0 pre-alpha / public-development**. The core product path is
implemented. This is not a finished stable 1.0.

**Implemented (do not treat as unfinished V1):** local auth and workspaces
(including member APIs and membership audit), document upload + MinIO +
in-process processing worker, Memory / Collections / Tags, keyword-semantic-hybrid
search and embeddings, RAG conversations with citations, Capability Framework +
planner + execution engine + workflows (approval/resume), filesystem connector
(manual sync), desktop product UI, observability/logging/ready, Postgres +
MinIO, fake + OpenAI reasoning, configurable embeddings, live desktop/API smoke.

**V1 host execution model:** Capabilities → Planner → Execution Engine →
Workflow Engine. `ToolRegistry` / `ToolExecutor` are **removed** (Milestone 49).
`ToolCall` / `ToolResult` are unused type plumbing only. Redis is **not used
in V1**.

**Remaining V1 (release hardening, not new architecture):**

* OSS process files (SECURITY, code of conduct, issue/PR templates) — separate PR
* Contributor / operator docs polish after README + architecture truth passes
* Coverage floor is enforced at 80% on application sources; measured total
  meets the **80%** requirement
* Linux Tauri packaging in CI; Windows/macOS packaging matrix and signing not done
* Packaged WebView session cookies: API flags proven; native jar is local
  (`task desktop:smoke:native` / [`testing/NATIVE_DESKTOP_SMOKE.md`](testing/NATIVE_DESKTOP_SMOKE.md)), not CI
* No GitHub Release / tag automation
* Operator UX follow-ups: capability permission settings UI, deeper model /
  workspace / indexing-status product depth
* Architecture boundary tests (never shipped; not a user-facing V1 blocker)

**Explicitly not V1 (see ROADMAP_V2):** OCR, extra connectors (GitHub, Drive,
Slack, Notion), knowledge graph, AI summaries as a pipeline, plugin SDK,
distributed workers, Redis, Prometheus/Grafana/Loki stack, native Tauri E2E,
multi-agent systems.

---

# Milestone 0 — Foundation

**Overall Status:** Complete

Engineering foundation is in place: workspaces, local infrastructure, CI, tooling, and documentation.

**Completed**

* Repository and workspace layout
* Local Docker Compose infrastructure
* CI, quality tooling, pre-commit, and documentation

**In Progress**

* None

**Remaining**

* None for this milestone

**Known Risks**

* None material

**Next Recommended Work**

* Maintain foundation as later milestones add packages and ops surface

---

# Milestone 1 — Platform

**Overall Status:** Complete for V1 (typed config in Milestone 36)

Backend composition root is operational. Observability foundation (request context, structured logs, diagnostic bridge, metrics, readiness) is in place. Typed configuration is wired through `memovi_config`. Architecture boundary tests were never added; they are a V1 follow-up, not an open product milestone.

**Completed**

* FastAPI composition root and bootstrap
* Dependency injection and router registration
* Health liveness (`/health`) and readiness (`/ready`) endpoints
* Domain packages for auth, documents, search, and intelligence
* `memovi_observability` RequestContext, structured JSON logging, diagnostic event bridge, metrics recorder, and OpenTelemetry-API spans
* Typed `memovi_config` settings, env parsing, secrets, and startup validation (Milestone 36)

**In Progress**

* None

**Remaining**

* Architecture tests validating package boundaries (deferred follow-up; not a V1
  product blocker)

**Known Risks**

* None specific to typed config after Milestone 36

**Next Recommended Work**

* Optional: add architecture boundary tests during release hardening

---

# Milestone 2 — Identity & Ownership

**Overall Status:** Complete (superseded hardening in Milestone 28)

Local authentication works. Workspace membership is validated on workspace-scoped
APIs. Capability authorization and durable audit are covered by Milestone 28.

**Completed**

* User registration
* Secure local login
* HTTP-only session cookies
* Session persistence and logout
* Current-user API boundary
* Workspace domain (`packages/workspace`) with Default Workspace seed
* `WorkspaceId` shared primitive and repository-level workspace isolation
* Optional `X-Memovi-Workspace-Id` API resolution with Default fallback
* Authenticated workspace membership checks (Milestone 28)

**In Progress**

* None

**Remaining**

* None for V1 identity. Owner / member APIs and membership audit shipped in
  Milestone 43.

**Known Risks**

* None specific — desktop now authenticates end-to-end via session cookies

**Next Recommended Work**

* Keep membership covered in the desktop release checklist

---

# Milestone 3 — Knowledge Ingestion

**Overall Status:** Complete for V1

Upload-to-processing pipeline is operational (PDF, Markdown, plain text). The
Connector Framework (Milestone 32) plus Filesystem Connector (Milestone 44)
import local folders through Documents. OCR and additional cloud connectors are
**V2 / future**, not remaining V1 work.

**Completed**

* Document uploads (`POST /documents`)
* MinIO-backed object storage (explicit backend; no silent in-memory fallback — PR #9)
* Document processing engine for PDF, Markdown, and plain text
* Processing queue and background worker
* Chunk generation via Memory materialization on `ProcessingCompleted`
* Event-driven handoff into Memory
* Connector Framework foundation (`memovi-connectors`: registry, sync, normalize,
  health, scheduler foundation, `DocumentImportPort`)
* Filesystem Connector: folder registration, manual sync, Documents provenance

**In Progress**

* None for V1

**Remaining (V2 / future, not V1 blockers)**

* OCR pipeline
* Additional connector providers (GitHub, Drive, Slack, …)
* Deeper metadata extraction beyond ingest/process basics

**Known Risks**

* Unsupported formats (no OCR) limit ingestion to extractable text types

**Next Recommended Work**

* Keep processing visibility covered by desktop smoke; extra formats/connectors
  belong on ROADMAP_V2

---

# Milestone 4 — Knowledge Platform

**Overall Status:** Complete for V1

Memory materialization, explorer APIs, Collections, and Tags are shipped.
Version history and a knowledge graph are **V2**. Explorer
concepts/relationships are provenance projections, not graph infrastructure.

**Completed**

* Memory domain core for chunk materialization and persistence from processing events
* Knowledge Collections organization (Milestone 33): create/rename/delete, memberships,
  summaries, search filter, desktop management
* Tags + resource metadata V1 (Milestone 45): first-class tags complementary to Collections,
  assignment API, search member-id resolution with AND semantics, polymorphic metadata upsert

**In Progress**

* None for V1

**Remaining (V2 / follow-up)**

* Version history
* Knowledge relationships beyond provenance edges
* Deeper metadata management UX beyond the V1 upsert API
* Semantic entity/topic extraction (not V1)

**Known Risks**

* None specific for Tags V1 beyond case-insensitive name uniqueness

**Next Recommended Work**

* Keep Collections and Tags complementary; do not add a graph for V1

---

# Milestone 5 — Retrieval Intelligence

**Overall Status:** Complete for V1

Keyword, semantic, and hybrid retrieval are operational. Query planning, cache /
summary lookup, and learned rerank are **V2**.

**Completed**

* Full-text / keyword retrieval
* Vector / semantic retrieval (pgvector)
* Hybrid retrieval with Reciprocal Rank Fusion
* Metadata filtering
* Stable search APIs (`GET /search`)

**In Progress**

* None for V1

**Remaining (V2)**

* Query planning and context budgeting
* Cache and summary lookup paths
* Learned reranker (score normalization + RRF is V1)

**Known Risks**

* Retrieval is search-centric; cost-aware summary/cache paths are not V1

**Next Recommended Work**

* Do not block public V1 on query planning; keep hybrid search covered by tests

---

# Milestone 6 — Reasoning Engine

**Overall Status:** Complete for V1

Reasoning pipeline, conversation memory, Conversation REST API (including list,
rename, delete, and SSE streaming), and Search-backed retrieval are operational.
Desktop Chat consumes that API. AI summaries as a knowledge pipeline are **V2**.

**Completed**

* Reasoning pipeline (retrieve → assemble → prompt → provider)
* Conversation memory (`ConversationService`, history-aware context)
* Conversation REST API (create/list/get/rename/delete, list/send messages, SSE stream)
* Conversation titles and workspace-scoped listing
* Per-request provider/model selection on send/stream
* Execution traces and citations
* Provider gateway with `fake` and `openai` adapters (including token streaming)
* Search-backed knowledge retrieval (`SearchKnowledgeRetriever` in `apps/api`)
* Durable conversation storage (`SqlAlchemyConversationRepository` in `apps/api`)

**In Progress**

* None for V1

**Remaining (V2 / follow-up)**

* AI summaries as a product pipeline
* Additional live reasoning adapters (config enums are not adapters)
* Prompt library / versioning product
* WebSocket channels beyond SSE (only if needed)

**Known Risks**

* Reserved `ReasoningProviderKind` names (`anthropic`, `ollama`, `gemini`) are
  not live adapters. V1 `INTELLIGENCE_PROVIDER` accepts only `fake` and `openai`;
  other values fail configuration validation at startup.

**Next Recommended Work**

* Keep fake/OpenAI path covered; do not claim Anthropic/Ollama/Gemini reasoning

---

# Milestone 17 — Model Provider Framework

**Overall Status:** Removed (Milestone 46)

The unused `packages/models` (`memovi-models`) parallel framework was deleted.
Live provider selection remains `ModelGateway` + `ReasoningProvider` in
`packages/intelligence`. No migration onto a separate models package is planned
for V1.

**Completed**

* N/A — package removed; see Milestone 46

**In Progress**

* None

**Remaining**

* None

**Known Risks**

* None

**Next Recommended Work**

* Keep extending `ModelGateway` / `ReasoningProvider` adapters as needed

---

# Milestone 19 — Conversation Experience

**Overall Status:** Complete

Desktop Chat is the first functional conversation surface. It consumes Conversation
and Intelligence APIs only; no domain logic lives in the client.

**Completed**

* Conversation list / create / rename / delete
* Conversation history persistence via backend APIs
* SSE token streaming with stop (AbortController) and clean error surfacing
* Markdown rendering, code blocks, copy message / copy code
* Enter to send, Shift+Enter newline, auto-scroll, retry failed responses
* Top-bar workspace and model selection reflected in stream requests
* Workspace switching reloads isolated conversation lists
* `docs/architecture/DESKTOP_CLIENT.md` conversation flow

**Remaining**

* Multi-chat tabs, prompt library, agents, voice, images, automation, plugins (explicitly out of scope)

---

# Milestone 20 — Knowledge Explorer

**Overall Status:** Complete

Desktop Knowledge Explorer is the first read-only inspection surface for answering
"What does Memovi know?" without asking the AI. It consumes Memory, Documents, and
Search APIs only; no knowledge business logic lives in the client.

**Completed**

* Memory HTTP read APIs (`/memory`, detail, dashboard, concepts, relationships)
* Documents list/get HTTP for Sources (`GET /documents`, `GET /documents/{id}`)
* Desktop Knowledge page with Overview, Search, Concepts, Entities, Relationships, Sources
* List + detail inspection with source links, related concepts/entities, confidence, timestamps
* Full-text search with immediate updates and workspace / document / entity-type filters
* Workspace isolation via `X-Memovi-Workspace-Id`
* `docs/architecture/KNOWLEDGE_EXPLORER.md`

**Remaining**

* Graph visualization, manual editing, merging, deleting, auto-corrections, version history (explicitly out of scope)
* Semantic entity/topic extraction and confidence scoring (future pipeline stages)

---

# Milestone 21 — Capability Execution Engine

**Overall Status:** Complete

Conversations and API clients invoke registered capabilities only through the
Capability Execution Engine. Intelligence never calls capabilities directly.

**Completed**

* `CapabilityExecutionEngine` with resolve → authorize → invoke → audit pipeline
* Execution types: request, context, result, status, audit entry; permission modes
  (`always_allow`, `ask_every_time`, `deny`)
* HTTP surface under `/capabilities` (list, submit, approve, cancel, audit, policy)
* Conversation bridge: `POST/GET /conversations/{id}/capability-executions`
* Composition-root registration of Filesystem capability + Intelligence port adapter
* Desktop Chat pending-approval / progress / result presentation
* `docs/architecture/CAPABILITY_EXECUTION.md`

**Remaining**

* Desktop settings UI for capability permission policies (V1 operator follow-up)
* Additional concrete capabilities (Clipboard, Notifications) — **V2**
* Durable execution **state** shipped in Milestone 38 (`SqlAlchemyExecutionStateStore`);
  `SqlAlchemyExecutionAuditStore` exists — do not list audit as missing V1 architecture

---

# Milestone 22 — Filesystem Write Capability

**Overall Status:** Complete

The Filesystem Capability is the trusted interface for creating, modifying,
moving, copying, renaming, and deleting files. The Capability Execution Engine
remains responsible for permission modes, approval, and audit.

**Completed**

* Write operations: create file/directory, replace, append, rename, copy, move, delete
* Overwrite policies: `reject` (default), `ask_user`, `replace` — never silent overwrite
* Deletion modes: `trash` (default when available) and explicit `permanent`
* Fine-grained permissions: `filesystem.create` / `modify` / `move` / `delete`
  plus coarse `filesystem.write` umbrella
* Structured success/error payloads; content redacted in audit arguments
* Desktop confirmation, progress, success/failure, overwrite Replace, and undo messaging
* `docs/architecture/FILESYSTEM_WRITE.md`

**Verified**

* Filesystem — existing read operations still function
* Capability Engine — writes execute through the Execution Engine (production path)
* Permissions — read-only cannot write; ask-every-time prompts before run; deny blocks
* Knowledge — indexed documents untouched (no documents/memory coupling)
* Desktop — confirmation, progress, and friendly failure messages
* Observability — audit records for writes; request/correlation IDs on execution + audit
* Regression — automation suite green; full suite green aside from intermittent unrelated documents worker flake

**Remaining**

* Desktop settings UI for capability permission policies (V1 operator follow-up)
* Autonomous workflows and background scheduling (explicitly out of scope / V2)

---

# Milestone 23 — Terminal Capability

**Overall Status:** Complete

The Terminal Capability executes operating-system commands through the Capability
Execution Engine. The LLM never receives a raw shell; all runs are structured
capability requests with engine-owned permission modes, approval, and audit.

**Completed**

* `TerminalCapability` (`terminal`) with `terminal.execute` permission
* Execute command / working directory / env / timeout support
* Capture stdout, stderr, exit code, and duration in structured results
* Safety: Ask/Allow/Deny via engine, max timeout, max output size, process termination
* Reject empty commands and invalid working directories
* Cancellation of pending and in-flight terminal processes
* Audit records with command, cwd, duration, exit code; sensitive env redacted
* Desktop: command preview, approval dialog, live status, streaming stdout when available, exit status, cancel
* Composition-root registration (`MEMOVI_TERMINAL_ROOTS`, fallback to filesystem roots)
* `docs/architecture/TERMINAL_CAPABILITY.md`

**Verified**

* Filesystem — read and write operations remain unaffected
* Capability Engine — terminal executes exclusively through the Execution Engine; existing capabilities continue functioning
* Desktop — approval dialogs, progress during execution, and cancellation UI updates
* Observability — request/correlation IDs propagate; audit/result summaries include terminal execution metadata
* Permissions — Allow / Ask Every Time / Deny continue working across capabilities
* Regression — full automated suite green (`468 passed, 23 skipped`) including terminal acceptance checklist

**Remaining**

* Desktop settings UI for capability permission policies (V1 operator follow-up)
* True push/SSE streaming for capability output (polling + best-effort progress today)

---

# Milestone 24 — Git Capability

**Overall Status:** Complete

The Git Capability exposes structured repository operations through the Capability
Execution Engine. Intelligence requests status, branches, commits, diffs, and
remotes without constructing shell commands. CLI details stay private to
`memovi_automation.git`.

**Completed**

* `GitCapability` (`git`) with `git.read` / `git.write` / `git.network`
* Repository detect/info, status, branches, stage/unstage/commit/history, diff, fetch/pull/push
* Structured results (no raw CLI dumps); normalized Git errors
* Root-scoped repository paths (`MEMOVI_GIT_ROOTS`), timeouts, cancellation
* Desktop status/branch/history/diff presentation + write/network approval copy
* Composition-root registration and Ask Every Time seeding
* `docs/architecture/GIT_CAPABILITY.md`

**Verified**

* Filesystem — read/write capabilities remain unaffected
* Terminal — continues functioning independently; Git does not expose raw terminal commands
* Capability Engine — all Git operations execute through the Execution Engine
* Desktop — approval dialogs and progress indicators continue working
* Permissions — `git.read` blocks repository modifications; `git.network` controls fetch/pull/push
* Observability — structured audit/result summaries include Git metadata; request/correlation IDs propagate
* Regression — full automated suite green (`491 passed, 23 skipped`) including git acceptance checklist

**Remaining**

* Desktop settings UI for capability permission policies (V1 operator follow-up)
* Richer dedicated Git product page beyond Chat capability panel (follow-up / V2)

---

# Milestone 25 — Browser Capability

**Overall Status:** Complete

The Browser Capability exposes structured web operations through the Capability
Execution Engine. Intelligence requests open/read/search/download without issuing
browser-specific commands. Downloads persist under Filesystem Capability roots.

**Completed**

* `BrowserCapability` (`browser`) with `browser.read` / `browser.search` / `browser.download`
* Navigation (`open_url`), reading (`read_page`, extract content/links/metadata), `search_web`, `download_file`
* Structured results (`NavigationResult`, `BrowserPage`, `SearchResults`, `DownloadResult`, …)
* Private `BrowserProvider` abstraction + default HTTP provider; normalized browser errors
* URL safety (http/https only), sensitive query redaction in audit/results
* Download lifecycle: confirmation, progress, cancellation, SHA-256, filesystem root integration
* Desktop navigation/download progress, approval prompts, search/download presentation
* Composition-root registration (`MEMOVI_BROWSER_DOWNLOAD_ROOTS`) and Ask Every Time seeding
* `docs/architecture/BROWSER_CAPABILITY.md`

**Verified**

* Capability Engine — browser operations execute exclusively through the Capability Execution Engine
* Filesystem — downloads are saved through Filesystem Capability roots; existing read/write operations remain unaffected
* Terminal — Terminal Capability remains unaffected
* Git — Git operations continue functioning normally
* Desktop — approval dialogs display correctly; navigation and download progress update correctly; browser errors are presented cleanly
* Permissions — Read, Search, and Download permissions are enforced independently
* Observability — structured logs/audit include browser metadata; request/correlation IDs propagate correctly
* Regression — full automated suite green (`514 passed, 23 skipped`) including browser acceptance checklist

**Remaining**

* Desktop settings UI for capability permission policies (V1 operator follow-up)
* Richer dedicated Browser product surface beyond Chat capability panel (follow-up / V2)

---

# Milestone 26 — Capability Planner

**Overall Status:** Complete

The Capability Planner lets Intelligence create validated, deterministic execution
plans before any capability runs. Planning never executes capabilities; plan steps
are submitted only through the Capability Execution Engine.

**Completed**

* `CapabilityPlanner`, `ExecutionPlanValidator`, `PlanExecutionService`
* Plan contracts: `ExecutionPlan`, `ExecutionStep`, `ExecutionDependency`, `ExecutionPlanResult`
* Validation: capability exists, operation supported, argument schema, dependency graph
* Intelligence port + conversation use cases + HTTP create/execute plan endpoints
* Composition-root wiring; planner has no direct capability/invoker execute path
* `docs/architecture/CAPABILITY_PLANNER.md`

**Verified**

* Intelligence generates validated execution plans
* Multi-step Browser + Filesystem plans produce correct ordered steps and dependencies
* Invalid plans are rejected before execution begins (no engine/provider side effects)
* Plans execute exclusively through the Capability Execution Engine
* Planner output is deterministic for identical requests (stable content-derived plan ids)
* Planner itself never invokes capabilities
* Regression — full automated suite green (`530 passed, 23 skipped`) including planner acceptance

**Remaining**

* Conditional execution, loops, scheduled/background workflow runners (future Automation)
* Durable plan persistence and richer task orchestration UX

---

# Milestone 27 — Workflow Automation

**Overall Status:** Complete

The Workflow Automation Framework lets users run reusable, declarative sequences
of capabilities. Workflows validate variables, materialize each step through the
Capability Planner, execute only via the Capability Execution Engine, and record
structured history.

**Completed**

* `WorkflowEngine`, `WorkflowValidator`, `WorkflowHistory` (+ in-memory store/library)
* Contracts: `WorkflowDefinition`, `WorkflowStep`, `WorkflowVariable`, `WorkflowContext`,
  `WorkflowInstance`, `WorkflowExecutionResult`, `WorkflowHistoryEntry`
* Sequential execution with input/output mapping and `${var}` / `${steps…}` substitution
* Built-in library workflows; HTTP `/workflows` list/get/execute/history
* Desktop Workflows page: library, run, progress, history (presentation only)
* `docs/architecture/WORKFLOW_AUTOMATION.md`

**Verified**

* Browser + Filesystem `download-and-verify` workflow: ordered steps, output mapping
* Terminal `run-command` and Git workflows execute through planner + engine
* Approval pauses until engine approve; intentional failures stop with structured errors
* Variables validated before planner/engine side effects
* History + per-step audit entries recorded; plans generated before each step runs
* Structured logs include `workflow_id`; ambient `request_id` propagates to every step
* Regression checklist covers planner independence, engine solo path, permissions, FS/Terminal/Git/Browser
* Full automated suite green (`559 passed, 23 skipped`)

**Remaining**

* Loops, parallel execution, conditionals
* Background / scheduled workflow runners

---

# Milestone 28 — Platform Hardening I: Authorization & Capability Security

**Overall Status:** Complete

Server-owned authorization for capability execution. Clients request actions;
they do not decide authorization. Authenticated execution context, membership
validation, durable capability policies, and durable audit storage are in place.

**Completed**

* Authentication middleware for non-public endpoints (`/health` and `/ready` remain public)
* `AuthenticatedPrincipal` + authenticated workspace membership validation
* `CapabilityAuthorizationService` (Authorization Service)
* `AuthenticatedExecutionContext` required by Capability Execution Engine
* Durable capability policies (`automation_capability_policies`)
* Durable capability audits (`automation_execution_audits`) with user/operation
* Removed client-controlled `permission_mode` from public execution request contracts
* Workspace membership persistence (`workspace_memberships`) + Default Workspace enrollment on register
* `docs/architecture/AUTHORIZATION.md`

**Verified**

* Capability policy resolution ignores client-supplied permission overrides
* Ask Every Time / Deny / Always Allow remain server-owned
* Filesystem, Terminal, Git, Browser, and Workflow execute only through authorized engine context
* Audit entries include user and survive process/DB-backed store reloads

**Remaining**

* Additional roles beyond owner/member (deferred; V1 uses owner/member)
* Broader non-membership domain audit (capability + membership audits exist)

---

# Forward Roadmap Status

Future work tracks [`ROADMAP.md`](ROADMAP.md) / [`ROADMAP_V2.md`](ROADMAP_V2.md) Phases 1–6.
Milestones 0–6 above remain the platform foundation tracker; Milestone 17 adds the shared model provider boundary.
Milestone 20 adds the Knowledge Explorer inspection surface. Milestone 21 adds the
Capability Execution Engine. Milestone 23 adds Terminal; Milestone 24 adds Git;
Milestone 25 adds Browser. Milestone 26 adds the Capability Planner. Milestone 27
adds Workflow Automation. Milestone 28 hardens authorization and capability security.

---

# Phase 1 — Complete V1 Platform

**Overall Status:** Complete for the V1 product path (release hardening remains)

Documents, Memory, Search, and Intelligence vertical slices exist. Workspace
ownership is enforced. Observability foundation and typed config are in place.
Remaining work is public-release quality, not rebuilding the platform.

**Completed**

* Core Documents → Memory → Search → Intelligence pipeline paths
* Conversation API with Search-backed retrieval and durable storage
* Workspace ownership boundary with repository and search isolation
* Observability foundation: request context, structured logs, diagnostic event
  bridge, metrics interface, OTel-neutral spans, `/ready` checks
* Typed configuration (Milestone 36)

**In Progress**

* Public V1 release hardening (see Current V1 snapshot)

**Remaining (hardening, not core build)**

* Coverage gate decision, packaging matrices, OSS process files, operator UX
  depth, optional architecture boundary tests

**Known Risks**

* Treating “API stability” as unfinished architecture would hide that clients
  already run against these contracts (desktop live smoke)

**Next Recommended Work**

* Follow [`ROADMAP.md`](ROADMAP.md) remaining V1 list; do not reopen domain design

---

# Phase 2 — Desktop Client

**Overall Status:** Complete for the V1 product path

The flagship Tauri desktop client lives in `apps/desktop`. It launches, probes
backend health/readiness, authenticates, and exposes working product pages over
the platform APIs. Remaining items are packaging and operator-UX depth, not
“build the first pages.”

**Completed**

* `apps/desktop` Tauri + React shell foundation
* Sidebar / top bar / main content / status bar layout
* Backend connection detection, reconnect polling, and friendly errors
* Navigation registry for Home, Chat, Knowledge, Collections, Workflows, Documents, Search,
  Activity, and Settings
* Chat conversation experience (list/create/rename/delete, history, SSE streaming,
  markdown/code copy, stop/retry, workspace + model selectors)
* Knowledge Explorer (overview, search, concepts, entities, relationships, sources)
* Collections page (create/rename/delete, memberships, statistics, activity, search filter)
* Workflows page (library, run, progress, history) over `/workflows`
* Documents, Search, Activity, and Settings product pages
* Home / Settings / Chat guidance for backend OpenAI env setup (no in-app API keys)
* Design system: tokens (light/dark), reusable `components/ui/` library, UX
  standards for loading/empty/error/confirm/toast, and
  `docs/design/DESIGN_SYSTEM.md`
* `docs/architecture/DESKTOP_CLIENT.md`
* `docs/architecture/KNOWLEDGE_EXPLORER.md`
* `docs/architecture/COLLECTIONS.md`
* End-to-end desktop authentication (login/register/logout, session restore,
  expiry handling) over existing `/auth/*` session cookies (Milestone 34)

**In Progress**

* Release packaging and contributor-facing polish (not new product pages)

**Remaining (V1 follow-up / packaging)**

* Model management product depth beyond Settings selectors
* Workspace management product depth beyond Settings (members shipped in M43)
* Indexing status surface beyond Documents processing lifecycle (M42)
* Windows/macOS packaging matrix and signing
* Native Tauri window automation (explicitly not V1)

**Known Risks**

* Desktop requires Rust and host linker tooling beyond Node/Python setup

**Next Recommended Work**

* Keep live and mock smoke green; packaging matrices when cutting installers

---

# Milestone 31 — UX Foundation & Design System

**Overall Status:** Complete

Established the first official desktop design system: centralized tokens,
reusable UI components, shared interaction patterns, accessibility baselines,
and page consistency without changing backend behavior.

**Completed**

* Design tokens for color, typography, spacing, radius, shadow, icons, motion,
  and z-index with light/dark themes
* Component library under `apps/desktop/src/components/ui/` (layout, inputs,
  feedback, display, navigation)
* UX standards for loading, empty, error, confirmation, success, focus, and
  keyboard patterns
* Existing pages retrofitted onto shared primitives where appropriate
* `docs/design/DESIGN_SYSTEM.md`

**In Progress**

* None

**Remaining**

* Gradual replacement of remaining page-local control markup as pages evolve

**Known Risks**

* Page-local CSS in `shell.css` still carries historical styles; prefer tokens
  and `components.css` for new work

**Next Recommended Work**

* Keep new desktop UI on design-system primitives; avoid page-specific controls

---

# Milestone 32 — Connector Framework

**Overall Status:** Complete (foundation)

Implemented the Connector Framework so external systems can import into the
existing Documents pipeline through a shared registry and normalization
contract. Filesystem Connector (Milestone 44) is the V1 production adapter.
Scheduled sync / extra providers are **V2**.

**Completed**

* `memovi-connectors` core types: `Connector`, `ConnectorRegistry`,
  `ConnectorConfiguration`, `ConnectorExecutionContext`, `ConnectorResult`,
  `ConnectorMetadata`, `ConnectorHealth`, `ConnectorScheduler` foundation
* `AuthCredentialRef` credential isolation (env/secret refs, no embedded secrets)
* `NormalizedSourceMetadata` / `NormalizedImportItem` + `DocumentImportPort`
* `FakeConnector` + unit tests
* Composition-root wiring (`configure_connector_framework`)
* `docs/architecture/CONNECTOR_FRAMEWORK.md`

**In Progress**

* None

**Remaining (V2)**

* Additional provider connectors beyond Filesystem (GitHub / Drive / Slack / Notion)
* Scheduled synchronization runner / filesystem watchers

**Known Risks**

* Provider work must keep feeding Documents — never invent parallel stores

**Next Recommended Work**

* Do not treat GitHub/Drive/Slack as V1; filesystem connector is the V1 adapter

---

# Milestone 33 — Knowledge Collections & Organization

**Overall Status:** Complete (V1)

Introduced first-class Knowledge Collections so users can organize Documents,
Knowledge, Conversations, and Workflows into flat, workspace-scoped groups
without changing the ingestion pipeline.

**Completed**

* Memory domain: `Collection`, `CollectionMembership`, `CollectionMetadata`,
  `CollectionSummary`, `CollectionRepository`, `CollectionService`
* Membership kinds: document, knowledge, conversation, workflow (with reason)
* Persistence: `memory_collections`, `memory_collection_memberships`,
  `memory_collection_activity` (+ Alembic `20260807_0012`)
* HTTP API `/collections` (CRUD, members, summary)
* Search integration: `collection_id` filter via membership resolution
* Desktop Collections page + Search collection filter
* Unit tests for collection service behavior
* `docs/architecture/COLLECTIONS.md`

**In Progress**

* None

**Remaining**

* Deeper cross-linking UX from collection members into conversations/workflows

**Known Risks**

* Nested folders must stay out of V1 — flat + search is the intended model

**Next Recommended Work**

* Deeper cross-linking UX from collection members into conversations/workflows

---

# Milestone 34 — Desktop Authentication End-to-End

**Overall Status:** Complete

Desktop is the primary authenticated client over the existing `/auth/*` session
cookie architecture. No JWT or alternate session mechanism was introduced.

**Completed**

* Login and registration screens (`AuthGate`) gated before the product shell
* Session restore via `GET /auth/me` on startup (`authStatus: checking`)
* Logout with confirmation (Settings → Account) and shell state cleanup
* Session-expired dialog on protected `401` responses
* Auth API client + `credentials: "include"` on fetch, SSE, and uploads
* Per-user restoration of last page and active workspace; theme remains local
* Cookie `Secure` flag follows request scheme so local HTTP desktop sessions work
* Desktop webview + API default to `127.0.0.1` for same-site session cookies
* `docs/architecture/DESKTOP_CLIENT.md` authentication / session lifecycle

**In Progress**

* None

**Remaining**

* Optional remembered-email convenience (still no password storage)

**Known Risks**

* Mixing `localhost` and `127.0.0.1` origins breaks SameSite cookie attachment
  (desktop defaults both webview and API to `127.0.0.1`)

**Next Recommended Work**

* Keep ecosystem clients on the same cookie session contracts

---

# Milestone 35 — Production Embedding Providers

**Overall Status:** Complete

Production embedding providers are implemented on the existing Search
`EmbeddingProvider` protocol and wired through the API composition root.
`FakeEmbeddingProvider` remains available only when explicitly selected.

**Completed**

* OpenAI, Ollama, and Sentence Transformers embedding adapters
* `SearchEmbeddingConfig.from_env()` + `build_embedding_provider` factory selection
* Composition-root wiring (indexing, retrieval, readiness, Intelligence)
* Startup validation and provider probe (fail fast; no silent Fake fallback)
* pgvector dimension resize to 384 (`20260808_0013`) aligned with MiniLM / OpenAI dims
* Observability: provider, model, duration, dimensions, failures
* `docs/architecture/SEARCH.md`

**In Progress**

* None

**Remaining**

* Optional live smoke jobs against hosted OpenAI / Ollama outside default CI

**Known Risks**

* Changing vector dimensions still requires migration + full re-index
* Ollama / Sentence Transformers models must match schema dimensions

**Next Recommended Work**

* Document production `.env` presets per deployment topology (cloud vs self-hosted)

---

# Milestone 36 — Typed Configuration & Startup Validation

**Overall Status:** Complete

`packages/config` (`memovi_config`) is the authoritative typed configuration
system. Environment parsing, defaults, validation, secret redaction, and
startup fail-fast checks live there. Domain `from_env()` helpers delegate to
`memovi_config` instead of calling `os.getenv` directly.

**Completed**

* Typed settings for API, database, auth, search, embeddings, models, storage,
  capabilities, connectors, observability, and desktop
* `Settings` aggregate + `load_settings()` / `validate_configuration()`
* Secret wrapping (`SecretValue`) that never appears in `str`/`repr`/errors
* API startup validation through `api.bootstrap.validate_configuration()`
* Explicit object-storage backend (`MEMOVI_OBJECT_STORAGE=minio|memory`); MinIO
  unavailability fails startup instead of silently using in-memory storage (PR #9)
* `/ready` `object_storage` component for operator/desktop diagnostics
* Migration of database, MinIO, embeddings, intelligence, capability roots, and
  readiness environment reads onto `memovi_config`
* Configuration validation tests (valid, missing required, invalid enums/URLs/numbers)
* `docs/architecture/CONFIGURATION.md` and `.env.example` updates
* V1 reasoning allow-list: `INTELLIGENCE_PROVIDER` accepts only `fake` and
  `openai`; reserved/future names and arbitrary strings fail `ConfigurationError`
  at startup. Embedding providers (`SEARCH_EMBEDDING_PROVIDER`) are unchanged.

**In Progress**

* None

**Remaining**

* Optional auth cookie/TTL env overrides wired into the auth package
* Script-only helpers (`scripts/verify_workspace_e2e.py`) may still compose
  Postgres URLs locally

**Known Risks**

* Capability root env vars now fail startup when set to missing paths (intentional)
* `INTELLIGENCE_PROVIDER=openai` without `OPENAI_API_KEY` fails full startup validation

**Next Recommended Work**

* Architecture boundary tests (Milestone 1 remaining)

---

# Milestone 37 — Durable Document Processing Queue

**Overall Status:** Complete

Document processing jobs are dispatched from durable Postgres rows instead of a
process-local in-memory queue. The Documents → Memory → Search pipeline is
unchanged; only the queue implementation and job metadata were extended.

**Completed**

* `SqlAlchemyProcessingJobQueue` with atomic claim (`FOR UPDATE SKIP LOCKED` on
  Postgres) and poll/wake semantics
* Durable columns on `documents_processing_jobs`: attempt, request/workspace IDs,
  started/completed timestamps, available/claimed leases
* Restart recovery for interrupted `extracting` / `normalizing` jobs
* Retry attempt persistence and cancelled status for superseded reprocess jobs
* Worker metrics via existing `memovi_observability` recorder
* Document API fields for attempt / started / completed timestamps
* `docs/architecture/DOCUMENT_PIPELINE.md`
* Durable queue unit tests

**In Progress**

* None

**Remaining**

* Optional dedicated background worker process (same queue contract)
* Lease renewal for very long-running extraction

**Known Risks**

* Single in-process worker remains the default runtime; multi-worker safety relies
  on claim locks
* SQLite test locks are weaker than Postgres `SKIP LOCKED`

**Next Recommended Work**

* Run `task db:migrate` locally to apply `20260808_0014`
* Architecture boundary tests

---

# Milestone 38 — Durable Capability Executions

**Overall Status:** Complete

Live capability execution state (including pending approvals) is durable in
Postgres. The Capability Execution Engine API and capability implementations are
unchanged; only the state backend moved off process-local dicts.

**Completed**

* `ExecutionStateStore` port with `InMemoryExecutionStateStore` and
  `SqlAlchemyExecutionStateStore`
* Table `automation_capability_executions` (`20260808_0015`) for results +
  pending request/auth payloads
* Engine wired to persist results, pending approvals, progress, and terminal state
* Startup recovery: interrupted `executing` → `failed` (`interrupted_by_restart`);
  `pending_approval` survives for post-restart approve
* Existing execution/list/approve/cancel APIs unchanged for desktop
* Observability metrics for duration, failures, cancellations, recovery
* `docs/architecture/CAPABILITY_EXECUTION.md` updated
* Durable approval/history/recovery tests

**In Progress**

* None

**Remaining**

* Optional lease renewal / progress heartbeats for very long terminal runs

**Known Risks**

* Mid-flight `executing` work is not auto-resumed (by design, to avoid duplicates)
* Pending approval payloads store arguments needed to resume (audit still redacts)

**Next Recommended Work**

* Run `task db:migrate` for `20260808_0014` and `20260808_0015`

---

# Milestone 39 — Durable Workflow Library & History

**Overall Status:** Complete

Workflow definitions and execution history persist in Postgres. The Workflow
Engine, Capability Planner, and Capability Execution Engine contracts are
unchanged; only library/history backends and startup recovery were added.

**Completed**

* Durable `SqlAlchemyWorkflowLibrary` + `SqlAlchemyWorkflowHistoryStore`
* Tables `automation_workflow_definitions` and `automation_workflow_history`
  (`20260808_0016`)
* Definition CRUD: create / update / delete / duplicate / list (built-ins immutable)
* Progressive execution checkpoints (`running` → terminal) with full result JSON
* Startup recovery: interrupted `running` → `failed` (no duplicate resume);
  `awaiting_approval` preserved; approved-but-unfinished instances resume
  remaining steps without resubmitting the decided capability
* Metrics: duration, success/failure/awaiting/cancelled, recovery count
* `docs/architecture/WORKFLOW_ENGINE.md` (+ updates to `WORKFLOW_AUTOMATION.md`)
* Durable library/history/recovery tests

**In Progress**

* None

**Remaining**

* Background / scheduled workflow runners

**Known Risks**

* Mid-flight `running` workflows are marked failed rather than auto-resumed
  (by design, to avoid duplicate side effects)

**Next Recommended Work**

* Run `task db:migrate` for `20260808_0016`
* Architecture boundary tests

---

# Milestone 40 — Terminal Command Policy & Sandboxing

**Overall Status:** Complete

The existing Terminal Capability is hardened for public V1 with configurable
command policies, safer process invocation, centralized config, and clearer
observability — without redesigning the capability or execution engine.

**Completed**

* Command policy: allow list, deny list, confirmation-required executables,
  denied argument patterns (evaluated before process start)
* Safer defaults for destructive/privileged names; no default allow list
  (workflow-compatible)
* Working-directory roots, timeouts, and output caps remain enforced and are
  configurable via `memovi_config`
* Prefer argv / `shell=False` when practical; `shell=True` retained for
  builtins/pipes with explicit limitations documented
* High-risk commands escalate Always Allow → Ask Every Time via
  `evaluate_submit_policy`
* Audit/logs/metrics record executable, duration, exit code, policy decision,
  approval status; secret-like command flags redacted
* `docs/architecture/TERMINAL_CAPABILITY.md` (+ CONFIGURATION / `.env.example`)
* Policy unit/engine tests

**In Progress**

* None

**Remaining**

* Optional OS-level sandboxing beyond cwd roots (future hardening)
* Desktop settings UI for editing terminal policy lists

**Known Risks**

* Allowed executables can still touch paths outside roots if the OS command can;
  combine allow lists, confirmation policy, and host controls
* `shell=True` fallback remains for compatibility (documented)

**Next Recommended Work**

* Desktop settings UI for capability / terminal policies
* Architecture boundary tests

---

# Milestone 41 — Desktop CI & Critical Path Smoke Tests

**Overall Status:** Complete

The flagship desktop client is a first-class CI citizen: automated Vite build,
critical-path smoke coverage, packaging verification, and release checklist —
without product redesign or new desktop features.

**Completed**

* Vitest + Testing Library smoke suite for the critical journey (startup →
  auth → workspace → documents/upload/status → search → conversation →
  workflow execute → settings persistence → sign-out)
* In-memory API stub (`src/test/mockBackend.ts`) for stable workflow tests
* Unit tests for session preferences and API client helpers
* GitHub Actions workflow `.github/workflows/desktop.yml` (typecheck,
  unit, mock smoke, Vite build artifact, live API smoke, Tauri packaging artifact)
* Task commands: `desktop:test`, `desktop:smoke`, `desktop:smoke:live`,
  `desktop:smoke:native`, `desktop:build`, `desktop:check`
* `docs/testing/DESKTOP_TESTING.md` (CI, layers, local run, release checklist)
* `docs/testing/NATIVE_DESKTOP_SMOKE.md` (packaged WebView cookie jar; not CI)

**In Progress**

* None

**Remaining**

* Optional OS-native window launch automation beyond the packaged auth probe
  (`task desktop:smoke:native` is local/display-only; not Linux CI)
* Multi-platform packaging matrix (macOS / Windows) in CI when release hosts
  are available

**Known Risks**

* Mock smoke stubs the API; live API smoke covers the real FastAPI path in jsdom
  and does not launch the native Tauri window
* Full Tauri packaging on Linux is slower than the Vite job; Cargo cache helps

**Next Recommended Work**

* Keep Desktop CI green on every PR into public V1
* Expand packaging matrix when shipping multi-OS installers

---

# Milestone 42 — Knowledge Indexing & Processing Experience

**Overall Status:** Complete (honest Documents-status UX in PR #8)

Desktop exposes the existing Documents processing lifecycle clearly: received,
processing, ready, or failed — without redesigning ingestion, inventing a job
API, or presenting stages the Documents status field cannot distinguish.

**Completed**

* Shared presentation map over backend statuses (`pending` → `cancelled`)
* Documents detail: StatusBadge, LoadingState while in flight, upload ProgressBar
  (real transfer percent only), failure alerts, Retry processing, Search it /
  Ask about this when `completed`
* One-shot toast on transition to `completed`: "Document ready to search."
* Conditional polling while jobs are in flight; stop on terminal status and unmount
* Activity: upload started, in-progress, completed, failed/cancelled, re-index
  requested; Processing filter; light poll while work is in flight (unchanged
  client-side synthesis)
* Search: in-flight banner and empty states when content is still processing or failed
* `docs/architecture/DOCUMENT_PIPELINE.md` user-visible lifecycle
* Unit tests for presentation helpers; DocumentsPage tests; smoke assertions

**In Progress**

* None

**Remaining**

* Optional push/SSE status updates (polling remains bounded and conditional)
* Multi-platform packaging unrelated to this milestone

**Known Risks**

* Downstream Memory / Search / embedding work after Documents `completed` is not
  a separate user-visible Documents stage; search may lag briefly after Ready

**Next Recommended Work**

* Keep processing visibility covered by Desktop smoke / release checklist
* Architecture boundary tests

---

# Milestone 43 — Workspace Members & Roles

**Overall Status:** Complete

Workspace membership management and owner-role enforcement are finished on the
existing Workspace + Authorization foundations — without redesigning either.

**Completed**

* Member APIs: list, invite (by registered email), remove, transfer ownership,
  leave
* Durable membership audit (`workspace_membership_events`)
* Role on workspace list/detail responses
* `AuthorizationService.require_workspace_owner` + owner-gated capability
  permission-mode changes
* Desktop Settings → Workspaces member list, invite, remove/transfer/leave
  confirmations; capability policies read-only for members
* `docs/architecture/WORKSPACES.md` (+ AUTHORIZATION updates)
* Workspace and authorization unit tests

**In Progress**

* None

**Remaining**

* Optional email invite tokens / out-of-band invitations (not required for V1)
* Workspace delete / rename settings (still deferred)

**Known Risks**

* Invite requires an already-registered user email
* Sole owners must transfer before leaving

**Next Recommended Work**

* Keep membership covered in Desktop release checklist
* Architecture boundary tests

---

# Milestone 44 — First Production Connector (Filesystem)

**Overall Status:** Complete

Shipped the Filesystem Connector on the existing Connector Framework so local
folders import and sync through Documents — without a second ingestion pipeline.

**Completed**

* `FilesystemConnector` with folder registration, initial/incremental sync,
  updates, deletes, and practical content-hash rename detection
* Production `DocumentImportPort` adapter (`DocumentsDocumentImportPort`) +
  `IngestConnectorDocument` (upsert/delete by connector external identity)
* Documents provenance columns: `connector_id`, `external_id`, `external_path`
* Filesystem folder persistence (`connectors_filesystem_folders`)
* Connector HTTP API (`/connectors`, filesystem folders + manual sync)
* Desktop Connectors page: add/remove folder, sync now, status, last sync,
  imported count, errors
* Desktop add-folder Browse… uses the native OS folder picker (`FilePicker`
  directory mode); manual path entry remains available
* `docs/architecture/CONNECTOR_FRAMEWORK.md` updated for filesystem lifecycle
  and future provider expectations
* Unit tests for filesystem sync and connector document ingest

**In Progress**

* None

**Remaining**

* Filesystem watchers / scheduled sync (explicitly out of scope here)
* Next provider connectors (GitHub, Google Drive, Slack, Notion)

**Known Risks**

* Rename detection is best-effort via content hash within a single sync pass

**Next Recommended Work**

* Keep filesystem manual sync covered by tests; extra providers are V2

---

# Milestone 45 — Tags & Metadata V1

**Overall Status:** Complete

Shipped first-class Tags in Memory as a complementary organization primitive to
Collections, search tag filters on the existing Search API, desktop Tags UX, and
lightweight polymorphic resource metadata.

**Completed**

* Domain: `Tag`, `TagAssignment`, `TagId`, events, repository protocol
* `TagService` with create/update/delete, assign/unassign, suggest, list-for-target,
  assignment counts, and `resolve_search_member_ids` (AND intersection across tags)
* Resource metadata V1: `ResourceMetadata` + `ResourceMetadataService` upsert API
* Persistence: `memory_tags` (`name` display + `name_key` uniqueness),
  `memory_tag_assignments`, `memory_resource_metadata` (+ Alembic `20260808_0019`)
* HTTP API `/tags` and `/resource-metadata`
* Search: repeatable `tag_id` query params; intersects with `collection_id` when both set
* Desktop Tags page (CRUD, assignments, chips, metadata editing) + Search multi-tag filter
* Unit tests for tag uniqueness, assignments, delete semantics, suggest, AND search
  resolution, and metadata upsert
* `docs/architecture/COLLECTIONS.md` updated for tag philosophy, metadata, and search

**In Progress**

* None

**Remaining**

* Automatic / AI-assisted tagging (out of scope for V1)

**Known Risks**

* Case-insensitive uniqueness relies on `name_key`; display names preserve user casing

**Next Recommended Work**

* Keep Collections and Tags complementary in UX copy; avoid nesting tags under collections

---

# Milestone 46 — Dead Architecture Cleanup

**Overall Status:** Complete

Subtractive cleanup before public V1. Removed unused packages and dead
abstractions; collapsed auth session settings onto `memovi_config.AuthSettings`.
Unwired LLM tool-calling types were left as type plumbing. Milestone 49 later
**deleted** `ToolRegistry` / `ToolExecutor` (they are not frozen V1 architecture).

**Completed**

* Deleted `packages/models` and `packages/contracts` (and build/CI path refs)
* Deleted `EchoTool`, `PlaceholderReasoningProvider`, `PlaceholderKnowledgeRetriever`,
  `StreamingReasoningProvider`
* Deleted unused connector, auth, and memory event types that were never published
* Auth session cookie name/TTL now read from typed `AuthSettings` (single source)
* Left `ToolCall` / `ToolResult` on `ReasoningResult` as unused plumbing (not a
  live tool path). Registry/executor deletion is Milestone 49.
* Documentation updated to match implementation (`STATUS`, `ROADMAP`,
  `ARCHITECTURE`, `README`, related architecture notes)

**In Progress**

* None

**Remaining**

* None for this milestone

**Known Risks**

* None — no intentional runtime behavior changes

**Next Recommended Work**

* Continue Phase 1 V1 platform completion without reintroducing unused packages

---

# Milestone 47 — V1 Cleanup Sprint PR #1

**Overall Status:** Complete

Subtractive dead-architecture cleanup with no runtime behavior changes. Removed
empty leftover package trees and auth/intelligence scaffold packages that had no
imports; reconciled documentation drift left after Milestone 46.

**Completed**

* Deleted empty `packages/documents/src/memovi_documents/` twin tree
* Deleted empty leftover `apps/api/app/` layout
* Deleted empty untracked `events/` dirs under memory and search package roots
* Deleted empty auth `domain/services`, `application/services`, and
  `infrastructure/providers` scaffolds (no imports)
* Deleted empty `memovi_intelligence/events` package (no imports)
* Updated auth layer READMEs to match implemented routers, use cases, and adapters
* Corrected `ENGINEERING_SNAPSHOT.md` references to deleted placeholders (`EchoTool`,
  `Placeholder*`), middleware/config validation status, and Redis reserved usage
* Clarified README / local-infrastructure Redis wording (Compose-reserved, unused by app)
* Removed deprecated `GET /search/semantic` and the `SemanticSearch` adapter
  (PR #11); semantic retrieval remains `GET /search?mode=semantic`

**In Progress**

* None

**Remaining**

* None

**Known Risks**

* None — no intentional runtime behavior changes

**Next Recommended Work**

* Continue Phase 1 V1 platform completion without reintroducing unused packages

---

# Milestone 48 — V1 Cleanup Sprint PR #12

**Overall Status:** Complete

Removed unused Redis Compose infrastructure. Audit confirmed no application
client, package dependency, tests, CI service, or subsystem used Redis. Local
stack is PostgreSQL and MinIO only. No application behavior change.

**Completed**

* Deleted Compose `redis` service, healthcheck, ports, env, and `memovi_redis_data`
* Removed `REDIS_PASSWORD` and `REDIS_PORT` from `.env.example`
* Removed Dev Container port `6379` forwarding and Redis label
* Reconciled V1 docs so Redis is not described as a current dependency
* Labeled distributed queues / Redis Streams as future architectural options

**In Progress**

* None

**Remaining**

* None

**Known Risks**

* None — no intentional runtime behavior changes

**Next Recommended Work**

* Continue Phase 1 V1 platform completion without reintroducing unused infrastructure

---

# Milestone 49 — V1 Cleanup Sprint PR #13

**Overall Status:** Complete

Deleted the unused Intelligence `ToolRegistry` / `ToolExecutor` stack. Host
actions continue to run through Capabilities (registry, planner, execution
engine, approval / policy, workflows, connectors). `ModelGateway` / Reason /
`ReasoningResult` were not changed. `ToolCall` / `ToolResult` remain only as
unused fields on `ReasoningResult`.

**Completed**

* Deleted `ToolRegistry`, `ToolExecutor`, `Tool` protocol, `ToolDefinition`,
  `ToolParameter`, empty `infrastructure/tools`, and isolated tool-framework tests
* Removed executor-only exceptions (`UnknownToolError`, `InvalidToolArgumentsError`,
  `ToolExecutionError`, `ToolTimeoutError`); kept `InvalidToolError` for
  `ToolCall` / `ToolResult`
* Documentation now describes Capabilities as the V1 host-execution architecture,
  not a replacement tool registry; LLM tool calling is not claimed

**In Progress**

* None

**Remaining**

* Optional later removal of unused `ReasoningResult.tool_calls` / `tool_results`
  (requires touching `ReasoningResult`, `ModelGateway`, and `Reason`)

**Known Risks**

* None — no intentional runtime behavior changes

**Next Recommended Work**

* Continue Phase 1 V1 platform completion; do not reintroduce an Intelligence
  tool-execution stack

---

# Milestone 50 — V1 Cleanup Sprint PR #14

**Overall Status:** Complete

Added one live desktop critical-path smoke test: the existing React shell
against a real FastAPI process (Postgres, MinIO, in-process worker, search,
fake reasoning/embeddings). Mock Vitest smoke remains the fast PR gate. Native
Tauri window automation was not introduced.

**Completed**

* `apps/desktop/src/smoke/liveCriticalPath.smoke.test.tsx` (gated on `MEMOVI_LIVE_API=1`)
* Test-only jsdom cookie bridge for HttpOnly session cookies
* Dedicated GitHub Actions job `desktop-live-smoke`
* `task desktop:smoke:live` / `pnpm test:smoke:live`
* `docs/testing/DESKTOP_TESTING.md` layer split (unit, mock smoke, live API,
  packaging, manual native verification)

**In Progress**

* None

**Remaining**

* Optional OS-native window launch automation beyond the packaged auth probe
  (`task desktop:smoke:native` is local/display-only; not Linux CI)
* Multi-platform packaging matrix (macOS / Windows) in CI when release hosts
  are available

**Known Risks**

* Live smoke depends on Docker (Postgres + MinIO) and API readiness in CI
* Documents **Ready** is processing completion; the test retries search until
  the unique phrase is indexed

**Next Recommended Work**

* Keep mock smoke fast; keep live smoke on the real MinIO path; do not add a
  browser E2E framework for V1

---

# Phase 3 — Capability Framework

**Overall Status:** Complete for V1 (filesystem, terminal, git, browser + engine)

Clipboard, notifications, and a plugin SDK are **V2**. Desktop policy settings
UI is a V1 operator follow-up.

**Completed**

* `packages/automation` Capability Framework foundation
* Core contracts: `Capability`, `CapabilityRegistry`, `CapabilityInvoker`, `CapabilityMetadata`, `CapabilityPermission`, `CapabilityRequest`, `CapabilityResult`, `CapabilityContext`, `CapabilityExecutionPolicy`
* Capability Execution Engine with permission modes, approval states, and audit trail
* Composition-root filesystem registration and Intelligence execution port adapter
* Desktop approval / progress presentation for capability executions
* Unit and integration tests for registry, permissions, execution, cancellation, timeouts, and error contracts
* Smoke tests for MockFilesystem / MockTerminal registration, invocation, unknown-capability structured errors, and deterministic re-composition
* `FilesystemCapability` (`filesystem`) with root-scoped path safety, structured errors, and read/write permission enforcement
* Filesystem write operations with overwrite/trash policies and fine-grained create/modify/move/delete permissions
* Filesystem smoke and write tests: register, read/write, traversal rejection, permission and audit coverage
* `TerminalCapability` (`terminal`) with root-scoped cwd safety, timeouts, output caps, cancellation, and process termination
* Terminal command policy / sandboxing (allow/deny/confirm, argv preference) — Milestone 40
* Terminal unit/engine/smoke tests: execute, cwd, env, timeout, cancel, audit redaction, engine-only production path
* `GitCapability` (`git`) with structured status/branch/commit/diff/remote ops and `git.read` / `git.write` / `git.network`
* Git unit/engine/acceptance tests: structured results, permission tiers, approval, audit, engine-only path
* `BrowserCapability` (`browser`) with open/read/search/download and `browser.read` / `browser.search` / `browser.download`
* Browser unit/engine/acceptance/smoke tests: structured results, URL safety, download filesystem integration, audit redaction
* Architecture references: `docs/architecture/CAPABILITY_FRAMEWORK.md`, `docs/architecture/CAPABILITY_EXECUTION.md`, `docs/architecture/FILESYSTEM_CAPABILITY.md`, `docs/architecture/FILESYSTEM_WRITE.md`, `docs/architecture/TERMINAL_CAPABILITY.md`, `docs/architecture/GIT_CAPABILITY.md`, `docs/architecture/BROWSER_CAPABILITY.md`

**In Progress**

* None

**Remaining (V2 unless noted)**

* Concrete capabilities: Clipboard, Notifications (V2)
* Plugin system / loading (V2)
* Desktop settings UI for capability permission policies (V1 operator follow-up)

Durable execution state and SQLAlchemy audit store exist; do not list “durable
audit persistence” as missing architecture.

**Known Risks**

* Hosts that grant filesystem, terminal, git, or browser download roots over overly broad directories expand the trusted surface
* Shell/Git write, network, and browser download ops remain powerful; Ask Every Time should stay the default

**Next Recommended Work**

* Optional: capability policy settings UI during operator-UX polish
* Do not add Clipboard/Notifications/plugins as V1 blockers

---

# Phase 4 — Automation

**Overall Status:** Complete for V1 sequential workflows (approval/resume shipped)

Background schedules, conditionals/loops, and a plugin marketplace are **V2**.

**Completed**

* Capability Execution Engine safe execution + Ask Every Time approval path
* Capability Planner (deterministic plan/validate; execute via engine only)
* Plan contracts and Intelligence/conversation bridge for create + execute plan
* Workflow Automation Framework (reusable sequential workflows over planner + engine)
* Desktop Workflows library / run / progress / history surface
* Durable workflow library and history (`WORKFLOW_ENGINE.md`, Milestone 39)

**In Progress**

* None

**Remaining (V2 / operator follow-up)**

* Durable approval/settings UX depth (engine approval already ships)
* Background jobs / scheduled workflows (V2)
* Conditional/loop/parallel workflow features (V2)

**Known Risks**

* Automation without approval and provenance undermines trust

**Next Recommended Work**

* Background / scheduled workflow runners — still not a parallel agent stack

---

# Phase 5 — Knowledge Evolution

**Overall Status:** Not started (**V2 / future**)

**Completed**

* None

**In Progress**

* None

**Remaining**

* Summaries
* Long-term memory
* Knowledge graph
* Reasoning cache
* Inference-efficient retrieval

**Known Risks**

* Without this layer, AI and embedding spend will grow with corpus size

**Next Recommended Work**

* Begin after V1 platform and desktop product contracts are stable

---

# Phase 6 — Ecosystem

**Overall Status:** Not started (**V2 / future**; optional web shell exists only)

**Completed**

* None

**In Progress**

* None

**Remaining**

* Optional web client
* Optional mobile client
* Cloud sync
* Enterprise deployment
* Connector marketplace

**Known Risks**

* Treating web or mobile as primary would conflict with the desktop-first vision

**Next Recommended Work**

* Keep ecosystem clients optional and API-backed

---

# How To Update This Document

When implementation changes:

1. Move items between Completed / In Progress / Remaining
2. Refresh Overall Status and the short summary
3. Update Known Risks and Next Recommended Work
4. Keep [`ROADMAP.md`](ROADMAP.md) / [`ROADMAP_V2.md`](ROADMAP_V2.md) focused on direction, not progress
5. Keep Milestones 0–6 as historical platform foundation; the **Current V1**
   snapshot at the top is the source of “what is unfinished for V1.”
