# Smart Academic AI

> Multi-tenant academic intelligence and personalized learning platform powered by RAG, LLMs, vector search, and asynchronous AI pipelines.

Smart Academic AI is a production-oriented academic intelligence platform designed to help educational institutions transform academic documents, assessments, and student performance data into actionable learning insights.

The platform combines **Retrieval-Augmented Generation (RAG)**, **LLM integration**, **vector search**, **hybrid retrieval**, and **deterministic academic rules** to provide grounded and personalized academic assistance.

---

## 🚀 Features

### 🔐 Multi-Tenant Architecture

- Institution-level tenant isolation
- JWT-based authentication
- Access and refresh tokens
- Role-Based Access Control (RBAC)
- Secure tenant-aware database queries
- UUID-based resource identification

Supported roles:

- Admin
- Teacher
- Student

---

### 📚 AI-Powered Academic RAG

Upload academic material and interact with it using natural language.

The RAG pipeline supports:

- PDF ingestion
- DOCX ingestion
- TXT ingestion
- Text extraction
- Intelligent chunking
- Embedding generation
- Vector similarity search
- PostgreSQL Full-Text Search
- Reciprocal Rank Fusion (RRF)
- Grounded LLM responses
- Source-level citations

### RAG Pipeline

```text
Document Upload
      ↓
Text Extraction
      ↓
Document Chunking
      ↓
Embedding Generation
      ↓
PostgreSQL + pgvector
      ↓
┌─────────────────────┐
│ Vector Search       │
│         +           │
│ Full-Text Search    │
└──────────┬──────────┘
           ↓
          RRF
           ↓
       Top-K Context
           ↓
          LLM
           ↓
 Grounded Response
           ↓
        Citations
