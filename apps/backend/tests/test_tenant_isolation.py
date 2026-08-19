import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_multi_tenant_course_isolation(client: AsyncClient, setup_test_tenants: dict):
    headers_a = setup_test_tenants["headers_a"]
    headers_b = setup_test_tenants["headers_b"]

    # 1. User A creates Course A in Tenant A
    course_a_resp = await client.post(
        "/api/v1/courses",
        json={"code": "CS101", "name": "Intro to Computer Science", "description": "Tenant A Course"},
        headers=headers_a
    )
    assert course_a_resp.status_code == 201
    course_a = course_a_resp.json()
    course_a_id = course_a["id"]

    # 2. User B creates Course B in Tenant B
    course_b_resp = await client.post(
        "/api/v1/courses",
        json={"code": "CS101", "name": "Intro to Data Science", "description": "Tenant B Course"},
        headers=headers_b
    )
    assert course_b_resp.status_code == 201
    course_b = course_b_resp.json()
    course_b_id = course_b["id"]

    # 3. User A attempts to access Course B using Course B's exact UUID
    cross_access_resp = await client.get(
        f"/api/v1/courses/{course_b_id}",
        headers=headers_a
    )
    # MUST return 404 Not Found (or 403 Forbidden). Must NOT return Course B data!
    assert cross_access_resp.status_code in [404, 403]

    # 4. User A lists courses - MUST only return Course A
    list_a_resp = await client.get("/api/v1/courses", headers=headers_a)
    assert list_a_resp.status_code == 200
    list_a = list_a_resp.json()
    
    course_ids_for_a = [c["id"] for c in list_a]
    assert course_a_id in course_ids_for_a
    assert course_b_id not in course_ids_for_a

    # 5. User B lists courses - MUST only return Course B
    list_b_resp = await client.get("/api/v1/courses", headers=headers_b)
    assert list_b_resp.status_code == 200
    list_b = list_b_resp.json()
    
    course_ids_for_b = [c["id"] for c in list_b]
    assert course_b_id in course_ids_for_b
    assert course_a_id not in course_ids_for_b


@pytest.mark.asyncio
async def test_client_supplied_tenant_id_tampering_ignored(client: AsyncClient, setup_test_tenants: dict):
    headers_a = setup_test_tenants["headers_a"]
    inst_b_id = str(setup_test_tenants["inst_b"].id)

    # User A tries to pass Tenant B's institution_id in payload or query
    tampered_payload = {
        "code": "MATH101",
        "name": "Calculus I",
        "institution_id": inst_b_id  # Malicious client injection attempt
    }

    create_resp = await client.post("/api/v1/courses", json=tampered_payload, headers=headers_a)
    assert create_resp.status_code == 201
    created_course = create_resp.json()

    # Verify created course belongs strictly to Tenant A, NOT Tenant B!
    assert created_course["institution_id"] == str(setup_test_tenants["inst_a"].id)
    assert created_course["institution_id"] != inst_b_id
