"""Initial Phase 1 baseline schema with extensions and core entities

Revision ID: 001_initial_phase1
Revises: 
Create Date: 2026-08-19 23:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_phase1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable PostgreSQL Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # 2. Table: institutions
    op.create_table(
        'institutions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_institutions')),
        sa.UniqueConstraint('slug', name=op.f('uq_institutions_slug'))
    )
    op.create_index(op.f('ix_institutions_slug'), 'institutions', ['slug'], unique=True)

    # 3. Table: users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=255), nullable=False),
        sa.Column('last_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), server_default='STUDENT', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], name=op.f('fk_users_institution_id_institutions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('institution_id', 'email', name='uq_user_institution_email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_institution_id'), 'users', ['institution_id'], unique=False)

    # 4. Table: courses
    op.create_table(
        'courses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_courses_created_by_users'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], name=op.f('fk_courses_institution_id_institutions'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_courses')),
        sa.UniqueConstraint('institution_id', 'code', name='uq_course_institution_code')
    )
    op.create_index(op.f('ix_courses_institution_id'), 'courses', ['institution_id'], unique=False)

    # 5. Table: classes
    op.create_table(
        'classes',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('academic_term', sa.String(length=50), nullable=False),
        sa.Column('teacher_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_classes_course_id_courses'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], name=op.f('fk_classes_institution_id_institutions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], name=op.f('fk_classes_teacher_id_users'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_classes')),
        sa.UniqueConstraint('institution_id', 'course_id', 'name', 'academic_term', name='uq_class_institution_course_name_term')
    )
    op.create_index('idx_classes_institution_course', 'classes', ['institution_id', 'course_id'], unique=False)
    op.create_index(op.f('ix_classes_teacher_id'), 'classes', ['teacher_id'], unique=False)

    # 6. Table: topics
    op.create_table(
        'topics',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_topics_course_id_courses'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], name=op.f('fk_topics_institution_id_institutions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['topics.id'], name=op.f('fk_topics_parent_id_topics'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_topics'))
    )
    op.create_index('idx_topics_institution_course', 'topics', ['institution_id', 'course_id'], unique=False)

    # 7. Table: enrollments
    op.create_table(
        'enrollments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('class_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], name=op.f('fk_enrollments_class_id_classes'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], name=op.f('fk_enrollments_institution_id_institutions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], name=op.f('fk_enrollments_student_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_enrollments')),
        sa.UniqueConstraint('class_id', 'student_id', name='uq_enrollment_class_student')
    )
    op.create_index('idx_enrollments_institution_class', 'enrollments', ['institution_id', 'class_id'], unique=False)
    op.create_index('idx_enrollments_institution_student', 'enrollments', ['institution_id', 'student_id'], unique=False)

    # 8. Table: ai_request_logs
    op.create_table(
        'ai_request_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('estimated_cost', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='SUCCESS', nullable=False),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], name=op.f('fk_ai_request_logs_institution_id_institutions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_ai_request_logs_user_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_request_logs'))
    )
    op.create_index('idx_ai_logs_institution_created', 'ai_request_logs', ['institution_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('ai_request_logs')
    op.drop_table('enrollments')
    op.drop_table('topics')
    op.drop_table('classes')
    op.drop_table('courses')
    op.drop_table('users')
    op.drop_table('institutions')
