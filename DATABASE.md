# Smart Academic AI - Database Architecture & Schema Specification

## 1. Overview & Technology Stack

- **Database Engine**: PostgreSQL 16
- **Vector Search Extension**: `pgvector` (`v0.5.0+`)
- **ORM**: SQLAlchemy 2.0 (Async Drivers: `asyncpg` for FastAPI, `psycopg3` / `psycopg2` for Celery/Alembic)
- **Migrations**: Alembic

---

## 2. Multi-Tenancy Strategy & Data Isolation

Smart Academic AI uses a **Shared Database, Shared Schema** design with a strict `institution_id` discriminator column present on all tenant-scoped tables.

### Tenant-Scoped Isolation Principle
1. Every database query targeting tenant entities MUST enforce:
   ```sql
   WHERE institution_id = :tenant_id
   ```
2. The `institution_id` MUST be extracted from the authenticated JWT token context (`TenantContext`) and NEVER trusted from client-supplied HTTP headers, query parameters, or request body.
3. Every foreign key constraint and query index includes `institution_id` to guarantee tenant isolation during joins and vector searches.

---

## 3. Entity-Relationship Diagram (ERD)

```mermaid
erdiagram
    INSTITUTION ||--o{ USER : contains
    INSTITUTION ||--o{ COURSE : owns
    COURSE ||--o{ CLASS : offers
    USER ||--o{ CLASS : teaches
    CLASS ||--o{ ENROLLMENT : has_students
    USER ||--o{ ENROLLMENT : enrolled_in

    COURSE ||--o{ DOCUMENT : has
    COURSE ||--o{ TOPIC : defines
    COURSE ||--o{ ASSESSMENT : contains

    DOCUMENT ||--o{ DOCUMENT_CHUNK : chunked_into
    DOCUMENT_CHUNK ||--o{ CHUNK_EMBEDDING : has_vector

    ASSESSMENT ||--o{ QUESTION : contains
    TOPIC ||--o{ QUESTION : maps_to

    ASSESSMENT ||--o{ STUDENT_SUBMISSION : produces
    USER ||--o{ STUDENT_SUBMISSION : submits

    STUDENT_SUBMISSION ||--o{ SUBMISSION_ANSWER : evaluates
    QUESTION ||--o{ SUBMISSION_ANSWER : receives

    USER ||--o{ LEARNING_GAP : exhibits
    TOPIC ||--o{ LEARNING_GAP : targets

    USER ||--o{ GENERATED_QUIZ : receives
    GENERATED_QUIZ ||--o{ GENERATED_QUIZ_QUESTION : contains

    INSTITUTION ||--o{ AI_REQUEST_LOG : monitors
    INSTITUTION ||--o{ RAG_EVALUATION_RUN : evaluates
```

---

## 4. Complete Schema Specification

### 4.1 Institutions, Users & Roles

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Institutions (Tenants)
CREATE TABLE institutions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    domain VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Users (Admin, Teacher, Student)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('INSTITUTION_ADMIN', 'TEACHER', 'STUDENT')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_email_institution UNIQUE (institution_id, email)
);
CREATE INDEX idx_users_tenant ON users(institution_id);
CREATE INDEX idx_users_email ON users(email);
```

### 4.2 Courses, Classes, Topics & Enrollments

```sql
-- Courses
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_course_code_tenant UNIQUE (institution_id, code)
);
CREATE INDEX idx_courses_tenant ON courses(institution_id);

-- Classes / Class Sections
CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL, -- e.g., "Section A - Fall 2026"
    academic_term VARCHAR(50) NOT NULL, -- e.g., "Fall 2026"
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_class_course_term UNIQUE (institution_id, course_id, name, academic_term)
);
CREATE INDEX idx_classes_tenant_course ON classes(institution_id, course_id);
CREATE INDEX idx_classes_teacher ON classes(institution_id, teacher_id);

-- Topics / Academic Taxonomies
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES topics(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_topics_course ON topics(institution_id, course_id);

-- Student Enrollments
CREATE TABLE enrollments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_student_class UNIQUE (class_id, student_id)
);
CREATE INDEX idx_enrollments_student ON enrollments(institution_id, student_id);
CREATE INDEX idx_enrollments_class ON enrollments(institution_id, class_id);
```

### 4.3 Academic Documents & Vectors (RAG)

```sql
-- Academic Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_type VARCHAR(50) NOT NULL, -- pdf, docx, txt
    file_size_bytes BIGINT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED
    error_message TEXT,
    uploaded_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_documents_tenant_course ON documents(institution_id, course_id);

-- Document Chunks & Vector Store
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    page_number INT,
    token_count INT NOT NULL,
    metadata_json JSONB DEFAULT '{}'::jsonb,
    embedding vector(768), -- Vector dimension for embedding provider
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_chunks_doc ON document_chunks(document_id);
CREATE INDEX idx_chunks_tenant_course ON document_chunks(institution_id, course_id);

-- HNSW Vector Index for Fast Similarity Search
CREATE INDEX idx_chunks_embedding ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### 4.4 Assessments & Student Submissions

```sql
-- Assessments
CREATE TABLE assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    class_id UUID REFERENCES classes(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    total_max_score NUMERIC(6, 2) NOT NULL DEFAULT 100.00,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_assessments_tenant_course ON assessments(institution_id, course_id);

-- Assessment Questions
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE SET NULL,
    question_type VARCHAR(50) NOT NULL CHECK (question_type IN ('MCQ', 'SHORT_ANSWER', 'ESSAY', 'NUMERICAL')),
    question_text TEXT NOT NULL,
    options_json JSONB, -- MCQ options
    correct_answer TEXT NOT NULL,
    max_score NUMERIC(5, 2) NOT NULL,
    rubric_criteria JSONB -- Grading guidelines
);
CREATE INDEX idx_questions_assessment ON questions(assessment_id);

-- Student Submissions
CREATE TABLE student_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_score NUMERIC(6, 2),
    percentage NUMERIC(5, 2),
    status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED', -- SUBMITTED, EVALUATED
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_submissions_student ON student_submissions(institution_id, student_id);

-- Individual Answer Evaluations
CREATE TABLE submission_answers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID NOT NULL REFERENCES student_submissions(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    student_response TEXT NOT NULL,
    obtained_score NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    deterministic_feedback TEXT,
    ai_feedback TEXT,
    topic_id UUID REFERENCES topics(id)
);
```

### 4.5 Analytics, Learning Gaps & Personalized Interventions

```sql
-- Detected Learning Gaps (Rule Engine + AI)
CREATE TABLE learning_gaps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    mastery_score NUMERIC(5, 2) NOT NULL, -- e.g., 42.50%
    severity_level VARCHAR(20) NOT NULL CHECK (severity_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    trigger_reason TEXT NOT NULL, -- Deterministic rule engine explanation
    ai_intervention_summary TEXT, -- LLM-generated explanation
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_learning_gaps_student ON learning_gaps(institution_id, student_id, course_id);

-- AI Generated Targeted Practice Quizzes
CREATE TABLE generated_quizzes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    learning_gap_id UUID REFERENCES learning_gaps(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    questions_json JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    student_score NUMERIC(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 4.6 AI Observability & Cost Tracking

```sql
-- AI Request Logs for Cost & Latency Auditing
CREATE TABLE ai_request_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    request_id VARCHAR(100) NOT NULL,
    prompt_type VARCHAR(100) NOT NULL, -- e.g., RAG_QUERY, FEEDBACK_GEN, QUIZ_GEN
    provider VARCHAR(50) NOT NULL, -- e.g., GEMINI, OPENAI
    model_name VARCHAR(100) NOT NULL,
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    latency_ms INT NOT NULL,
    estimated_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.000000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ai_logs_tenant ON ai_request_logs(institution_id, created_at);
```

### 4.7 RAG Evaluation Store

```sql
-- RAG Quality Benchmark Runs
CREATE TABLE rag_evaluation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    run_name VARCHAR(255) NOT NULL,
    total_questions INT NOT NULL,
    hit_rate NUMERIC(5, 4) NOT NULL, -- e.g., 0.8500 (85%)
    citation_accuracy NUMERIC(5, 4) NOT NULL,
    context_relevance NUMERIC(5, 4) NOT NULL,
    groundedness_score NUMERIC(5, 4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```
