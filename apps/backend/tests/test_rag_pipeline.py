import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.worker.tasks import _async_process_document


@pytest.mark.asyncio
async def test_full_rag_ingestion_query_and_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    setup_test_tenants: dict
):
    headers_a = setup_test_tenants["headers_a"]
    headers_b = setup_test_tenants["headers_b"]
    inst_a_id = setup_test_tenants["inst_a"].id
    inst_b_id = setup_test_tenants["inst_b"].id
    user_a_id = setup_test_tenants["user_a"].id
    user_b_id = setup_test_tenants["user_b"].id

    # 1. Create Course A in Tenant A
    c_a_resp = await client.post(
        "/api/v1/courses",
        json={"code": "PHYS101", "name": "General Physics", "description": "Mechanics and Waves"},
        headers=headers_a
    )
    assert c_a_resp.status_code == 201
    course_a_id = c_a_resp.json()["id"]

    # 2. Create Course B in Tenant B
    c_b_resp = await client.post(
        "/api/v1/courses",
        json={"code": "PHYS101", "name": "Physics B", "description": "Thermal Physics"},
        headers=headers_b
    )
    assert c_b_resp.status_code == 201
    course_b_id = c_b_resp.json()["id"]

    # 3. Upload Academic Document to Tenant A
    doc_content = b"Newton's second law states that Force equals mass times acceleration (F = m * a).\n\fPage 2 content describing kinetic energy equation KE = 0.5 * m * v^2."
    
    upload_resp = await client.post(
        "/api/v1/documents",
        data={"course_id": course_a_id},
        files={"file": ("physics_notes.txt", doc_content, "text/plain")},
        headers=headers_a
    )
    assert upload_resp.status_code == 202
    upload_data = upload_resp.json()
    doc_a_id = upload_data["document_id"]

    # 4. Run async document processor task with active test db_session
    proc_res = await _async_process_document(doc_a_id, use_mock_ai=True, db_session=db_session)
    assert proc_res["status"] == "COMPLETED"

    # 5. Check Document Status API
    status_resp = await client.get(f"/api/v1/documents/{doc_a_id}/status", headers=headers_a)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "COMPLETED"

    # 6. Execute RAG Query as Tenant A
    rag_payload = {
        "course_id": course_a_id,
        "query": "Explain Newton's second law",
        "top_k": 3
    }
    rag_resp = await client.post("/api/v1/rag/query", json=rag_payload, headers=headers_a)
    assert rag_resp.status_code == 200
    rag_data = rag_resp.json()
    assert "answer" in rag_data
    assert "citations" in rag_data
    assert len(rag_data["citations"]) > 0
    assert rag_data["citations"][0]["document_name"] == "physics_notes.txt"

    # 7. Execute SSE Streaming RAG Query
    stream_resp = await client.post("/api/v1/rag/stream", json=rag_payload, headers=headers_a)
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers["content-type"]
    assert "data:" in stream_resp.text

    # 8. Create Conversation Thread & List
    conv_resp = await client.post(
        "/api/v1/rag/conversations",
        json={"title": "Physics Q&A Session", "course_id": course_a_id},
        headers=headers_a
    )
    assert conv_resp.status_code == 201
    conv_a_id = conv_resp.json()["id"]

    list_conv_resp = await client.get("/api/v1/rag/conversations", headers=headers_a)
    assert list_conv_resp.status_code == 200
    assert len(list_conv_resp.json()) == 1

    # =========================================================================
    # MULTI-TENANT SECURITY & ISOLATION REJECTION TESTS
    # =========================================================================

    # Security Test 1: Tenant B cannot access Tenant A Document
    cross_doc_resp = await client.get(f"/api/v1/documents/{doc_a_id}", headers=headers_b)
    assert cross_doc_resp.status_code == 404

    # Security Test 2: Tenant B cannot delete Tenant A Document
    cross_del_resp = await client.delete(f"/api/v1/documents/{doc_a_id}", headers=headers_b)
    assert cross_del_resp.status_code == 404

    # Security Test 3: Tenant B RAG Query for Course A returns no chunks from Tenant A
    cross_rag_payload = {
        "course_id": course_a_id,  # Course A belonging to Tenant A
        "query": "Explain Newton's second law",
        "top_k": 3
    }
    cross_rag_resp = await client.post("/api/v1/rag/query", json=cross_rag_payload, headers=headers_b)
    assert cross_rag_resp.status_code == 200
    # Because Tenant B context filter applies, zero chunks from Tenant A are retrieved
    assert len(cross_rag_resp.json()["citations"]) == 0

    # Security Test 4: Tenant B cannot view Tenant A Conversations
    cross_conv_resp = await client.get(f"/api/v1/rag/conversations/{conv_a_id}/messages", headers=headers_b)
    assert cross_conv_resp.status_code == 404
