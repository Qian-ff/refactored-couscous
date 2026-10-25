"""C02 immutable content snapshots and compatible tenant references.

Static DDL captured from the reviewed C02 model; never imports mutable domain models.
"""
from alembic import op
import sqlalchemy as sa

revision = "c02d0c00001"
down_revision = "b1c0e0a00001"
branch_labels = None
depends_on = None

DDL = (
    """CREATE TABLE content_library (
	id UUID NOT NULL,
	scope VARCHAR(24) NOT NULL,
	school_id UUID,
	college_id UUID,
	catalog_id UUID,
	course_id UUID,
	audience VARCHAR(8) NOT NULL,
	title VARCHAR(200) NOT NULL,
	creator_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_content_library_scope CHECK ((scope='platform_public' AND school_id IS NULL AND college_id IS NULL AND catalog_id IS NULL AND course_id IS NULL) OR (scope='school' AND school_id IS NOT NULL AND college_id IS NULL AND catalog_id IS NULL AND course_id IS NULL) OR (scope='college' AND school_id IS NOT NULL AND college_id IS NOT NULL AND catalog_id IS NULL AND course_id IS NULL) OR (scope='catalog' AND school_id IS NOT NULL AND college_id IS NOT NULL AND catalog_id IS NOT NULL AND course_id IS NULL) OR (scope='course' AND school_id IS NOT NULL AND college_id IS NOT NULL AND catalog_id IS NOT NULL AND course_id IS NOT NULL)),
	CONSTRAINT ck_content_library_audience CHECK (audience IN ('all','staff')),
	FOREIGN KEY(college_id, school_id) REFERENCES college (id, school_id),
	FOREIGN KEY(catalog_id, school_id) REFERENCES course_catalog (id, school_id),
	FOREIGN KEY(course_id, school_id) REFERENCES course (id, school_id),
	CONSTRAINT fk_content_library_course_parent FOREIGN KEY(course_id, school_id, college_id, catalog_id) REFERENCES course (id, school_id, college_id, catalog_id),
	FOREIGN KEY(school_id) REFERENCES school (id),
	FOREIGN KEY(creator_id) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_content_library_scope ON content_library (scope, school_id, college_id, catalog_id, course_id)""",
    """CREATE TABLE content_material (
	id UUID NOT NULL,
	library_id UUID NOT NULL,
	creator_id UUID NOT NULL,
	title VARCHAR(200) NOT NULL,
	revision INTEGER NOT NULL,
	retired BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(library_id) REFERENCES content_library (id),
	FOREIGN KEY(creator_id) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_content_material_library_id ON content_material (library_id)""",
    """CREATE TABLE content_upload (
	id UUID NOT NULL,
	library_id UUID NOT NULL,
	material_id UUID,
	owner_id UUID NOT NULL,
	login_session_id UUID NOT NULL,
	work_role VARCHAR(20) NOT NULL,
	school_id UUID,
	original_name VARCHAR(240) NOT NULL,
	title VARCHAR(200) NOT NULL,
	source_metadata JSONB NOT NULL,
	format VARCHAR(8) NOT NULL,
	encoding VARCHAR(12) NOT NULL,
	mime VARCHAR(150) NOT NULL,
	expected_bytes BIGINT NOT NULL,
	expected_hash VARCHAR(64) NOT NULL,
	file_key VARCHAR(100) NOT NULL,
	state VARCHAR(16) NOT NULL,
	generation INTEGER NOT NULL,
	lease_owner UUID,
	lease_until TIMESTAMP WITH TIME ZONE,
	reserved_bytes BIGINT NOT NULL,
	retained_bytes BIGINT NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	sealed_version_id UUID,
	error_code VARCHAR(40),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_content_upload_session_owner FOREIGN KEY(login_session_id, owner_id) REFERENCES login_session (id, user_id),
	CONSTRAINT ck_content_upload_state CHECK (state IN ('created','receiving','sealed','canceled','expired','failed')),
	CONSTRAINT ck_content_upload_bytes CHECK (expected_bytes > 0 AND expected_bytes <= 20971520 AND reserved_bytes >= 0 AND retained_bytes >= 0),
	CONSTRAINT ck_content_upload_role CHECK (work_role IN ('teacher','administrator')),
	FOREIGN KEY(library_id) REFERENCES content_library (id),
	FOREIGN KEY(material_id) REFERENCES content_material (id),
	FOREIGN KEY(owner_id) REFERENCES app_user (id),
	FOREIGN KEY(login_session_id) REFERENCES login_session (id),
	FOREIGN KEY(school_id) REFERENCES school (id),
	UNIQUE (file_key)
)""",
    """CREATE INDEX ix_content_upload_expiry ON content_upload (state, expires_at)""",
    """CREATE INDEX ix_content_upload_library_id ON content_upload (library_id)""",
    """CREATE INDEX ix_content_upload_owner_state ON content_upload (owner_id, state)""",
    """CREATE INDEX ix_content_upload_school_id ON content_upload (school_id)""",
    """CREATE UNIQUE INDEX uq_content_upload_owner_active ON content_upload (owner_id) WHERE state IN ('created','receiving')""",
    """CREATE TABLE content_material_version (
	id UUID NOT NULL,
	material_id UUID NOT NULL,
	version_no INTEGER NOT NULL,
	input_kind VARCHAR(8) NOT NULL,
	upload_id UUID,
	input_text TEXT,
	content_hash VARCHAR(64) NOT NULL,
	parser_version VARCHAR(200),
	extraction_state VARCHAR(16) NOT NULL,
	source_metadata JSONB NOT NULL,
	warnings JSONB NOT NULL,
	allow_cloud BOOLEAN NOT NULL,
	retained_bytes BIGINT NOT NULL,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_content_material_version UNIQUE (material_id, version_no),
	CONSTRAINT ck_content_version_number CHECK (version_no > 0),
	CONSTRAINT ck_content_version_bytes CHECK (retained_bytes >= 0),
	CONSTRAINT ck_content_version_input CHECK ((input_kind='file' AND upload_id IS NOT NULL AND input_text IS NULL) OR (input_kind='text' AND upload_id IS NULL AND input_text IS NOT NULL)),
	CONSTRAINT ck_content_version_state CHECK (extraction_state IN ('queued','running','succeeded','failed','canceled')),
	FOREIGN KEY(material_id) REFERENCES content_material (id),
	FOREIGN KEY(upload_id) REFERENCES content_upload (id),
	FOREIGN KEY(created_by) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_content_material_version_material_id ON content_material_version (material_id)""",
    """CREATE TABLE content_job (
	id UUID NOT NULL,
	owner_id UUID NOT NULL,
	login_session_id UUID NOT NULL,
	work_role VARCHAR(20) NOT NULL,
	school_id UUID,
	library_id UUID NOT NULL,
	version_id UUID NOT NULL,
	state VARCHAR(16) NOT NULL,
	stage VARCHAR(30) NOT NULL,
	generation INTEGER NOT NULL,
	lease_owner UUID,
	execution_id UUID,
	lease_until TIMESTAMP WITH TIME ZONE,
	heartbeat_at TIMESTAMP WITH TIME ZONE,
	stop_confirmed BOOLEAN NOT NULL,
	reserved_bytes BIGINT NOT NULL,
	error_code VARCHAR(40),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	started_at TIMESTAMP WITH TIME ZONE,
	finished_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT fk_content_job_session_owner FOREIGN KEY(login_session_id, owner_id) REFERENCES login_session (id, user_id),
	CONSTRAINT ck_content_job_state CHECK (state IN ('queued','running','succeeded','failed','canceled')),
	CONSTRAINT ck_content_job_role CHECK (work_role IN ('teacher','administrator')),
	CONSTRAINT ck_content_job_generation CHECK (generation > 0 AND reserved_bytes >= 0),
	FOREIGN KEY(owner_id) REFERENCES app_user (id),
	FOREIGN KEY(login_session_id) REFERENCES login_session (id),
	FOREIGN KEY(school_id) REFERENCES school (id),
	FOREIGN KEY(library_id) REFERENCES content_library (id),
	FOREIGN KEY(version_id) REFERENCES content_material_version (id),
	UNIQUE (execution_id)
)""",
    """CREATE INDEX ix_content_job_owner_state ON content_job (owner_id, work_role, state, created_at, id)""",
    """CREATE INDEX ix_content_job_school_id ON content_job (school_id)""",
    """CREATE INDEX ix_content_job_version_id ON content_job (version_id)""",
    """CREATE UNIQUE INDEX uq_content_job_version_active ON content_job (version_id) WHERE state IN ('queued','running')""",
    """CREATE TABLE content_material_review (
	id UUID NOT NULL,
	version_id UUID NOT NULL,
	target_library_id UUID NOT NULL,
	state VARCHAR(12) NOT NULL,
	submitter_id UUID NOT NULL,
	reviewer_id UUID,
	warning_hash VARCHAR(64) NOT NULL,
	original_authorized BOOLEAN NOT NULL,
	authorization_statement TEXT NOT NULL,
	reason VARCHAR(1000),
	revision INTEGER NOT NULL,
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL,
	decided_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT ck_content_review_state CHECK (state IN ('submitted','approved','rejected')),
	CONSTRAINT uq_content_review_binding UNIQUE (id, version_id, target_library_id),
	FOREIGN KEY(version_id) REFERENCES content_material_version (id),
	FOREIGN KEY(target_library_id) REFERENCES content_library (id),
	FOREIGN KEY(submitter_id) REFERENCES app_user (id),
	FOREIGN KEY(reviewer_id) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_content_review_queue ON content_material_review (target_library_id, state, submitted_at, id)""",
    """CREATE TABLE content_source_chunk (
	id UUID NOT NULL,
	material_version_id UUID NOT NULL,
	ordinal INTEGER NOT NULL,
	locator JSONB NOT NULL,
	text TEXT NOT NULL,
	text_hash VARCHAR(64) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_content_chunk_ordinal UNIQUE (material_version_id, ordinal),
	CONSTRAINT ck_content_chunk_bounds CHECK (ordinal > 0 AND char_length(text) <= 8192),
	FOREIGN KEY(material_version_id) REFERENCES content_material_version (id)
)""",
    """CREATE INDEX ix_content_source_chunk_material_version_id ON content_source_chunk (material_version_id)""",
    """CREATE TABLE content_material_publication (
	id UUID NOT NULL,
	review_id UUID NOT NULL,
	version_id UUID NOT NULL,
	target_library_id UUID NOT NULL,
	active BOOLEAN NOT NULL,
	published_by UUID NOT NULL,
	published_at TIMESTAMP WITH TIME ZONE NOT NULL,
	retired_at TIMESTAMP WITH TIME ZONE,
	revision INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT fk_content_publication_review FOREIGN KEY(review_id, version_id, target_library_id) REFERENCES content_material_review (id, version_id, target_library_id),
	CONSTRAINT uq_content_publication_review UNIQUE (review_id),
	FOREIGN KEY(version_id) REFERENCES content_material_version (id),
	FOREIGN KEY(target_library_id) REFERENCES content_library (id),
	FOREIGN KEY(published_by) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_content_publication_target ON content_material_publication (target_library_id, active, version_id)""",
    """ALTER TABLE content_upload ADD CONSTRAINT fk_content_upload_sealed_version FOREIGN KEY(sealed_version_id) REFERENCES content_material_version (id)""",
)

GUARDS = """-- Candidate for A's migration, not an installer. Requires the eight C tables first.
-- A adds these named UNIQUEs in core metadata/migration before C's composite FKs:
-- login_session(id,user_id): uq_login_session_owner
-- course(id,school_id,college_id,catalog_id): uq_course_content_parent
-- No cascading deletes; application DB role must not own/disable these triggers.

CREATE FUNCTION content_immutable_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE allowed text[];
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_HISTORY_DELETE_FORBIDDEN';
  END IF;
  CASE TG_TABLE_NAME
    WHEN 'content_library' THEN allowed := ARRAY['title','active','revision'];
    WHEN 'content_material' THEN allowed := ARRAY['title','retired','revision'];
    WHEN 'content_material_version' THEN
      IF OLD.extraction_state = 'succeeded' THEN allowed := ARRAY[]::text[];
      ELSE allowed := ARRAY['parser_version','extraction_state','warnings','retained_bytes']; END IF;
    WHEN 'content_source_chunk' THEN allowed := ARRAY[]::text[];
    WHEN 'content_material_review' THEN
      IF OLD.state <> 'submitted' THEN allowed := ARRAY[]::text[];
      ELSE
        allowed := ARRAY['state','reviewer_id','original_authorized','reason','revision','decided_at'];
        IF NEW.state NOT IN ('approved','rejected') OR NEW.reviewer_id IS NULL OR NEW.decided_at IS NULL
          OR NEW.revision <> OLD.revision + 1 OR (NEW.state='approved' AND NOT NEW.original_authorized)
          OR (NEW.state='rejected' AND (NEW.original_authorized OR NULLIF(btrim(NEW.reason),'') IS NULL)) THEN
          RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_REVIEW_TRANSITION';
        END IF;
      END IF;
    WHEN 'content_material_publication' THEN
      allowed := ARRAY['active','retired_at','revision'];
      IF NOT OLD.active OR NEW.active OR NEW.retired_at IS NULL OR NEW.revision <> OLD.revision+1 THEN
        RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_PUBLICATION_TRANSITION';
      END IF;
    WHEN 'content_upload' THEN
      IF OLD.state='sealed' THEN allowed := ARRAY['lease_owner','lease_until'];
      ELSE
        allowed := ARRAY['state','generation','lease_owner','lease_until','reserved_bytes','retained_bytes',
                         'sealed_version_id','material_id','error_code'];
        IF NEW.generation < OLD.generation OR (OLD.material_id IS NOT NULL AND
           NEW.material_id IS DISTINCT FROM OLD.material_id) OR
           (OLD.state IN ('failed','expired','canceled') AND NEW.state <> OLD.state) OR
           (NEW.state='sealed' AND OLD.state <> 'receiving') THEN
          RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_UPLOAD_TRANSITION';
        END IF;
      END IF;
    WHEN 'content_job' THEN
      allowed := ARRAY['state','stage','generation','lease_owner','execution_id','lease_until','heartbeat_at',
                       'stop_confirmed','reserved_bytes','error_code','started_at','finished_at'];
      IF (OLD.execution_id IS NOT NULL AND NEW.execution_id IS DISTINCT FROM OLD.execution_id)
         OR NEW.generation < OLD.generation OR (OLD.stop_confirmed AND NOT NEW.stop_confirmed)
         OR (OLD.state IN ('succeeded','failed','canceled') AND NEW.state <> OLD.state) THEN
        RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_JOB_TRANSITION';
      END IF;
    ELSE RAISE EXCEPTION 'UNEXPECTED_CONTENT_TABLE';
  END CASE;
  IF (to_jsonb(NEW) - allowed) IS DISTINCT FROM (to_jsonb(OLD) - allowed) THEN
    RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_IMMUTABLE_FIELD';
  END IF;
  RETURN NEW;
END $$;

DO $$ DECLARE name text; BEGIN
  FOREACH name IN ARRAY ARRAY['content_library','content_material','content_material_version',
    'content_source_chunk','content_material_review','content_material_publication','content_upload','content_job'] LOOP
    EXECUTE format('CREATE TRIGGER content_immutable BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION content_immutable_guard()', name);
  END LOOP;
END $$;

CREATE FUNCTION content_catalog_parent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_TABLE_NAME='content_library' THEN
    IF NEW.scope='catalog' THEN
      PERFORM 1 FROM course_catalog WHERE id=NEW.catalog_id AND school_id=NEW.school_id
        AND college_id=NEW.college_id FOR SHARE;
      IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_CATALOG_PARENT'; END IF;
    END IF;
  ELSE
    IF (NEW.school_id,NEW.college_id) IS DISTINCT FROM (OLD.school_id,OLD.college_id)
      AND EXISTS (SELECT 1 FROM content_library WHERE scope='catalog' AND catalog_id=OLD.id) THEN
      RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_CATALOG_PARENT_IN_USE';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER content_catalog_parent BEFORE INSERT OR UPDATE ON content_library
  FOR EACH ROW EXECUTE FUNCTION content_catalog_parent_guard();
CREATE TRIGGER content_catalog_parent_in_use BEFORE UPDATE OF school_id,college_id ON course_catalog
  FOR EACH ROW EXECUTE FUNCTION content_catalog_parent_guard();

CREATE FUNCTION content_insert_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE version_state text; source_school uuid; target_school uuid; metadata jsonb; actual_school uuid;
BEGIN
  IF TG_TABLE_NAME='content_source_chunk' THEN
    SELECT extraction_state INTO version_state FROM content_material_version
      WHERE id=NEW.material_version_id FOR UPDATE;
    IF version_state IS DISTINCT FROM 'running' THEN
      RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_SNAPSHOT_NOT_RUNNING';
    END IF;
  ELSIF TG_TABLE_NAME='content_material_version' THEN
    IF NEW.extraction_state <> 'queued' OR NEW.parser_version IS NOT NULL OR NEW.warnings <> '[]'::jsonb THEN
      RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_VERSION_INITIAL_STATE';
    END IF;
  ELSIF TG_TABLE_NAME='content_material_review' THEN
    SELECT v.extraction_state,l.school_id,v.source_metadata INTO version_state,source_school,metadata
      FROM content_material_version v JOIN content_material m ON m.id=v.material_id
      JOIN content_library l ON l.id=m.library_id WHERE v.id=NEW.version_id FOR SHARE OF v,m,l;
    SELECT school_id INTO target_school FROM content_library WHERE id=NEW.target_library_id FOR SHARE;
    IF NEW.state <> 'submitted' OR NEW.reviewer_id IS NOT NULL OR NEW.original_authorized OR NEW.decided_at IS NOT NULL
      OR version_state IS DISTINCT FROM 'succeeded' OR NULLIF(btrim(NEW.authorization_statement),'') IS NULL
      OR (source_school IS NOT NULL AND target_school IS NOT NULL AND source_school <> target_school)
      OR (target_school IS NULL AND (metadata->'public_reuse_allowed' IS DISTINCT FROM 'true'::jsonb
          OR NULLIF(metadata->>'license','') IS NULL OR NULLIF(metadata->>'license_url','') IS NULL)) THEN
      RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_REVIEW_SOURCE';
    END IF;
  ELSIF TG_TABLE_NAME='content_material_publication' THEN
    PERFORM 1 FROM content_material_review WHERE id=NEW.review_id AND version_id=NEW.version_id
      AND target_library_id=NEW.target_library_id AND state='approved' AND original_authorized FOR SHARE;
    IF NOT FOUND OR NOT NEW.active OR NEW.retired_at IS NOT NULL THEN
      RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_PUBLICATION_NOT_APPROVED';
    END IF;
  ELSIF TG_TABLE_NAME IN ('content_upload','content_job') THEN
    SELECT school_id INTO actual_school FROM content_library WHERE id=NEW.library_id FOR SHARE;
    IF actual_school IS DISTINCT FROM NEW.school_id THEN
      RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_SCOPE_MISMATCH';
    END IF;
    IF TG_TABLE_NAME='content_upload' THEN
      IF NEW.state <> 'created' OR NEW.sealed_version_id IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_UPLOAD_INITIAL_STATE';
      END IF;
      IF NEW.material_id IS NOT NULL THEN
        PERFORM 1 FROM content_material WHERE id=NEW.material_id AND library_id=NEW.library_id FOR SHARE;
        IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_UPLOAD_MATERIAL'; END IF;
      END IF;
    ELSE
      PERFORM 1 FROM content_material_version v JOIN content_material m ON m.id=v.material_id
        WHERE v.id=NEW.version_id AND m.library_id=NEW.library_id FOR SHARE OF v,m;
      IF NOT FOUND OR NEW.state <> 'queued' OR NEW.execution_id IS NOT NULL OR NEW.stop_confirmed THEN
        RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_JOB_INITIAL_BINDING';
      END IF;
    END IF;
  END IF;
  RETURN NEW;
END $$;
DO $$ DECLARE name text; BEGIN
  FOREACH name IN ARRAY ARRAY['content_material_version','content_source_chunk','content_material_review',
    'content_material_publication','content_upload','content_job'] LOOP
    EXECUTE format('CREATE TRIGGER content_insert BEFORE INSERT ON %I FOR EACH ROW EXECUTE FUNCTION content_insert_guard()', name);
  END LOOP;
END $$;

-- Deferred because _finish flushes the new version before setting the upload's seal pointer.
-- Reparse can reuse an original, but cannot change its material/library/hash/metadata.
CREATE FUNCTION content_file_binding_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE upload_key uuid; u content_upload%ROWTYPE;
BEGIN
  IF TG_TABLE_NAME='content_upload' THEN upload_key := NEW.id; ELSE upload_key := NEW.upload_id; END IF;
  IF upload_key IS NULL THEN RETURN NULL; END IF;
  SELECT * INTO u FROM content_upload WHERE id=upload_key;
  IF u.state='sealed' OR EXISTS (SELECT 1 FROM content_material_version WHERE upload_id=u.id) THEN
    IF u.state <> 'sealed' OR u.material_id IS NULL OR u.sealed_version_id IS NULL
      OR NOT EXISTS (SELECT 1 FROM content_material_version WHERE id=u.sealed_version_id AND upload_id=u.id)
      OR EXISTS (SELECT 1 FROM content_material_version v JOIN content_material m ON m.id=v.material_id
        WHERE v.upload_id=u.id AND (v.material_id <> u.material_id OR m.library_id <> u.library_id
          OR v.content_hash <> u.expected_hash OR v.source_metadata <> u.source_metadata)) THEN
      RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='CONTENT_FILE_BINDING';
    END IF;
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER content_file_binding AFTER INSERT OR UPDATE ON content_material_version
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION content_file_binding_guard();
CREATE CONSTRAINT TRIGGER content_file_binding AFTER INSERT OR UPDATE ON content_upload
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION content_file_binding_guard();
"""

def upgrade():
    connection = op.get_bind()
    # Existing IDs and associations remain untouched; fail before changing schema.
    for table, columns in (("login_session", "id,user_id"),
                           ("course", "id,school_id,college_id,catalog_id")):
        if connection.execute(sa.text(f"SELECT 1 FROM {table} GROUP BY {columns} HAVING count(*)>1 LIMIT 1")).first():
            raise RuntimeError("C02 legacy key conflict; data retained")
    op.create_unique_constraint("uq_login_session_owner", "login_session", ["id", "user_id"])
    op.create_unique_constraint("uq_course_content_parent", "course", ["id", "school_id", "college_id", "catalog_id"])
    for statement in DDL:
        connection.exec_driver_sql(statement)
    connection.execute(sa.text(GUARDS))


def downgrade():
    connection = op.get_bind()
    connection.exec_driver_sql("DROP TRIGGER content_catalog_parent_in_use ON course_catalog")
    for function in ("content_file_binding_guard", "content_insert_guard", "content_catalog_parent_guard", "content_immutable_guard"):
        connection.exec_driver_sql(f"DROP FUNCTION {function}() CASCADE")
    op.drop_constraint("fk_content_upload_sealed_version", "content_upload", type_="foreignkey")
    op.drop_table('content_material_publication')
    op.drop_table('content_source_chunk')
    op.drop_table('content_material_review')
    op.drop_table('content_job')
    op.drop_table('content_material_version')
    op.drop_table('content_upload')
    op.drop_table('content_material')
    op.drop_table('content_library')
    op.drop_constraint("uq_course_content_parent", "course", type_="unique")
    op.drop_constraint("uq_login_session_owner", "login_session", type_="unique")
