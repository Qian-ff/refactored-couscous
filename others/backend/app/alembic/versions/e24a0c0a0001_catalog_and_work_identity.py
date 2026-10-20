"""A0 compatible catalog backfill and identity defaults; retain every old class/relationship ID."""
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa

revision = "e24a0c0a0001"
down_revision = "c7d7105add2f"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    conflicts = connection.execute(sa.text("""
        SELECT user_id FROM role_grant GROUP BY user_id
        HAVING bool_or(role = 'student') AND bool_or(role <> 'student')
    """)).scalars().all()
    if conflicts:
        raise RuntimeError("Student role conflicts; data preserved. Review account IDs: "
                           + ", ".join(str(value) for value in conflicts))
    op.create_table("course_catalog",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("school_id", sa.Uuid(), nullable=False),
        sa.Column("college_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "school_id"),
        sa.UniqueConstraint("school_id", "code"),
        sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
        sa.ForeignKeyConstraint(["college_id", "school_id"], ["college.id", "college.school_id"]),
        sa.ForeignKeyConstraint(["owner_id", "school_id"], ["app_user.id", "app_user.school_id"]),
    )
    op.create_index("ix_course_catalog_school_id", "course_catalog", ["school_id"])
    op.add_column("course", sa.Column("catalog_id", sa.Uuid(), nullable=True))
    rows = connection.execute(sa.text("""
        SELECT c.*, (SELECT s.user_id FROM course_staff s
          WHERE s.course_id = c.id AND s.is_primary ORDER BY s.id LIMIT 1) AS owner_id
        FROM course c ORDER BY c.id
    """)).mappings().all()
    for row in rows:
        catalog_id = uuid5(NAMESPACE_URL, "https://labconnect.invalid/catalog-migration/" + str(row["id"]))
        connection.execute(sa.text("""INSERT INTO course_catalog
            (id, school_id, college_id, owner_id, code, title, created_at)
            VALUES (:catalog, :school_id, :college_id, :owner_id, :code, :title, :created_at)"""),
            {**row, "catalog": catalog_id})
        connection.execute(sa.text("UPDATE course SET catalog_id=:catalog WHERE id=:id"),
                           {"catalog": catalog_id, "id": row["id"]})
    op.alter_column("course", "catalog_id", nullable=False)
    op.create_index("ix_course_catalog_id", "course", ["catalog_id"])
    op.create_foreign_key("fk_course_catalog_school", "course", "course_catalog",
                          ["catalog_id", "school_id"], ["id", "school_id"])
    op.add_column("login_session", sa.Column("default_work_role", sa.String(20), nullable=True))
    # Parent-row locking also protects callers that use SQL rather than the shared B writer.
    op.execute("""CREATE FUNCTION labconnect_check_role_family() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      PERFORM 1 FROM app_user WHERE id = NEW.user_id FOR UPDATE;
      IF (NEW.role = 'student' AND EXISTS(SELECT 1 FROM role_grant
          WHERE user_id=NEW.user_id AND id<>NEW.id AND role<>'student')) OR
         (NEW.role <> 'student' AND EXISTS(SELECT 1 FROM role_grant
          WHERE user_id=NEW.user_id AND id<>NEW.id AND role='student')) THEN
        RAISE EXCEPTION 'student account cannot hold staff roles' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$""")
    op.execute("""CREATE TRIGGER role_family_guard BEFORE INSERT OR UPDATE ON role_grant
        FOR EACH ROW EXECUTE FUNCTION labconnect_check_role_family()""")


def downgrade():
    op.execute("DROP TRIGGER role_family_guard ON role_grant")
    op.execute("DROP FUNCTION labconnect_check_role_family()")
    op.drop_column("login_session", "default_work_role")
    op.drop_constraint("fk_course_catalog_school", "course", type_="foreignkey")
    op.drop_index("ix_course_catalog_id", "course")
    op.drop_column("course", "catalog_id")
    op.drop_index("ix_course_catalog_school_id", "course_catalog")
    op.drop_table("course_catalog")
