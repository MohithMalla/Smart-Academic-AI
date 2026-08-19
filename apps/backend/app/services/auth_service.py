from datetime import timedelta
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    parse_uuid,
    verify_password,
    verify_token_type
)
from app.models.institution import Institution
from app.models.user import Role, User
from app.schemas.auth import LoginRequest, RegisterInstitutionRequest, TokenResponse


class AuthService:
    @staticmethod
    async def register_institution_and_admin(
        db: AsyncSession,
        req: RegisterInstitutionRequest
    ) -> TokenResponse:
        """Atomic registration of tenant Institution and initial Institution Admin."""
        # 1. Check if slug exists
        stmt_slug = select(Institution).where(Institution.slug == req.institution_slug)
        res_slug = await db.execute(stmt_slug)
        if res_slug.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Institution slug already registered"
            )

        # 2. Create Institution
        institution = Institution(
            name=req.institution_name,
            slug=req.institution_slug,
            domain=req.institution_domain,
            is_active=True
        )
        db.add(institution)
        await db.flush()  # Generate institution.id

        # 3. Create Admin User
        admin_user = User(
            institution_id=institution.id,
            email=req.admin_email.lower(),
            password_hash=hash_password(req.admin_password),
            first_name=req.admin_first_name,
            last_name=req.admin_last_name,
            role=Role.INSTITUTION_ADMIN,
            is_active=True
        )
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)

        # 4. Issue Tokens
        access_token = create_access_token(
            user_id=str(admin_user.id),
            institution_id=str(institution.id),
            role=admin_user.role.value
        )
        refresh_token = create_refresh_token(
            user_id=str(admin_user.id),
            institution_id=str(institution.id),
            role=admin_user.role.value
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    @staticmethod
    async def login(
        db: AsyncSession,
        req: LoginRequest
    ) -> TokenResponse:
        """Authenticate user by institution slug & email, issuing JWT token pair."""
        # 1. Fetch institution
        stmt_inst = select(Institution).where(Institution.slug == req.institution_slug, Institution.is_active == True)
        res_inst = await db.execute(stmt_inst)
        institution = res_inst.scalar_one_or_none()
        
        if not institution:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials or institution"
            )

        # 2. Fetch user
        stmt_user = select(User).where(
            User.institution_id == institution.id,
            User.email == req.email.lower(),
            User.is_active == True
        )
        res_user = await db.execute(stmt_user)
        user = res_user.scalar_one_or_none()

        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # 3. Issue Tokens
        access_token = create_access_token(
            user_id=str(user.id),
            institution_id=str(institution.id),
            role=user.role.value
        )
        refresh_token = create_refresh_token(
            user_id=str(user.id),
            institution_id=str(institution.id),
            role=user.role.value
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    @staticmethod
    async def refresh_tokens(
        db: AsyncSession,
        refresh_token_str: str
    ) -> TokenResponse:
        """Exchange valid Refresh Token for new Access + Refresh Token pair."""
        try:
            payload = decode_token(refresh_token_str)
            verify_token_type(payload, "refresh")
            
            user_id_raw = payload.get("sub")
            institution_id_raw = payload.get("institution_id")
            
            if not user_id_raw or not institution_id_raw:
                raise ValueError("Invalid payload claims: missing sub or institution_id")

            user_id = parse_uuid(user_id_raw)
            institution_id = parse_uuid(institution_id_raw)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )

        # Verify user still active
        stmt = select(User).where(
            User.id == user_id,
            User.institution_id == institution_id,
            User.is_active == True
        )
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive or no longer exists"
            )

        # Issue new token pair
        new_access_token = create_access_token(
            user_id=str(user.id),
            institution_id=str(user.institution_id),
            role=user.role.value
        )
        new_refresh_token = create_refresh_token(
            user_id=str(user.id),
            institution_id=str(user.institution_id),
            role=user.role.value
        )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
