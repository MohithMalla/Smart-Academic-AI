from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.tenant import TenantContext
from app.models.course import Course
from app.schemas.course import CourseCreate


class CourseService:
    @staticmethod
    async def create_course(
        db: AsyncSession,
        tenant_ctx: TenantContext,
        req: CourseCreate
    ) -> Course:
        """Create course strictly bound to current TenantContext institution_id."""
        # Check code uniqueness within tenant
        stmt_check = select(Course).where(
            Course.institution_id == tenant_ctx.institution_id,
            Course.code == req.code
        )
        res_check = await db.execute(stmt_check)
        if res_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Course code '{req.code}' already exists in this institution."
            )

        course = Course(
            institution_id=tenant_ctx.institution_id,
            code=req.code,
            name=req.name,
            description=req.description,
            created_by=tenant_ctx.user_id
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)
        return course

    @staticmethod
    async def get_course_by_id(
        db: AsyncSession,
        tenant_ctx: TenantContext,
        course_id: UUID
    ) -> Course:
        """Fetch course enforcing strict tenant boundary filter."""
        stmt = select(Course).where(
            Course.id == course_id,
            Course.institution_id == tenant_ctx.institution_id
        )
        res = await db.execute(stmt)
        course = res.scalar_one_or_none()

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found or access forbidden"
            )
        return course

    @staticmethod
    async def list_courses(
        db: AsyncSession,
        tenant_ctx: TenantContext
    ) -> List[Course]:
        """List all courses belonging strictly to current tenant."""
        stmt = select(Course).where(
            Course.institution_id == tenant_ctx.institution_id
        ).order_by(Course.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())
