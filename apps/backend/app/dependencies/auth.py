from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token, parse_uuid, verify_token_type
from app.db.session import get_db
from app.dependencies.tenant import TenantContext, get_tenant_context_from_user
from app.models.user import Role, User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate JWT access token to retrieve active user."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
        verify_token_type(payload, "access")
        
        user_id_raw = payload.get("sub")
        institution_id_raw = payload.get("institution_id")
        
        if not user_id_raw or not institution_id_raw:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload credentials"
            )
            
        user_id = parse_uuid(user_id_raw)
        institution_id = parse_uuid(institution_id_raw)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Fetch user enforcing tenant isolation filter
    stmt = select(User).where(
        User.id == user_id,
        User.institution_id == institution_id,
        User.is_active == True
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user


async def get_tenant_context(
    current_user: User = Depends(get_current_user)
) -> TenantContext:
    """FastAPI Dependency providing TenantContext derived from authenticated user."""
    return get_tenant_context_from_user(current_user)


def require_roles(*allowed_roles: Role):
    """Reusable dependency generator for role-based authorization."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker
