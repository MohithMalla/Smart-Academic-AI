import asyncio
import os
import uuid
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure test settings use test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["JWT_SECRET"] = "test-secret-key-smart-academic-ai-32-chars"

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.institution import Institution
from app.models.user import Role, User

# Use SQLite in-memory with aiosqlite for fast isolated testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestAsyncSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def setup_test_tenants(db_session: AsyncSession):
    """Setup Tenant A (User A) and Tenant B (User B) for isolation testing."""
    # Tenant A
    inst_a = Institution(id=uuid.uuid4(), name="Institution A", slug="inst-a", is_active=True)
    db_session.add(inst_a)
    await db_session.flush()

    user_a = User(
        id=uuid.uuid4(),
        institution_id=inst_a.id,
        email="user_a@inst-a.edu",
        password_hash=hash_password("password123"),
        first_name="Alice",
        last_name="Admin",
        role=Role.INSTITUTION_ADMIN,
        is_active=True
    )
    db_session.add(user_a)

    # Tenant B
    inst_b = Institution(id=uuid.uuid4(), name="Institution B", slug="inst-b", is_active=True)
    db_session.add(inst_b)
    await db_session.flush()

    user_b = User(
        id=uuid.uuid4(),
        institution_id=inst_b.id,
        email="user_b@inst-b.edu",
        password_hash=hash_password("password123"),
        first_name="Bob",
        last_name="Admin",
        role=Role.INSTITUTION_ADMIN,
        is_active=True
    )
    db_session.add(user_b)
    await db_session.commit()

    token_a = create_access_token(user_id=str(user_a.id), institution_id=str(inst_a.id), role=user_a.role.value)
    token_b = create_access_token(user_id=str(user_b.id), institution_id=str(inst_b.id), role=user_b.role.value)

    return {
        "inst_a": inst_a,
        "user_a": user_a,
        "token_a": token_a,
        "headers_a": {"Authorization": f"Bearer {token_a}"},
        "inst_b": inst_b,
        "user_b": user_b,
        "token_b": token_b,
        "headers_b": {"Authorization": f"Bearer {token_b}"}
    }
