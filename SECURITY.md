# Smart Academic AI - Security Architecture & Threat Model

## 1. Core Security Principles

Smart Academic AI handles sensitive academic data, student performance metrics, and proprietary course documents across multiple institutions.

### Golden Security Commandments:
1. **Zero Hardcoded Secrets**: All credentials, keys, and connection strings must be injected via environment variables (`pydantic-settings`).
2. **JWT (`jti`) Claim Uniqueness**: Every JWT token generated contains a unique UUID4 `jti` claim to guarantee token uniqueness and prevent replay vulnerabilities.
3. **Centralized UUID Validation**: All JWT claims (`sub`, `institution_id`) are strictly parsed into Python `uuid.UUID` objects before SQL execution, preventing type coercion attacks.
4. **Prompt Injection Defense**: Untrusted academic document content is enclosed inside strict `<academic_reference_context>` XML data boundaries. The LLM is system-instructed to treat content within these tags strictly as passive text data and disregard any embedded prompt override directives (e.g., "Ignore previous instructions").
5. **Strict Multi-Tenant Vector & RAG Isolation**: Every vector similarity query, full-text search, document lookup, conversation query, and deletion statement includes an explicit `institution_id = :tenant_id` filter derived directly from the authenticated JWT `TenantContext`. Global or cross-tenant vector searches are strictly prohibited.
6. **Untrusted Client Inputs**: **NEVER trust client-supplied `institution_id` in path parameters, query params, or body payload.** The `institution_id` MUST be extracted directly from the verified JWT `TenantContext` in FastAPI dependencies.
7. **Strict Multi-Tenant Isolation**: No database query or vector search can execute without an explicit `institution_id` filter derived from validated JWT context.
8. **Defense in Depth**: Security controls apply at Nginx, FastAPI middleware, database queries, and object storage paths.
9. **Least Privilege Access**: Users can only execute actions permitted by their explicit Role (SuperAdmin, InstitutionAdmin, Teacher, Student).

---

## 2. Threat Vector Mitigation Matrix

| Threat Vector | Severity | Mitigation Strategy | Enforced In |
|---|---|---|---|
| **IDOR / Cross-Tenant Data Access** | Critical | Enforce `institution_id` derived exclusively from JWT `TenantContext` on all SQLAlchemy queries, vector lookups, and file accesses. | FastAPI `TenantContext` Dependency & Repository Layer |
| **Path Traversal / Arbitrary File Writes** | High | Sanitize all uploaded filenames; store files on disk/S3 using randomly generated `UUIDv4` filenames; strictly validate extension and MIME types. | `DocumentIngestionService` |
| **Malicious File Uploads (Executables/Scripts)** | High | Restrict allowed upload types strictly to `.pdf`, `.docx`, `.txt`; enforce max file size limit (50MB); parse via sandboxed libraries. | FastAPI `UploadFile` Validation Middleware |
| **Prompt Injection Attacks** | High | Wrap user RAG inputs in strict context delimiter blocks; sanitize prompt delimiters; enforce structured output schemas via Pydantic on LLM calls. | `RAGService` & `LLMProvider` Wrappers |
| **Secret Leakage** | Critical | `.gitignore` `.env` files; enforce `pydantic-settings` environment validation; static secret scanning in CI/CD pipeline. | Project Config & GitHub Actions |
| **Insecure CORS / Unauthorized API Access** | High | Restrict `Access-Control-Allow-Origin` explicitly to domain whitelist; enforce CORS credentials check; mandate Bearer JWT on protected API endpoints. | FastAPI CORS Middleware |
| **SQL / Vector Injection** | High | Use SQLAlchemy 2.0 parameterized queries exclusively; vector queries use parameterized raw SQL with pgvector operators (`<=>`). | Database Layer |

---

## 3. Authentication & JWT Authorization

### Authentication Flow
- **Password Hashing**: Passwords hashed using **bcrypt** with cost factor `12` or **Argon2id**.
- **Token Format**: Standard JSON Web Tokens (JWT) signed with `HS256` or `RS256`.
- **Token Expiry**:
  - Access Token: `15 minutes`
  - Refresh Token: `7 days` (stored in `HttpOnly`, `SameSite=Strict`, `Secure` cookie).

### JWT Payload Schema
```json
{
  "sub": "u1234567-89ab-cdef-0123-456789abcdef",
  "institution_id": "i9876543-21ba-fedc-3210-9876543210fe",
  "role": "TEACHER",
  "email": "teacher@university.edu",
  "exp": 1787184000,
  "iat": 1787180400
}
```

### Role-Based Access Control (RBAC) Matrix

| Endpoint Group | Super Admin | Institution Admin | Teacher | Student |
|---|---|---|---|---|
| Manage Institutions | ✅ | ❌ | ❌ | ❌ |
| Manage Users / Teachers | ❌ | ✅ | ❌ | ❌ |
| Upload Course Documents | ❌ | ✅ | ✅ | ❌ |
| Query RAG Assistant | ❌ | ✅ | ✅ | ✅ |
| Create Assessments | ❌ | ✅ | ✅ | ❌ |
| Submit Assessment Answers | ❌ | ❌ | ❌ | ✅ |
| View Class Analytics | ❌ | ✅ | ✅ | ❌ |
| View Personal Analytics | ❌ | ❌ | ❌ | ✅ |

---

## 4. Multi-Tenant Enforcement Layer Code Blueprint

FastAPI dependency injection guarantees tenant boundary verification before reaching route handlers:

```python
class TenantContext:
    def __init__(self, user_id: UUID, institution_id: UUID, role: str):
        self.user_id = user_id
        self.institution_id = institution_id
        self.role = role

async def get_tenant_context(
    token_payload: dict = Depends(verify_jwt_token)
) -> TenantContext:
    institution_id = token_payload.get("institution_id")
    if not institution_id:
        raise HTTPException(status_code=403, detail="Tenant context missing in token")
    return TenantContext(
        user_id=UUID(token_payload["sub"]),
        institution_id=UUID(institution_id),
        role=token_payload["role"]
    )
```

---

## 5. Storage Security & Path Traversal Prevention

Uploaded academic files must be safely stored:

```python
# Safe File Storage Pattern
import uuid
import pathspec
from pathlib import Path

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain"
}

def generate_safe_storage_path(base_dir: str, institution_id: UUID, course_id: UUID, original_filename: str) -> Path:
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Disallowed file extension")
    
    # Storage filename uses secure UUIDv4, preventing path traversal
    safe_filename = f"{uuid.uuid4()}{ext}"
    return Path(base_dir) / str(institution_id) / str(course_id) / safe_filename
```
