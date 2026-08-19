from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_tenant_context, require_roles
from app.dependencies.tenant import TenantContext
from app.models.user import Role
from app.schemas.course import CourseCreate, CourseResponse
from app.services.course_service import CourseService

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.INSTITUTION_ADMIN, Role.TEACHER))]
)
async def create_course(
    req: CourseCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """Create course bound to tenant context. Restricted to Admin and Teacher roles."""
    return await CourseService.create_course(db, tenant_ctx, req)


@router.get("", response_model=List[CourseResponse])
async def list_courses(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """List all courses belonging to the authenticated tenant."""
    return await CourseService.list_courses(db, tenant_ctx)


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: UUID,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """Fetch single course by ID enforcing strict tenant isolation."""
    return await CourseService.get_course_by_id(db, tenant_ctx, course_id)
