# Smart Academic AI - Developer Guidelines & Coding Rules

## 1. Core Engineering Commandments

1. **NO FAKE OR HARDCODED AI**: AI features must call real LLM/Embedding providers via abstraction wrappers (`BaseLLMProvider`, `BaseEmbeddingProvider`). Mocking is strictly permitted in automated test suites only.
2. **NO HARDCODED SECRETS**: No API keys, database credentials, or JWT secrets in source code or git commits. Use `.env` with strict validation via Pydantic (`Settings` class).
3. **STRICT MULTI-TENANCY**: Never write a SQLAlchemy query or raw SQL without explicitly appending `.where(Model.institution_id == tenant_context.institution_id)`.
4. **NO DETERMINISTIC AI**: Do not use LLMs to sum scores, count correct answers, or perform basic math. Use deterministic Python/SQL code for arithmetic and rule calculations.
5. **CITE SOURCES**: Every RAG endpoint response must return verifiable context citations (document title, page number, similarity score).

---

## 2. Backend Coding Standards (Python / FastAPI)

- **Python Version**: 3.11+
- **Code Style**: Black formatter, Flake8 / Ruff linting, explicit type hints on all function arguments and return types.
- **ORM Standard**: Use SQLAlchemy 2.0 style (`select(Model).where(...)`).
- **Validation**: Use Pydantic v2 schemas for request validation, response serialization, and internal settings.
- **Async Usage**: Use `async def` for I/O bound FastAPI routes. Heavy synchronous operations (PDF parsing, CPU bound processing) MUST be offloaded to Celery task queues.

```python
# GOOD: Proper SQLAlchemy 2.0 query with tenant isolation & type annotations
async def get_course_by_id(
    db: AsyncSession, 
    course_id: UUID, 
    tenant_context: TenantContext
) -> Optional[Course]:
    stmt = select(Course).where(
        Course.id == course_id,
        Course.institution_id == tenant_context.institution_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
```

---

## 3. Frontend Coding Standards (Next.js / TypeScript)

- **Framework**: Next.js 14+ App Router (`app/` directory).
- **TypeScript**: Strict type checking (`"strict": true` in `tsconfig.json`). Avoid `any`.
- **UI Components**: `shadcn/ui` components located in `@/components/ui`. Custom components in `@/components/features/`.
- **State Management**: TanStack Query (React Query) for server state; Zustand for local workspace state.
- **Styling**: Utility-first Tailwind CSS.

---

## 4. Testing Standards & Guidelines

- **Backend Framework**: `pytest`, `pytest-asyncio`, `httpx` for AsyncClient testing.
- **Rule for AI Testing**: Unit tests MUST mock AI provider calls (`BaseLLMProvider`) using fixture responses to ensure tests run fast, deterministically, and offline without API costs.
- **Integration Tests**: Tests using test database instance (PostgreSQL + pgvector container) for verifying migrations, vector indices, and SQLAlchemy queries.

---

## 5. Directory Structure Reference

```
smart-academic-ai/
├── apps/
│   ├── web/                      # Next.js 14 Frontend App Router
│   │   ├── src/
│   │   │   ├── app/              # Routes (admin, teacher, student, auth)
│   │   │   ├── components/       # shadcn/ui and custom feature components
│   │   │   ├── lib/              # API clients, utils, formatters
│   │   │   ├── store/            # Zustand stores
│   │   │   └── types/            # TypeScript interface definitions
│   │   ├── package.json
│   │   └── tailwind.config.js
│   │
│   └── backend/                  # FastAPI Application
│       ├── app/
│       │   ├── api/              # API route controllers (v1)
│       │   ├── core/             # Security, JWT, config, database connection
│       │   ├── db/               # Base models, SQLAlchemy models
│       │   ├── models/           # Domain models
│       │   ├── schemas/          # Pydantic schemas
│       │   ├── services/         # Business logic, rule engine, RAG pipeline
│       │   │   ├── ai/           # LLM & Embedding provider abstractions
│       │   │   └── rules/        # Deterministic scoring & gap detection
│       │   └── worker/           # Celery async tasks
│       ├── alembic/              # Database migration scripts
│       ├── tests/                # Pytest unit & integration suite
│       └── requirements.txt
│
├── docker/                       # Dockerfiles & Nginx config
├── docker-compose.yml            # Local & Production container orchestration
├── ARCHITECTURE.md               # System Architecture specification
├── DATABASE.md                   # Database schema & ERD
├── API_SPEC.md                   # REST API & OpenAPI specification
├── RAG_ARCHITECTURE.md           # RAG, Vector & AI pipeline
├── SECURITY.md                   # Multi-tenant security & auth
├── IMPLEMENTATION_PLAN.md        # Roadmap & milestones
└── DEVELOPMENT_RULES.md          # Coding rules & guidelines
```
