from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterInstitutionRequest,
    TokenResponse
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterInstitutionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new educational tenant institution and initial Institution Admin."""
    return await AuthService.register_institution_and_admin(db, req)


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user with institution_slug, email, and password."""
    return await AuthService.login(db, req)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Exchange valid refresh token for a new access + refresh token pair."""
    return await AuthService.refresh_tokens(db, req.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """Retrieve profile and tenant context of the currently authenticated user."""
    return current_user
