# Memovi

> Your knowledge, organized. AI that remembers what matters.

Memovi is an AI-powered knowledge platform that continuously ingests information from multiple sources, transforms it into structured knowledge, and makes it searchable through semantic retrieval and intelligent assistants.

Rather than acting as another chatbot, Memovi serves as a personal knowledge infrastructure capable of connecting documents, conversations, notes, code, and external services into a unified memory system.

---

## Vision

The long-term vision of Memovi is to become an extensible knowledge platform rather than a single AI application.

```
               External Sources
      ┌─────────────────────────────────┐
      │ GitHub • Gmail • Slack • Drive │
      │ Notion • Obsidian • Files      │
      └─────────────────────────────────┘
                     │
                     ▼
              Connector Framework
                     │
                     ▼
             Document Processing
      OCR → Chunking → Metadata → Events
                     │
                     ▼
          Knowledge & Memory Platform
                     │
      PostgreSQL • pgvector • Redis
                     │
                     ▼
         Retrieval & AI Runtime Layer
                     │
                     ▼
      Web • Desktop • Mobile • API
```

Every feature in Memovi is designed to build upon this pipeline instead of existing as an isolated component.

---

# Goals

- Build a production-quality AI platform
- Demonstrate modern backend architecture
- Support multiple AI providers
- Enable scalable document ingestion
- Create an extensible connector ecosystem
- Remain self-hostable
- Follow clean architecture and DDD principles

---

# Core Principles

## Modular Monolith

Memovi begins as a modular monolith.

Each domain owns:

- API
- Business Logic
- Database Models
- Events
- Tests

Modules can later be extracted into independent services without major rewrites.

---

## Domain Driven Design

Source code is organized around business domains instead of technical layers.

Example:

```
memory/

    application/

    domain/

    infrastructure/

    api/
```

Business rules remain isolated from infrastructure concerns.

---

## Event-Driven Processing

Long-running operations are asynchronous.

Example:

```
Document Uploaded
        │
        ▼
Embedding Worker
        │
        ▼
Embeddings Created
        │
        ▼
Summary Worker
        │
        ▼
Memory Updated
```

This architecture allows features to evolve independently.

---

# Planned Features

## Knowledge Management

- Documents
- Notes
- Conversations
- Semantic Search
- Version History
- Collections
- Tags

---

## AI

- Chat with your knowledge
- Retrieval Augmented Generation
- AI Summaries
- Prompt Templates
- Multiple LLM Providers
- Agent Runtime (future)

---

## Connectors

- Local Files
- GitHub
- Google Drive
- Gmail
- Slack
- Discord
- Notion
- Obsidian
- Confluence
- Jira

---

## Search

- Full Text Search
- Vector Search
- Hybrid Search
- Metadata Filtering
- Semantic Ranking

---

## Authentication

- Email
- OAuth
- API Keys
- RBAC

---

# Architecture

```
Internet
    │
Traefik
    │
Next.js
    │
FastAPI
    │
──────────────────────────────────

Auth

Memory

Search

Documents

Connectors

AI

──────────────────────────────────
        Domain Events
──────────────────────────────────

Workers

OCR

Chunking

Embeddings

Summaries

──────────────────────────────────

PostgreSQL + pgvector

Redis

MinIO
```

---

# Repository Structure

```
apps/

    web/

    api/

packages/

    core/

    events/

    database/

    config/

    logging/

    connectors/

    ai/

    shared/

docs/

    architecture/

    decisions/

    api/

    diagrams/
```

---

# Technology Stack

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- TanStack Query

## Backend

- FastAPI
- SQLAlchemy
- Pydantic
- Alembic

## Infrastructure

- PostgreSQL
- pgvector
- Redis
- MinIO
- Docker

## AI

- Ollama
- OpenAI
- Anthropic
- Sentence Transformers

## Observability

- OpenTelemetry
- Prometheus
- Grafana
- Loki

---

# Roadmap

## Phase 1

- Authentication
- Document Upload
- Vector Search
- AI Chat
- Local Files

---

## Phase 2

- Connectors
- Event Processing
- OCR
- Summaries
- Collections

---

## Phase 3

- Agent Runtime
- Browser Extension
- Desktop Client
- Mobile Support

---

## Phase 4

- Knowledge Graph
- Temporal Memory
- Plugin Marketplace
- Multi-user Workspaces

---

# Design Philosophy

Memovi is designed as a platform instead of a single application.

Every feature should contribute to a shared knowledge pipeline:

```
Connect

↓

Normalize

↓

Store

↓

Index

↓

Retrieve

↓

Reason

↓

Learn
```

If a new feature does not strengthen this pipeline, it likely belongs outside the core platform.

---

# Status

🚧 Early Development

The project is currently focused on building the core platform and architecture before expanding into advanced AI capabilities.