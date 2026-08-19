# Smart Academic AI - System Architecture Document

## 1. System Overview

**Smart Academic AI** is a production-grade multi-tenant academic intelligence and personalized learning platform. It empowers educational institutions by combining academic document intelligence, Retrieval-Augmented Generation (RAG), deterministic analytics, hybrid AI rule engines, and automated assessment and intervention workflows.

### Core Value Proposition
- **Multi-Tenant Isolation**: Strict logical data separation per educational institution derived from JWT token context (`TenantContext`).
- **Academic Document Intelligence**: Seamless ingestion, chunking, vector indexing, and citation-backed RAG over course materials.
- **Hybrid Evaluation Engine**: Deterministic scoring and topic mapping coupled with LLM-powered feedback and personalized practice quiz generation.
- **Async Job Architecture**: Heavy operations (document ingestion, PDF parsing, bulk grading, embedding generation, practice quiz generation) execute off the API thread using Redis and Celery.
- **AI Observability & RAG Quality**: Built-in tracking of token usage, latencies, estimated API costs, and automated evaluation metrics (Hit Rate, Citation Accuracy, Groundedness).

---

## 2. High-Level Architecture Diagram

```mermaid
graph TD
    subgraph Client Layer
        A[Student Web App / Next.js]
        B[Teacher Web App / Next.js]
        C[Admin Portal / Next.js]
    end

    subgraph Gateway & Security Layer
        NGINX[Nginx Reverse Proxy / SSL / Rate Limiting]
        AUTH[FastAPI Auth Guard / JWT + Tenant Enforcer]
    end

    subgraph Application Server Layer / FastAPI
        API_AUTH[Auth & User Module]
        API_INST[Institution, Course & Class Module]
        API_DOC[Document Ingestion API]
        API_RAG[RAG & Query API]
        API_ASSESS[Assessment & Rule Engine API]
        API_ANALYTICS[Analytics & Learning Gaps API]
        API_OBS[AI Observability & RAG Eval API]
    end

    subgraph Async Worker Layer / Celery + Redis
        REDIS[(Redis Broker & Cache)]
        CELERY_DOC[Celery Worker: Doc Processing & Embeddings]
        CELERY_EVAL[Celery Worker: Async Assessment Grading]
        CELERY_QUIZ[Celery Worker: AI Practice Quiz Gen]
    end

    subgraph Data & Vector Storage Layer
        PG[(PostgreSQL 16 + pgvector)]
        STORAGE[S3 / Local Object Storage - Documents & PDFs]
    end

    subgraph AI Provider Abstraction Layer
        AI_FACTORY[AI Provider Factory]
        GEMINI[Google Gemini API Adapter]
        OPENAI[OpenAI / Anthropic Fallback Adapter]
        EMBED_PROV[Embedding Provider / text-embedding-004]
    end

    %% Flow Connections
    A & B & C --> NGINX
    NGINX --> AUTH
    AUTH --> API_AUTH & API_INST & API_DOC & API_RAG & API_ASSESS & API_ANALYTICS & API_OBS

    API_DOC --> STORAGE
    API_DOC --> REDIS
    API_ASSESS --> REDIS

    REDIS --> CELERY_DOC & CELERY_EVAL & CELERY_QUIZ

    CELERY_DOC --> STORAGE
    CELERY_DOC --> EMBED_PROV
    CELERY_DOC --> PG

    API_RAG --> EMBED_PROV
    API_RAG --> PG
    API_RAG --> AI_FACTORY

    CELERY_EVAL --> PG
    CELERY_EVAL --> AI_FACTORY

    AI_FACTORY --> GEMINI
    AI_FACTORY --> OPENAI
```

---

## 3. Component Details

### 3.1 Frontend (Next.js 14+ App Router)
- **Framework**: Next.js (TypeScript, React 18/19, App Router architecture).
- **Styling & UI**: Tailwind CSS, `shadcn/ui` accessible component library, Lucide icons.
- **Charts & Visualizations**: `Recharts` for student performance trends, learning gap heatmaps, and topic mastery distribution.
- **State Management & Data Fetching**: TanStack Query (React Query) for server state caching, optimistic updates, and automatic refetching; Zustand for client-side workspace state.

### 3.2 Backend (FastAPI + Python 3.11+)
- **API Framework**: FastAPI for async HTTP endpoints, high throughput, and automatic OpenAPI schema generation.
- **ORM & Database Drivers**: SQLAlchemy 2.0 (asyncio with `asyncpg`), Pydantic v2 for strict data validation and serialization.
- **Database Migrations**: Alembic.
- **Multi-Tenancy Enforcer**: Middleware & Dependency Injection asserting valid `tenant_id` derived exclusively from JWT token context on all database operations.

### 3.3 Database (PostgreSQL + pgvector)
- **Relational Storage**: Core tables for Users, Roles, Institutions, Courses, Classes, Assessments, Submissions, Questions, Analytics, AI Request Logs, and RAG Evaluations.
- **Vector Search Engine**: `pgvector` extension for storing 768-dim vector embeddings.
- **Vector Indexing**: HNSW (Hierarchical Navigable Small World) index for fast approximate nearest-neighbor search filtered by `institution_id` and `course_id`.

### 3.4 Async Task Pipeline (Redis + Celery)
- **Message Broker & Cache**: Redis 7+.
- **Task Execution**: Celery workers handling:
  - Document extraction (PDF, DOCX, TXT via PyPDF / pdfplumber / python-docx).
  - Text chunking (recursive character splitting with overlap).
  - Batch embedding generation.
  - Asynchronous AI practice quiz generation and gap analysis computing.

### 3.5 AI & RAG Abstraction Layer
- **LLM Interface**: Abstract Base Class (`BaseLLMProvider`) with methods `generate()`, `generate_structured()`, returning standard `LLMResponse` containing token usage metrics. Concrete adapter: `GeminiLLMProvider`.
- **Embedding Interface**: Abstract Base Class (`BaseEmbeddingProvider`) with `embed_text()` and `embed_batch()`. Concrete adapter: `GeminiEmbeddingProvider` (`text-embedding-004`).
- **Hybrid Retrieval**: Dense vector similarity search (`pgvector`) + PostgreSQL Full-Text Search (`tsvector`/`tsquery` with `ts_rank_cd`) combined via Reciprocal Rank Fusion (RRF).

---

## 4. Multi-Tenant Architecture & Isolation Model

Smart Academic AI enforces strict **Logical Tenant Isolation** via a shared database, single schema design with discriminator columns (`institution_id`).

### Isolation Enforcement Guarantees:
1. **JWT Auth Token Context**: Token payload embeds `institution_id`, `user_id`, and `role`. Client-supplied `institution_id` in HTTP params or body is NEVER trusted.
2. **FastAPI Context Dependency**: Every protected route receives `TenantContext` extracted from token.
3. **Repository/Query Wrapper**: All database query filters append `.where(Model.institution_id == tenant_context.institution_id)`.
4. **Vector Search Filtering**: Vector similarity SQL queries explicitly include `WHERE institution_id = :tenant_id AND course_id = :course_id`.
5. **Object Storage Isolation**: Document assets are stored under structured paths: `storage/{tenant_id}/{course_id}/{document_id}/{filename}` using secure UUID filenames.
