from dataclasses import dataclass
from uuid import UUID
from fastapi import Depends, HTTPException, status
from app.models.user import Role, User


@dataclass
class TenantContext:
    """Explicit multi-tenant context derived exclusively from authenticated JWT user."""
    user_id: UUID
    institution_id: UUID
    role: Role
    user: User


def get_tenant_context_from_user(current_user: User) -> TenantContext:
    """Construct TenantContext from validated authenticated User instance."""
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an institution."
        )
    return TenantContext(
        user_id=current_user.id,
        institution_id=current_user.institution_id,
        role=current_user.role,
        user=current_user
    )
