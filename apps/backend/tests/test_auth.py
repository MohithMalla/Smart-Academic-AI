import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_institution_and_admin(client: AsyncClient):
    payload = {
        "institution_name": "MIT University",
        "institution_slug": "mit-edu",
        "institution_domain": "mit.edu",
        "admin_email": "admin@mit.edu",
        "admin_password": "Password123!",
        "admin_first_name": "Ada",
        "admin_last_name": "Lovelace"
    }

    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_and_get_me(client: AsyncClient):
    # 1. Register
    reg_payload = {
        "institution_name": "Stanford",
        "institution_slug": "stanford-edu",
        "admin_email": "admin@stanford.edu",
        "admin_password": "Password123!",
        "admin_first_name": "John",
        "admin_last_name": "McCarthy"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # 2. Login
    login_payload = {
        "email": "admin@stanford.edu",
        "password": "Password123!",
        "institution_slug": "stanford-edu"
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    access_token = token_data["access_token"]

    # 3. Call /me endpoint
    headers = {"Authorization": f"Bearer {access_token}"}
    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "admin@stanford.edu"
    assert me_data["role"] == "INSTITUTION_ADMIN"
    assert me_data["first_name"] == "John"


@pytest.mark.asyncio
async def test_refresh_token_endpoint(client: AsyncClient):
    # 1. Register
    reg_payload = {
        "institution_name": "Harvard",
        "institution_slug": "harvard-edu",
        "admin_email": "admin@harvard.edu",
        "admin_password": "Password123!",
        "admin_first_name": "Alan",
        "admin_last_name": "Turing"
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    tokens = reg_resp.json()

    # 2. Refresh immediately without artificial delays
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    # Proves immediate access tokens are distinct due to unique jti claim
    assert new_tokens["access_token"] != tokens["access_token"]
