# Memovi Status

Living implementation tracker for Memovi as a desktop-first knowledge operating
system on a reusable backend platform. Last reviewed: 2026-08-07 (Milestone 33).

* [`ROADMAP.md`](ROADMAP.md) / [`ROADMAP_V2.md`](ROADMAP_V2.md) describe where Memovi is going.
* [`STATUS.md`](STATUS.md) describes where Memovi is today.

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

**Overall Status:** In progress

Backend composition root is operational. Observability foundation (request context, structured logs, diagnostic bridge, metrics, readiness) is in place. Typed config and architecture boundary tests remain.

**Completed**

* FastAPI composition root and bootstrap
* Dependency injection and router registration
* Health liveness (`/health`) and readiness (`/ready`) endpoints
* Domain packages for auth, documents, search, and intelligence
* `memovi_observability` RequestContext, structured JSON logging, diagnostic event bridge, metrics recorder, and OpenTelemetry-API spans

**In Progress**

* Domain package scaffolding for remaining packages
* Environment-based configuration (typed `memovi_config` not yet wired)

**Remaining**

* Architecture tests validating package boundaries
* Typed configuration wiring

**Known Risks**

* Cross-cutting concerns may stay ad hoc without typed config

**Next Recommended Work**

* Wire typed configuration and add architecture boundary tests

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

* Richer membership roles beyond owner/member
* Broader ownership audit beyond capability execution audits

**Known Risks**

* None specific — desktop now authenticates end-to-end via session cookies

**Next Recommended Work**

* Continue platform hardening (API stability, typed config)

---

# Milestone 3 — Knowledge Ingestion

**Overall Status:** In progress

Upload-to-processing pipeline is operational locally. OCR remains open. The
Connector Framework foundation (Milestone 32) now provides registration, sync
contracts, and Documents handoff without concrete provider adapters yet.

**Completed**

* Document uploads (`POST /documents`)
* MinIO-backed object storage
* Document processing engine for PDF, Markdown, and plain text
* Processing queue and background worker
* Chunk generation via Memory materialization on `ProcessingCompleted`
* Event-driven handoff into Memory
* Connector Framework foundation (`memovi-connectors`: registry, sync, normalize,
  health, scheduler foundation, `DocumentImportPort`)

**In Progress**

* Local file intake (upload path exists; provider connectors not yet implemented)
* Metadata extraction beyond ingest/process basics
* Document versioning (initial version on upload; no re-version workflow)

**Remaining**

* OCR pipeline
* Concrete connector providers (GitHub, Drive, Slack, …)

**Known Risks**

* Unsupported formats and OCR gaps limit ingestion coverage

**Next Recommended Work**

* Implement the first concrete connector on the framework (e.g. filesystem or GitHub)
* Harden processing status visibility and expand supported ingest formats as needed

---

# Milestone 4 — Knowledge Platform

**Overall Status:** In progress

Memory materialization, chunk persistence, explorer APIs, and Collections
organization work. Tags and deeper metadata management remain.

**Completed**

* Memory domain core for chunk materialization and persistence from processing events
* Knowledge Collections organization (Milestone 33): create/rename/delete, memberships,
  summaries, search filter, desktop management

**In Progress**

* Memory domain ownership of knowledge items (HTTP `/memory` read surface exposed for explorer)
* Processing status as a knowledge concern (job statuses exist in documents; no public Memory status API)
* Knowledge independence from AI providers (memory/search do not depend on Intelligence; tags incomplete)

**Remaining**

* Tags
* Version history
* Knowledge relationships beyond provenance edges
* Metadata management as a first-class platform concern

**Known Risks**

* Knowledge organization may lag behind ingestion and search capability without tags

**Next Recommended Work**

* Add semantic entity/topic extraction while keeping explorer contracts stable
* Introduce Tags without coupling them to Collections hierarchies

---

# Milestone 5 — Retrieval Intelligence

**Overall Status:** In progress

Keyword, semantic, and hybrid retrieval are operational. Query planning, caching, summaries, and deeper ranking remain.

**Completed**

* Full-text / keyword retrieval
* Vector / semantic retrieval (pgvector)
* Hybrid retrieval with Reciprocal Rank Fusion
* Metadata filtering
* Stable search APIs (`GET /search`)

**In Progress**

* Semantic ranking (score normalization + RRF; no learned reranker)

**Remaining**

* Query planning and context budgeting
* Cache and summary lookup paths

**Known Risks**

* Without planning/cache/summary paths, retrieval remains search-centric rather than cost-aware

**Next Recommended Work**

* Add query planning, context budgeting, and cheaper lookup paths before deeper ranking

---

# Milestone 6 — Reasoning Engine

**Overall Status:** In progress

Reasoning pipeline, conversation memory, Conversation REST API (including list,
rename, delete, and SSE streaming), and Search-backed retrieval for conversations
are operational. AI summaries remain.

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

* Provider abstraction and routing (env-driven selection; broader providers reserved)
* Prompt construction (`PromptBuilder`; no prompt library/versioning product)
* Tool execution framework (`ToolRegistry` / `ToolExecutor` / `EchoTool`; not in conversation Reason path)
* Cost-aware model selection (basic provider/model config only)

**Remaining**

* AI summaries
* WebSocket/realtime channels beyond SSE (only if needed)

**Known Risks**

* Tool framework is not yet part of the conversation path

**Next Recommended Work**

* Close Phase 1 platform gaps (ownership, observability, API stability)
* Migrate Intelligence `ModelGateway` onto `packages/models` (`ModelRegistry` / `ModelProvider`)

---

# Milestone 17 — Model Provider Framework

**Overall Status:** Complete (architecture foundation)

**Completed**

* `packages/models` (`memovi-models`) Model Provider Framework
* Core contracts: `ModelProvider`, `ModelRegistry`, `ModelRequest`, `ModelResponse`, `ModelMetadata`, `ModelCapabilities`, `ProviderConfiguration`, `ProviderHealth`
* Normalized provider error codes (authentication, unavailable, rate_limit, timeout, unsupported_capability, invalid_configuration, …)
* `FakeModelProvider` for tests and local wiring (no production vendor SDKs)
* Architecture reference: `docs/architecture/MODEL_PROVIDER_FRAMEWORK.md`

**In Progress**

* None

**Remaining**

* Concrete adapters: OpenAI, Anthropic, Gemini, Ollama, OpenRouter, LM Studio
* Intelligence migration from in-package `ReasoningProvider` / `ModelGateway` onto `memovi-models`
* Optional Search embeddings convergence onto shared capability model
* Desktop provider settings UI (consumes configuration; not owned here)

**Known Risks**

* Until Intelligence migrates, vendor SDK dependencies remain in `memovi-intelligence`

**Next Recommended Work**

* Implement the first production adapter (OpenAI or Ollama) behind `ModelProvider`, then adapt Intelligence `ModelGateway` to resolve through `ModelRegistry`

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

* Durable audit persistence, additional concrete capabilities, settings UI for policies

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

* Durable audit persistence (shared with Milestone 21)
* Desktop settings UI for capability permission policies
* Autonomous workflows and background scheduling (explicitly out of scope)

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

* Durable audit persistence (shared with Milestones 21–22)
* Desktop settings UI for capability permission policies
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

* Durable audit persistence (shared with Milestones 21–23)
* Desktop settings UI for capability permission policies
* Richer dedicated Git product page beyond Chat capability panel

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

* Durable audit persistence (shared with Milestones 21–24)
* Desktop settings UI for capability permission policies
* Richer dedicated Browser product surface beyond Chat capability panel

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
* Resume remaining steps after Ask Every Time approval within one instance
* Durable cross-process workflow history

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

* Broader non-capability ownership audit logging
* Richer role-based authorization beyond membership + capability policy modes

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

**Overall Status:** In progress

Documents, Memory, Search, and Intelligence vertical slices exist. Workspace
ownership is enforced on those paths. Observability, production hardening, and
API stability remain.

**Completed**

* Core Documents → Memory → Search → Intelligence pipeline paths
* Conversation API with Search-backed retrieval and durable storage
* Workspace ownership boundary with repository and search isolation

**In Progress**

* Typed config and platform package/contract hardening
* API stability for clients

**Remaining**

* Documents / Memory / Search / Intelligence production readiness
* Production hardening beyond capability authorization
* API stability for clients

**Completed (Phase 1 platform)**

* Observability foundation: request context propagation, structured logs, diagnostic event bridge, metrics interface, OTel-neutral spans, `/ready` checks

**Known Risks**

* Building the desktop client before API stability lands creates rework

**Next Recommended Work**

* Finish API stability and typed config before Phase 2

---

# Phase 2 — Desktop Client

**Overall Status:** In progress

The flagship Tauri desktop shell lives in `apps/desktop`. It launches, probes
backend health/readiness, and exposes working product pages over the platform
APIs. Milestone 31 established the official design system so new screens compose
shared UI primitives.

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
* Design system: tokens (light/dark), reusable `components/ui/` library, UX
  standards for loading/empty/error/confirm/toast, and
  `docs/design/DESIGN_SYSTEM.md`
* `docs/architecture/DESKTOP_CLIENT.md`
* `docs/architecture/KNOWLEDGE_EXPLORER.md`
* `docs/architecture/COLLECTIONS.md`
* End-to-end desktop authentication (login/register/logout, session restore,
  expiry handling) over existing `/auth/*` session cookies (Milestone 34)

**In Progress**

* Continuing to deepen page consistency on top of the design system

**Remaining**

* Model management product depth beyond Settings selectors
* Workspace management product depth beyond Settings
* Indexing status surface

**Known Risks**

* Building rich client pages before Phase 1 contracts stabilize creates rework
* Desktop requires Rust and host linker tooling beyond Node/Python setup

**Next Recommended Work**

* Assemble new desktop surfaces exclusively from design-system primitives
* Expand Documents ingestion UX and deepen semantic entity/concept extraction behind explorer labels

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
contract. No concrete provider adapters or scheduled sync runners yet.

**Completed**

* `memovi-connectors` core types: `Connector`, `ConnectorRegistry`,
  `ConnectorConfiguration`, `ConnectorExecutionContext`, `ConnectorResult`,
  `ConnectorMetadata`, `ConnectorHealth`, `ConnectorScheduler` foundation
* `AuthCredentialRef` credential isolation (env/secret refs, no embedded secrets)
* `NormalizedSourceMetadata` / `NormalizedImportItem` + `DocumentImportPort`
* Domain events: `ConnectorAuthorized`, `ConnectorSynchronized`, `ImportCompleted`
* `FakeConnector` + unit tests
* Composition-root wiring (`configure_connector_framework`)
* `docs/architecture/CONNECTOR_FRAMEWORK.md`

**In Progress**

* None

**Remaining**

* Concrete provider connectors
* Production `DocumentImportPort` adapter over Documents ingest
* Scheduled synchronization runner

**Known Risks**

* Provider work must keep feeding Documents — never invent parallel stores

**Next Recommended Work**

* Ship the first real connector (filesystem or GitHub) on this framework

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

* Tags (separate from Collections)
* Deeper cross-linking UX from collection members into conversations/workflows

**Known Risks**

* Nested folders must stay out of V1 — flat + search is the intended model

**Next Recommended Work**

* Add Tags as a complementary organization primitive

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

# Phase 3 — Capability Framework

**Overall Status:** In progress

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
* Terminal unit/engine/smoke tests: execute, cwd, env, timeout, cancel, audit redaction, engine-only production path
* `GitCapability` (`git`) with structured status/branch/commit/diff/remote ops and `git.read` / `git.write` / `git.network`
* Git unit/engine/acceptance tests: structured results, permission tiers, approval, audit, engine-only path
* `BrowserCapability` (`browser`) with open/read/search/download and `browser.read` / `browser.search` / `browser.download`
* Browser unit/engine/acceptance/smoke tests: structured results, URL safety, download filesystem integration, audit redaction
* Architecture references: `docs/architecture/CAPABILITY_FRAMEWORK.md`, `docs/architecture/CAPABILITY_EXECUTION.md`, `docs/architecture/FILESYSTEM_CAPABILITY.md`, `docs/architecture/FILESYSTEM_WRITE.md`, `docs/architecture/TERMINAL_CAPABILITY.md`, `docs/architecture/GIT_CAPABILITY.md`, `docs/architecture/BROWSER_CAPABILITY.md`

**In Progress**

* None

**Remaining**

* Concrete capabilities: Clipboard, Notifications
* Desktop settings UI for capability permission policies
* Plugin system / loading
* Durable audit persistence

**Known Risks**

* Hosts that grant filesystem, terminal, git, or browser download roots over overly broad directories expand the trusted surface
* Shell/Git write, network, and browser download ops remain powerful; Ask Every Time should stay the default

**Next Recommended Work**

* Add the next concrete capability (Clipboard or Notifications) and durable audit storage

---

# Phase 4 — Automation

**Overall Status:** In progress

**Completed**

* Capability Execution Engine safe execution + Ask Every Time approval path
* Capability Planner (deterministic plan/validate; execute via engine only)
* Plan contracts and Intelligence/conversation bridge for create + execute plan
* Workflow Automation Framework (reusable sequential workflows over planner + engine)
* Desktop Workflows library / run / progress / history surface

**In Progress**

* None

**Remaining**

* Durable approval/settings UX
* Background jobs / scheduled workflows
* Conditional/loop/parallel workflow features
* Resume-after-approval for multi-step workflow instances

**Known Risks**

* Automation without approval and provenance undermines trust

**Next Recommended Work**

* Add durable workflow/plan history and background runners — still not a parallel agent stack

---

# Phase 5 — Knowledge Evolution

**Overall Status:** Not started

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

**Overall Status:** Not started

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
5. Keep Milestones 0–6 as the platform foundation; use Phases 1–6 for forward work
