import uuid
from datetime import timedelta
import pytest
from httpx import AsyncClient

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    parse_uuid,
    verify_password,
    verify_token_type
)
from app.dependencies.tenant import TenantContext
from app.models.user import Role, User


def test_password_hashing_and_verification():
    raw_password = "SecurePassword123!"
    hashed = hash_password(raw_password)
    
    assert hashed != raw_password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")  # Bcrypt hash signature
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_immediate_uniqueness_and_jti_claims():
    user_id = str(uuid.uuid4())
    institution_id = str(uuid.uuid4())
    role = "TEACHER"

    # Generate two access tokens immediately
    access_token_1 = create_access_token(user_id, institution_id, role)
    access_token_2 = create_access_token(user_id, institution_id, role)
    refresh_token = create_refresh_token(user_id, institution_id, role)

    payload_1 = decode_token(access_token_1)
    payload_2 = decode_token(access_token_2)
    payload_refresh = decode_token(refresh_token)

    # 1. Tokens generated immediately must be different strings
    assert access_token_1 != access_token_2

    # 2. Their jti claims must be unique UUIDs
    assert "jti" in payload_1
    assert "jti" in payload_2
    assert "jti" in payload_refresh
    assert payload_1["jti"] != payload_2["jti"]
    assert payload_1["jti"] != payload_refresh["jti"]

    # 3. Access token type is "access"
    assert payload_1["type"] == "access"

    # 4. Refresh token type is "refresh"
    assert payload_refresh["type"] == "refresh"

    # 5. Expiration remains valid
    assert payload_1["exp"] > payload_1["iat"]
    assert payload_refresh["exp"] > payload_refresh["iat"]


def test_token_type_validation_rejection():
    user_id = str(uuid.uuid4())
    inst_id = str(uuid.uuid4())

    access_token = create_access_token(user_id, inst_id, "STUDENT")
    refresh_token = create_refresh_token(user_id, inst_id, "STUDENT")

    payload_access = decode_token(access_token)
    payload_refresh = decode_token(refresh_token)

    verify_token_type(payload_access, "access")
    verify_token_type(payload_refresh, "refresh")

    with pytest.raises(ValueError, match="Invalid token type"):
        verify_token_type(payload_access, "refresh")

    with pytest.raises(ValueError, match="Invalid token type"):
        verify_token_type(payload_refresh, "access")


def test_expired_token_rejection():
    user_id = str(uuid.uuid4())
    inst_id = str(uuid.uuid4())

    expired_token = create_access_token(
        user_id, inst_id, "STUDENT", expires_delta=timedelta(minutes=-10)
    )

    with pytest.raises(ValueError, match="Token has expired"):
        decode_token(expired_token)


def test_parse_uuid_helper():
    valid_uuid_str = "12345678-1234-5678-1234-567812345678"
    parsed = parse_uuid(valid_uuid_str)
    assert isinstance(parsed, uuid.UUID)
    assert str(parsed) == valid_uuid_str

    # Passing existing UUID object
    obj_uuid = uuid.uuid4()
    assert parse_uuid(obj_uuid) == obj_uuid

    # Invalid UUID strings
    with pytest.raises(ValueError, match="Invalid UUID"):
        parse_uuid("not-a-valid-uuid")

    with pytest.raises(ValueError, match="Invalid UUID"):
        parse_uuid(None)


def test_tenant_context_uses_uuid_objects():
    u_id = uuid.uuid4()
    inst_id = uuid.uuid4()

    mock_user = User(
        id=u_id,
        institution_id=inst_id,
        email="test@tenant.edu",
        first_name="Test",
        last_name="User",
        role=Role.TEACHER
    )

    ctx = TenantContext(
        user_id=mock_user.id,
        institution_id=mock_user.institution_id,
        role=mock_user.role,
        user=mock_user
    )

    assert isinstance(ctx.user_id, uuid.UUID)
    assert isinstance(ctx.institution_id, uuid.UUID)
    assert ctx.user_id == u_id
    assert ctx.institution_id == inst_id


@pytest.mark.asyncio
async def test_invalid_uuid_claims_in_token(client: AsyncClient):
    # 1. Token with invalid user_id UUID string
    bad_user_token = create_access_token(
        user_id="invalid-user-uuid",
        institution_id=str(uuid.uuid4()),
        role="STUDENT"
    )
    resp1 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_user_token}"})
    assert resp1.status_code == 401

    # 2. Token with invalid institution_id UUID string
    bad_inst_token = create_access_token(
        user_id=str(uuid.uuid4()),
        institution_id="invalid-institution-uuid",
        role="STUDENT"
    )
    resp2 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_inst_token}"})
    assert resp2.status_code == 401
