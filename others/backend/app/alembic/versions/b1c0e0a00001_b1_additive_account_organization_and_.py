"""B1 additive account organization and class management

Revision ID: b1c0e0a00001
Revises: e24a0c0a0001
Create Date: 2026-10-21 12:49:10.590741

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'b1c0e0a00001'
down_revision = 'e24a0c0a0001'
branch_labels = None
depends_on = None


def upgrade():
    # Fail before any schema mutation; existing rows become active by default.
    conflicts = op.get_bind().execute(sa.text("""
        SELECT course_id FROM course_staff WHERE is_primary
        GROUP BY course_id HAVING count(*) > 1
    """)).scalars().all()
    if conflicts:
        raise RuntimeError("Multiple legacy primary teachers; data preserved. Class IDs: "
                           + ", ".join(str(value) for value in conflicts))
    op.create_table('command_receipt',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('subject', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
    sa.Column('work_role', sqlmodel.sql.sqltypes.AutoString(length=24), nullable=False),
    sa.Column('operation', sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
    sa.Column('key', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
    sa.Column('request_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('result', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('subject', 'work_role', 'operation', 'key')
    )
    op.create_table('major',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('school_id', sa.Uuid(), nullable=False),
    sa.Column('college_id', sa.Uuid(), nullable=False),
    sa.Column('code', sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
    sa.Column('revision', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.ForeignKeyConstraint(['college_id', 'school_id'], ['college.id', 'college.school_id'], ),
    sa.ForeignKeyConstraint(['school_id'], ['school.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'school_id', 'college_id'),
    sa.UniqueConstraint('school_id', 'college_id', 'code')
    )
    op.create_index(op.f('ix_major_school_id'), 'major', ['school_id'], unique=False)
    op.create_table('account_invitation',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('school_id', sa.Uuid(), nullable=False),
    sa.Column('college_id', sa.Uuid(), nullable=False),
    sa.Column('major_id', sa.Uuid(), nullable=True),
    sa.Column('code_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('max_uses', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('used_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('revoked', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.CheckConstraint('used_count >= 0 AND max_uses > 0 AND used_count <= max_uses'),
    sa.ForeignKeyConstraint(['college_id', 'school_id'], ['college.id', 'college.school_id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['app_user.id'], ),
    sa.ForeignKeyConstraint(['major_id', 'school_id', 'college_id'], ['major.id', 'major.school_id', 'major.college_id'], ),
    sa.ForeignKeyConstraint(['school_id'], ['school.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code_hash')
    )
    op.create_index(op.f('ix_account_invitation_school_id'), 'account_invitation', ['school_id'], unique=False)
    op.create_table('core_audit_event',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('school_id', sa.Uuid(), nullable=True),
    sa.Column('actor_id', sa.Uuid(), nullable=True),
    sa.Column('work_role', sqlmodel.sql.sqltypes.AutoString(length=24), nullable=False),
    sa.Column('operation', sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
    sa.Column('entity_id', sa.Uuid(), nullable=True),
    sa.Column('details', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['app_user.id'], ),
    sa.ForeignKeyConstraint(['school_id'], ['school.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_core_audit_event_school_id'), 'core_audit_event', ['school_id'], unique=False)
    op.create_table('enrollment_request',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('school_id', sa.Uuid(), nullable=False),
    sa.Column('course_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(length=12), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=12), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('decided_at', sa.DateTime(), nullable=True),
    sa.Column('decided_by', sa.Uuid(), nullable=True),
    sa.CheckConstraint("kind IN ('join','leave')"),
    sa.CheckConstraint("status IN ('pending','approved','rejected','canceled')"),
    sa.ForeignKeyConstraint(['course_id', 'school_id'], ['course.id', 'course.school_id'], ),
    sa.ForeignKeyConstraint(['decided_by'], ['app_user.id'], ),
    sa.ForeignKeyConstraint(['user_id', 'school_id'], ['app_user.id', 'app_user.school_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_enrollment_request_course_id'), 'enrollment_request', ['course_id'], unique=False)
    op.create_index(op.f('ix_enrollment_request_user_id'), 'enrollment_request', ['user_id'], unique=False)
    op.create_index('uq_pending_enrollment_request', 'enrollment_request', ['course_id', 'user_id', 'kind'], unique=True, postgresql_where=sa.text("status = 'pending'"))
    op.add_column('app_user', sa.Column('student_no', sqlmodel.sql.sqltypes.AutoString(length=80), nullable=True))
    op.add_column('app_user', sa.Column('major_id', sa.Uuid(), nullable=True))
    op.add_column('app_user', sa.Column('gender', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True))
    op.add_column('app_user', sa.Column('contact', sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True))
    op.add_column('app_user', sa.Column('must_change_password', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('app_user', sa.Column('revision', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.create_unique_constraint('uq_user_school_student_no', 'app_user', ['school_id', 'student_no'])
    op.create_foreign_key('fk_user_major_organization', 'app_user', 'major', ['major_id', 'school_id', 'college_id'], ['id', 'school_id', 'college_id'])
    op.create_check_constraint('ck_user_major_organization', 'app_user',
                               'major_id IS NULL OR (school_id IS NOT NULL AND college_id IS NOT NULL)')
    op.add_column('college', sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column('college', sa.Column('revision', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.add_column('course', sa.Column('archived', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('course', sa.Column('join_approval', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('course', sa.Column('leave_approval', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('course', sa.Column('join_code_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True))
    op.add_column('course', sa.Column('join_code_expires_at', sa.DateTime(), nullable=True))
    op.add_column('course', sa.Column('revision', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.create_unique_constraint('uq_course_join_code_hash', 'course', ['join_code_hash'])
    op.add_column('course_catalog', sa.Column('archived', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('course_catalog', sa.Column('revision', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.add_column('course_staff', sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.create_index('uq_course_active_primary', 'course_staff', ['course_id'], unique=True, postgresql_where=sa.text('is_primary AND is_active'))
    op.add_column('school', sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column('school', sa.Column('revision', sa.Integer(), server_default=sa.text('1'), nullable=False))



def downgrade():
    raise RuntimeError("B1 keeps account and teaching history; restore a verified backup instead of automatic downgrade")
