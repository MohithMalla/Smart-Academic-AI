# Smart Academic AI - OpenAPI & REST API Specification

## 1. Global API Standards

- **Base URL**: `/api/v1`
- **Protocol**: HTTPS / REST
- **Data Exchange Format**: JSON (`application/json`)
- **Authentication**: HTTP Bearer JWT (`Authorization: Bearer <token>`)
- **Tenant Context**: Automatically resolved from verified JWT claim `institution_id`

---

## 2. Global Response Standard

All endpoints return a standardized envelope structure:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "timestamp": "2026-08-19T22:30:00Z",
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

### Standard Error Payload
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "TENANT_ACCESS_DENIED",
    "message": "User does not have authorization for this institution.",
    "details": []
  },
  "meta": {
    "timestamp": "2026-08-19T22:30:00Z"
  }
}
```

---

## 3. API Module Breakdown

### 3.1 Authentication & Tenant Auth (`/api/v1/auth`)

| Method | Endpoint | Description | Roles Allowed |
|---|---|---|---|
| `POST` | `/auth/login` | Login user, issue JWT access + refresh tokens | Public |
| `POST` | `/auth/refresh` | Refresh JWT access token | Authenticated |
| `GET` | `/auth/me` | Retrieve active user profile & institution context | Authenticated |

### 3.2 Institution, User & Class Management (`/api/v1/institutions`)

| Method | Endpoint | Description | Roles Allowed |
|---|---|---|---|
| `POST` | `/institutions` | Register new tenant institution | SuperAdmin |
| `GET` | `/institutions/current` | Get current institution metadata | Admin |
| `POST` | `/users` | Create user (Teacher/Student/Admin) | Admin |
| `GET` | `/users` | List users within institution (Supports `role`, `page`, `limit`) | Admin, Teacher |
| `POST` | `/courses` | Create course | Admin, Teacher |
| `GET` | `/courses` | List courses within institution | Admin, Teacher, Student |
| `POST` | `/classes` | Create class section under a course | Admin, Teacher |
| `GET` | `/classes` | List classes for a course | Admin, Teacher, Student |

### 3.3 Document Ingestion & Management (`/api/v1/documents`)

| Method | Endpoint | Description | Roles Allowed |
|---|---|---|---|
| `POST` | `/documents/upload` | Upload academic file (PDF/DOCX/TXT) & dispatch async processing | Teacher, Admin |
| `GET` | `/documents` | List course documents (Supports `course_id`, `status`, `page`, `limit`) | Teacher, Student, Admin |
| `GET` | `/documents/{id}/status` | Check document async processing status | Teacher, Student, Admin |
| `DELETE` | `/documents/{id}` | Delete document and associated vector chunks | Teacher, Admin |

### 3.4 RAG Assistant & Academic Intelligence (`/api/v1/rag`)

| Method | Endpoint | Description | Roles Allowed |
|---|---|---|---|
| `POST` | `/rag/query` | Submit query for academic RAG answer with citations | Teacher, Student, Admin |
| `POST` | `/rag/search` | Direct hybrid vector + text search over chunks | Teacher, Student, Admin |

#### Request Body (`POST /api/v1/rag/query`):
```json
{
  "course_id": "8f3b2a19-4c5d-4e9a-9b12-000000000001",
  "query": "Explain the concept of backpropagation in neural networks.",
  "top_k": 5,
  "temperature": 0.2
}
```

#### Response Body:
```json
{
  "success": true,
  "data": {
    "answer": "Backpropagation is a supervised learning algorithm for artificial neural networks...",
    "citations": [
      {
        "document_id": "d1234567-89ab-cdef-0123-456789abcdef",
        "document_title": "Lecture 4 - Neural Networks.pdf",
        "page_number": 12,
        "chunk_content": "...gradient of the loss function with respect to weights...",
        "similarity_score": 0.892
      }
    ]
  }
}
```

### 3.5 Assessments & Submissions (`/api/v1/assessments`)

| Method | Endpoint | Description | Roles Allowed |
|---|---|---|---|
| `POST` | `/assessments` | Create assessment & define question rubric | Teacher, Admin |
| `GET` | `/assessments` | List assessments for course (Supports `course_id`, `class_id`) | Teacher, Student, Admin |
| `POST` | `/assessments/{id}/submissions` | Submit student assessment responses | Student |
| `GET` | `/submissions/{id}` | Get submission score & itemized evaluation | Teacher, Student |
| `POST` | `/submissions/{id}/evaluate` | Trigger deterministic + AI async evaluation | Teacher, Admin |

### 3.6 Analytics & Learning Gaps (`/api/v1/analytics`)

| Method | Endpoint | Description | Roles Allowed |
|---|---|---|---|
| `GET` | `/analytics/student/{student_id}` | Get student performance & gap analytics | Teacher, Student, Admin |
| `GET` | `/analytics/course/{course_id}/gaps` | Get course-wide topic gap heatmap | Teacher, Admin |
| `POST` | `/interventions/quiz/generate` | Generate personalized AI practice quiz for a gap | Student, Teacher |

### 3.7 AI Observability & Quality (`/api/v1/observability`)

| Method | Endpoint | Description | Roles Allowed |
|---|---|---|---|
| `GET` | `/observability/ai-logs` | Query AI token usage, latency, and cost logs | Admin |
| `POST` | `/observability/rag-eval` | Run RAG evaluation suite against benchmark query set | Admin, Teacher |
