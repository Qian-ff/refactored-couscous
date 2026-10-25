"""C1 fixed question and lesson tables. Reviewed static DDL; no domain imports."""
from alembic import op
import sqlalchemy as sa

revision = "c1d0c000001"
down_revision = "c02d0c00001"
branch_labels = None
depends_on = None

GUARDS = r"""
CREATE FUNCTION c1_history_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE allowed text[];
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF TG_TABLE_NAME IN ('content_question_draft','content_lesson_draft') THEN RETURN OLD; END IF;
    RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='C1_HISTORY_DELETE_FORBIDDEN';
  END IF;
  -- Even a no-op UPDATE creates a new xmin and must not reopen a sealed parent.
  IF TG_TABLE_NAME IN ('content_question_version','content_lesson_version') THEN
    RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='C1_FIXED_VERSION_UPDATE_FORBIDDEN';
  END IF;
  IF to_jsonb(NEW) = to_jsonb(OLD) THEN RETURN NEW; END IF;
  CASE TG_TABLE_NAME
    WHEN 'content_question' THEN allowed := ARRAY['revision','retired'];
    WHEN 'content_lesson' THEN allowed := ARRAY['revision','retired'];
    WHEN 'content_question_draft' THEN allowed := ARRAY['revision','payload','provenance','duplicate_hash','updated_by','updated_at','retained_bytes'];
    WHEN 'content_lesson_draft' THEN allowed := ARRAY['revision','content','scene_asset_id','updated_by','updated_at','retained_bytes'];
    WHEN 'content_question_review', 'content_lesson_review' THEN
      allowed := ARRAY['state','reviewer_id','reason','revision','decided_at'];
      IF OLD.state <> 'submitted' OR NEW.state NOT IN ('approved','rejected')
         OR NEW.reviewer_id IS NULL OR NEW.decided_at IS NULL OR NEW.revision <> OLD.revision + 1 THEN
        RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='C1_REVIEW_ALREADY_DECIDED';
      END IF;
    WHEN 'content_question_publication', 'content_lesson_publication' THEN
      allowed := ARRAY['active','retired_at','revision'];
      IF NOT OLD.active OR NEW.active OR NEW.retired_at IS NULL OR NEW.revision <> OLD.revision + 1 THEN
        RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='C1_PUBLICATION_RETIRE_ONLY';
      END IF;
    WHEN 'content_question_import_batch' THEN
      allowed := ARRAY['state','revision','preview_hash','row_count','normalized_rows','errors','retained_bytes','committed_at'];
    WHEN 'content_question_transfer_task' THEN
      allowed := ARRAY['state','stage','input_sealed','result_hash','result_bytes','generation','execution_id',
                       'lease_owner','lease_until','stop_confirmed','reserved_bytes','retained_bytes','error_code','finished_at'];
    ELSE allowed := ARRAY[]::text[];
  END CASE;
  IF (to_jsonb(NEW) - allowed) IS DISTINCT FROM (to_jsonb(OLD) - allowed) THEN
    RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='C1_FIXED_BINDING';
  END IF;
  RETURN NEW;
END $$;

CREATE FUNCTION c1_insert_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent_name text; parent_id uuid; parent_xmin xid; full_xid numeric; current_xid numeric;
        review_name text; approved boolean; actual_school uuid;
BEGIN
  CASE TG_TABLE_NAME
    WHEN 'content_question_source' THEN parent_name := 'content_question_version'; parent_id := NEW.question_version_id;
    WHEN 'content_lesson_source', 'content_lesson_question', 'content_lesson_question_origin' THEN
      parent_name := 'content_lesson_version'; parent_id := NEW.lesson_version_id;
    ELSE parent_name := NULL;
  END CASE;
  IF parent_name IS NOT NULL THEN
    EXECUTE format('SELECT xmin FROM %I WHERE id=$1 FOR SHARE', parent_name) INTO parent_xmin USING parent_id;
    -- A visible uncommitted insert belongs to this transaction, including savepoints.
    -- Reconstruct xid8's epoch rather than treating the row's 32-bit xmin as an ancient xid.
    current_xid := pg_current_xact_id()::text::numeric;
    full_xid := floor(current_xid / 4294967296) * 4294967296 + parent_xmin::text::numeric;
    IF full_xid - current_xid > 2147483648 THEN full_xid := full_xid - 4294967296; END IF;
    IF current_xid - full_xid > 2147483648 THEN full_xid := full_xid + 4294967296; END IF;
    IF parent_xmin IS NULL OR pg_xact_status(full_xid::text::xid8) IS DISTINCT FROM 'in progress' THEN
      RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='C1_SNAPSHOT_CLOSED';
    END IF;
  END IF;
  IF TG_TABLE_NAME IN ('content_question_review','content_lesson_review') THEN
    IF NEW.state <> 'submitted' OR NEW.reviewer_id IS NOT NULL OR NEW.decided_at IS NOT NULL OR NEW.revision <> 1 THEN
      RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='C1_REVIEW_INITIAL_STATE';
    END IF;
  ELSIF TG_TABLE_NAME IN ('content_question_publication','content_lesson_publication') THEN
    review_name := CASE TG_TABLE_NAME WHEN 'content_question_publication' THEN 'content_question_review' ELSE 'content_lesson_review' END;
    EXECUTE format('SELECT state=''approved'' FROM %I WHERE id=$1 AND version_id=$2 AND target_library_id=$3 FOR SHARE', review_name)
      INTO approved USING NEW.review_id,NEW.version_id,NEW.target_library_id;
    IF approved IS DISTINCT FROM true OR NOT NEW.active OR NEW.retired_at IS NOT NULL OR NEW.revision <> 1 THEN
      RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='C1_PUBLICATION_NOT_APPROVED';
    END IF;
  ELSIF TG_TABLE_NAME='content_question_transfer_task' THEN
    SELECT school_id INTO actual_school FROM content_library WHERE id=NEW.library_id FOR SHARE;
    IF actual_school IS DISTINCT FROM NEW.school_id THEN
      RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='C1_TRANSFER_SCOPE';
    END IF;
    IF NEW.batch_id IS NOT NULL AND NOT EXISTS (
      SELECT 1 FROM content_question_import_batch b WHERE b.id=NEW.batch_id AND b.library_id=NEW.library_id
        AND b.actor_id=NEW.owner_id AND b.login_session_id=NEW.login_session_id
        AND b.work_role=NEW.work_role AND b.input_hash=NEW.input_hash
    ) THEN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='C1_TRANSFER_BATCH_BINDING'; END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE FUNCTION c1_draft_origin_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  -- Defer until the final transaction state: discard removes ledger rows before the draft.
  IF EXISTS (SELECT 1 FROM content_lesson_draft WHERE lesson_id=OLD.lesson_id)
     AND NOT EXISTS (SELECT 1 FROM content_lesson_draft_question_origin
                     WHERE lesson_id=OLD.lesson_id AND activity_id=OLD.activity_id
                       AND question_version_id=OLD.question_version_id) THEN
    RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='C1_DRAFT_ORIGIN_RETAINED';
  END IF;
  RETURN NULL;
END $$;

DO $$ DECLARE name text; BEGIN
  FOREACH name IN ARRAY ARRAY[
    'content_question','content_question_draft','content_question_version','content_question_source',
    'content_question_review','content_question_publication','content_question_import_batch',
    'content_question_import_result','content_question_transfer_task','content_question_export_version',
    'content_scene_asset','content_lesson','content_lesson_draft','content_lesson_version',
    'content_lesson_source','content_lesson_question','content_lesson_question_origin',
    'content_lesson_review','content_lesson_publication'] LOOP
    EXECUTE format('CREATE TRIGGER c1_history BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION c1_history_guard()',name);
  END LOOP;
  FOREACH name IN ARRAY ARRAY['content_question_source','content_lesson_source','content_lesson_question',
    'content_lesson_question_origin','content_question_review','content_lesson_review',
    'content_question_publication','content_lesson_publication','content_question_transfer_task'] LOOP
    EXECUTE format('CREATE TRIGGER c1_insert BEFORE INSERT ON %I FOR EACH ROW EXECUTE FUNCTION c1_insert_guard()',name);
  END LOOP;
END $$;
CREATE TRIGGER c1_history BEFORE UPDATE ON content_lesson_draft_question_origin
  FOR EACH ROW EXECUTE FUNCTION c1_history_guard();
CREATE CONSTRAINT TRIGGER c1_draft_origin AFTER DELETE ON content_lesson_draft_question_origin
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION c1_draft_origin_guard();
"""

DDL = (
    """CREATE TABLE content_lesson (
	id UUID NOT NULL,
	library_id UUID NOT NULL,
	creator_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	retired BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_lesson_revision CHECK (revision > 0),
	FOREIGN KEY(library_id) REFERENCES content_library (id),
	FOREIGN KEY(creator_id) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_content_lesson_library_id ON content_lesson (library_id)""",
    """CREATE TABLE content_question (
	id UUID NOT NULL,
	library_id UUID NOT NULL,
	creator_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	retired BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_question_revision CHECK (revision > 0),
	FOREIGN KEY(library_id) REFERENCES content_library (id),
	FOREIGN KEY(creator_id) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_content_question_library_id ON content_question (library_id)""",
    """CREATE TABLE content_question_import_batch (
	id UUID NOT NULL,
	library_id UUID NOT NULL,
	actor_id UUID NOT NULL,
	login_session_id UUID NOT NULL,
	work_role VARCHAR(20) NOT NULL,
	input_hash VARCHAR(64) NOT NULL,
	preview_hash VARCHAR(64),
	state VARCHAR(12) NOT NULL,
	revision INTEGER NOT NULL,
	row_count INTEGER NOT NULL,
	normalized_rows JSONB NOT NULL,
	errors JSONB NOT NULL,
	retained_bytes BIGINT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	committed_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT ck_question_batch_state CHECK (state IN ('pending','invalid','ready','committed','expired','canceled','failed')),
	CONSTRAINT ck_question_batch_role CHECK (work_role IN ('teacher','administrator')),
	CONSTRAINT ck_question_batch_budget CHECK (revision > 0 AND retained_bytes >= 0 AND row_count BETWEEN 0 AND 1000),
	CONSTRAINT fk_question_batch_session_owner FOREIGN KEY(login_session_id, actor_id) REFERENCES login_session (id, user_id),
	FOREIGN KEY(library_id) REFERENCES content_library (id),
	FOREIGN KEY(actor_id) REFERENCES app_user (id),
	FOREIGN KEY(login_session_id) REFERENCES login_session (id)
)""",
    """CREATE INDEX ix_question_batch_actor ON content_question_import_batch (actor_id, work_role, created_at, id)""",
    """CREATE TABLE content_scene_asset (
	id UUID NOT NULL,
	library_id UUID NOT NULL,
	svg TEXT NOT NULL,
	content_hash VARCHAR(64) NOT NULL,
	provenance JSONB NOT NULL,
	view_box JSONB NOT NULL,
	creator_id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	retained_bytes BIGINT NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_scene_asset_budget CHECK (retained_bytes >= 0 AND octet_length(svg) <= 262144),
	FOREIGN KEY(library_id) REFERENCES content_library (id),
	FOREIGN KEY(creator_id) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_content_scene_asset_library_id ON content_scene_asset (library_id)""",
    """CREATE TABLE content_lesson_version (
	id UUID NOT NULL,
	lesson_id UUID NOT NULL,
	version_no INTEGER NOT NULL,
	draft_revision INTEGER NOT NULL,
	content JSONB NOT NULL,
	scene_asset_id UUID NOT NULL,
	copied_from_version_id UUID,
	payload_hash VARCHAR(64) NOT NULL,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	retained_bytes BIGINT NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_lesson_version_number UNIQUE (lesson_id, version_no),
	CONSTRAINT uq_lesson_frozen_revision UNIQUE (lesson_id, draft_revision),
	CONSTRAINT ck_lesson_version_budget CHECK (version_no > 0 AND draft_revision > 0 AND retained_bytes >= 0),
	FOREIGN KEY(lesson_id) REFERENCES content_lesson (id),
	FOREIGN KEY(scene_asset_id) REFERENCES content_scene_asset (id),
	FOREIGN KEY(copied_from_version_id) REFERENCES content_lesson_version (id),
	FOREIGN KEY(created_by) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_content_lesson_version_lesson_id ON content_lesson_version (lesson_id)""",
    """CREATE TABLE content_question_import_result (
	id UUID NOT NULL,
	batch_id UUID NOT NULL,
	row_number INTEGER NOT NULL,
	question_id UUID NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_question_import_row UNIQUE (batch_id, row_number),
	FOREIGN KEY(batch_id) REFERENCES content_question_import_batch (id),
	FOREIGN KEY(question_id) REFERENCES content_question (id)
)""",
    """CREATE INDEX ix_content_question_import_result_batch_id ON content_question_import_result (batch_id)""",
    """CREATE TABLE content_question_transfer_task (
	id UUID NOT NULL,
	batch_id UUID,
	kind VARCHAR(8) NOT NULL,
	format VARCHAR(4) NOT NULL,
	library_id UUID NOT NULL,
	school_id UUID,
	owner_id UUID NOT NULL,
	login_session_id UUID NOT NULL,
	work_role VARCHAR(20) NOT NULL,
	input_hash VARCHAR(64) NOT NULL,
	expected_bytes BIGINT NOT NULL,
	input_sealed BOOLEAN NOT NULL,
	file_key VARCHAR(100) NOT NULL,
	result_hash VARCHAR(64),
	result_bytes BIGINT NOT NULL,
	state VARCHAR(12) NOT NULL,
	stage VARCHAR(30) NOT NULL,
	generation INTEGER NOT NULL,
	execution_id UUID,
	lease_owner UUID,
	lease_until TIMESTAMP WITH TIME ZONE,
	stop_confirmed BOOLEAN NOT NULL,
	reserved_bytes BIGINT NOT NULL,
	retained_bytes BIGINT NOT NULL,
	error_code VARCHAR(40),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	finished_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT ck_question_transfer_kind CHECK (kind IN ('import','export') AND format IN ('csv','xlsx')),
	CONSTRAINT ck_question_transfer_state CHECK (state IN ('created','receiving','queued','running','succeeded','failed','canceled','expired')),
	CONSTRAINT ck_question_transfer_budget CHECK (generation > 0 AND reserved_bytes >= 0 AND retained_bytes >= 0),
	CONSTRAINT ck_question_transfer_role CHECK (work_role IN ('teacher','administrator')),
	CONSTRAINT ck_question_transfer_bytes CHECK (expected_bytes BETWEEN 0 AND 16777216 AND result_bytes BETWEEN 0 AND 16777216),
	CONSTRAINT ck_question_import_bytes CHECK (kind='export' OR (expected_bytes > 0 AND expected_bytes <= CASE WHEN format='csv' THEN 1048576 ELSE 5242880 END)),
	CONSTRAINT ck_question_transfer_batch CHECK ((kind='import' AND batch_id IS NOT NULL) OR (kind='export' AND batch_id IS NULL)),
	CONSTRAINT fk_question_transfer_session_owner FOREIGN KEY(login_session_id, owner_id) REFERENCES login_session (id, user_id),
	CONSTRAINT uq_question_transfer_batch UNIQUE (batch_id),
	FOREIGN KEY(batch_id) REFERENCES content_question_import_batch (id),
	FOREIGN KEY(library_id) REFERENCES content_library (id),
	FOREIGN KEY(school_id) REFERENCES school (id),
	FOREIGN KEY(owner_id) REFERENCES app_user (id),
	FOREIGN KEY(login_session_id) REFERENCES login_session (id),
	UNIQUE (file_key),
	UNIQUE (execution_id)
)""",
    """CREATE INDEX ix_question_transfer_queue ON content_question_transfer_task (state, created_at, id)""",
    """CREATE UNIQUE INDEX uq_question_transfer_receiving ON content_question_transfer_task (owner_id) WHERE kind='import' AND state IN ('created','receiving')""",
    """CREATE TABLE content_question_version (
	id UUID NOT NULL,
	question_id UUID NOT NULL,
	version_no INTEGER NOT NULL,
	draft_revision INTEGER NOT NULL,
	payload JSONB NOT NULL,
	provenance JSONB NOT NULL,
	copied_from_version_id UUID,
	payload_hash VARCHAR(64) NOT NULL,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	retained_bytes BIGINT NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_question_version_number UNIQUE (question_id, version_no),
	CONSTRAINT uq_question_frozen_revision UNIQUE (question_id, draft_revision),
	CONSTRAINT ck_question_version_budget CHECK (version_no > 0 AND draft_revision > 0 AND retained_bytes >= 0),
	FOREIGN KEY(question_id) REFERENCES content_question (id),
	FOREIGN KEY(copied_from_version_id) REFERENCES content_question_version (id),
	FOREIGN KEY(created_by) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_content_question_version_question_id ON content_question_version (question_id)""",
    """CREATE TABLE content_lesson_draft (
	lesson_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	content JSONB NOT NULL,
	scene_asset_id UUID NOT NULL,
	copied_from_version_id UUID,
	updated_by UUID NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	retained_bytes BIGINT NOT NULL,
	PRIMARY KEY (lesson_id),
	CONSTRAINT ck_lesson_draft_budget CHECK (revision > 0 AND retained_bytes >= 0),
	FOREIGN KEY(lesson_id) REFERENCES content_lesson (id),
	FOREIGN KEY(scene_asset_id) REFERENCES content_scene_asset (id),
	FOREIGN KEY(copied_from_version_id) REFERENCES content_lesson_version (id),
	FOREIGN KEY(updated_by) REFERENCES app_user (id)
)""",
    """CREATE TABLE content_lesson_question (
	id UUID NOT NULL,
	lesson_version_id UUID NOT NULL,
	activity_id VARCHAR(64) NOT NULL,
	question_version_id UUID NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_lesson_question UNIQUE (lesson_version_id, activity_id),
	FOREIGN KEY(lesson_version_id) REFERENCES content_lesson_version (id),
	FOREIGN KEY(question_version_id) REFERENCES content_question_version (id)
)""",
    """CREATE INDEX ix_content_lesson_question_lesson_version_id ON content_lesson_question (lesson_version_id)""",
    """CREATE TABLE content_lesson_question_origin (
	id UUID NOT NULL,
	lesson_version_id UUID NOT NULL,
	activity_id VARCHAR(64) NOT NULL,
	question_version_id UUID NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_lesson_question_origin UNIQUE (lesson_version_id, activity_id, question_version_id),
	FOREIGN KEY(lesson_version_id) REFERENCES content_lesson_version (id),
	FOREIGN KEY(question_version_id) REFERENCES content_question_version (id)
)""",
    """CREATE INDEX ix_content_lesson_question_origin_lesson_version_id ON content_lesson_question_origin (lesson_version_id)""",
    """CREATE TABLE content_lesson_review (
	id UUID NOT NULL,
	version_id UUID NOT NULL,
	target_library_id UUID NOT NULL,
	state VARCHAR(12) NOT NULL,
	submitter_id UUID NOT NULL,
	reviewer_id UUID,
	authorization_statement VARCHAR(2000) NOT NULL,
	reason VARCHAR(2000),
	revision INTEGER NOT NULL,
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL,
	decided_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT ck_lesson_review_state CHECK (state IN ('submitted','approved','rejected')),
	CONSTRAINT uq_lesson_review_binding UNIQUE (id, version_id, target_library_id),
	FOREIGN KEY(version_id) REFERENCES content_lesson_version (id),
	FOREIGN KEY(target_library_id) REFERENCES content_library (id),
	FOREIGN KEY(submitter_id) REFERENCES app_user (id),
	FOREIGN KEY(reviewer_id) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_lesson_review_queue ON content_lesson_review (target_library_id, state, submitted_at, id)""",
    """CREATE UNIQUE INDEX uq_lesson_review_pending ON content_lesson_review (version_id, target_library_id) WHERE state = 'submitted'""",
    """CREATE TABLE content_question_draft (
	question_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	payload JSONB NOT NULL,
	provenance JSONB NOT NULL,
	copied_from_version_id UUID,
	duplicate_hash VARCHAR(64) NOT NULL,
	updated_by UUID NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	retained_bytes BIGINT NOT NULL,
	PRIMARY KEY (question_id),
	CONSTRAINT ck_question_draft_budget CHECK (revision > 0 AND retained_bytes >= 0),
	FOREIGN KEY(question_id) REFERENCES content_question (id),
	FOREIGN KEY(copied_from_version_id) REFERENCES content_question_version (id),
	FOREIGN KEY(updated_by) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_question_draft_duplicate ON content_question_draft (duplicate_hash)""",
    """CREATE TABLE content_question_export_version (
	id UUID NOT NULL,
	task_id UUID NOT NULL,
	version_id UUID NOT NULL,
	ordinal INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_question_export_version UNIQUE (task_id, version_id),
	CONSTRAINT uq_question_export_ordinal UNIQUE (task_id, ordinal),
	CONSTRAINT ck_question_export_ordinal CHECK (ordinal BETWEEN 0 AND 999),
	FOREIGN KEY(task_id) REFERENCES content_question_transfer_task (id),
	FOREIGN KEY(version_id) REFERENCES content_question_version (id)
)""",
    """CREATE INDEX ix_content_question_export_version_task_id ON content_question_export_version (task_id)""",
    """CREATE TABLE content_question_review (
	id UUID NOT NULL,
	version_id UUID NOT NULL,
	target_library_id UUID NOT NULL,
	state VARCHAR(12) NOT NULL,
	submitter_id UUID NOT NULL,
	reviewer_id UUID,
	authorization_statement VARCHAR(2000) NOT NULL,
	reason VARCHAR(2000),
	revision INTEGER NOT NULL,
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL,
	decided_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT ck_question_review_state CHECK (state IN ('submitted','approved','rejected')),
	CONSTRAINT uq_question_review_binding UNIQUE (id, version_id, target_library_id),
	FOREIGN KEY(version_id) REFERENCES content_question_version (id),
	FOREIGN KEY(target_library_id) REFERENCES content_library (id),
	FOREIGN KEY(submitter_id) REFERENCES app_user (id),
	FOREIGN KEY(reviewer_id) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_question_review_queue ON content_question_review (target_library_id, state, submitted_at, id)""",
    """CREATE UNIQUE INDEX uq_question_review_pending ON content_question_review (version_id, target_library_id) WHERE state = 'submitted'""",
    """CREATE TABLE content_lesson_draft_question (
	id UUID NOT NULL,
	lesson_id UUID NOT NULL,
	activity_id VARCHAR(64) NOT NULL,
	question_version_id UUID NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_lesson_draft_question UNIQUE (lesson_id, activity_id),
	FOREIGN KEY(lesson_id) REFERENCES content_lesson_draft (lesson_id),
	FOREIGN KEY(question_version_id) REFERENCES content_question_version (id)
)""",
    """CREATE INDEX ix_content_lesson_draft_question_lesson_id ON content_lesson_draft_question (lesson_id)""",
    """CREATE TABLE content_lesson_draft_question_origin (
	id UUID NOT NULL,
	lesson_id UUID NOT NULL,
	activity_id VARCHAR(64) NOT NULL,
	question_version_id UUID NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_lesson_draft_question_origin UNIQUE (lesson_id, activity_id, question_version_id),
	FOREIGN KEY(lesson_id) REFERENCES content_lesson_draft (lesson_id),
	FOREIGN KEY(question_version_id) REFERENCES content_question_version (id)
)""",
    """CREATE INDEX ix_content_lesson_draft_question_origin_lesson_id ON content_lesson_draft_question_origin (lesson_id)""",
    """CREATE TABLE content_lesson_publication (
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
	CONSTRAINT fk_lesson_publication_review FOREIGN KEY(review_id, version_id, target_library_id) REFERENCES content_lesson_review (id, version_id, target_library_id),
	CONSTRAINT uq_lesson_publication_review UNIQUE (review_id),
	FOREIGN KEY(version_id) REFERENCES content_lesson_version (id),
	FOREIGN KEY(target_library_id) REFERENCES content_library (id),
	FOREIGN KEY(published_by) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_lesson_publication_target ON content_lesson_publication (target_library_id, active, version_id)""",
    """CREATE TABLE content_question_publication (
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
	CONSTRAINT fk_question_publication_review FOREIGN KEY(review_id, version_id, target_library_id) REFERENCES content_question_review (id, version_id, target_library_id),
	CONSTRAINT uq_question_publication_review UNIQUE (review_id),
	FOREIGN KEY(version_id) REFERENCES content_question_version (id),
	FOREIGN KEY(target_library_id) REFERENCES content_library (id),
	FOREIGN KEY(published_by) REFERENCES app_user (id)
)""",
    """CREATE INDEX ix_question_publication_target ON content_question_publication (target_library_id, active, version_id)""",
    """CREATE TABLE content_lesson_draft_source (
	id UUID NOT NULL,
	lesson_id UUID NOT NULL,
	activity_id VARCHAR(64) NOT NULL,
	material_version_id UUID NOT NULL,
	chunk_id UUID,
	PRIMARY KEY (id),
	CONSTRAINT uq_lesson_draft_source UNIQUE NULLS NOT DISTINCT (lesson_id, activity_id, material_version_id, chunk_id),
	FOREIGN KEY(lesson_id) REFERENCES content_lesson_draft (lesson_id),
	FOREIGN KEY(material_version_id) REFERENCES content_material_version (id),
	FOREIGN KEY(chunk_id) REFERENCES content_source_chunk (id)
)""",
    """CREATE INDEX ix_content_lesson_draft_source_lesson_id ON content_lesson_draft_source (lesson_id)""",
    """CREATE TABLE content_lesson_source (
	id UUID NOT NULL,
	lesson_version_id UUID NOT NULL,
	activity_id VARCHAR(64) NOT NULL,
	material_version_id UUID NOT NULL,
	chunk_id UUID,
	locator JSONB NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_lesson_source UNIQUE NULLS NOT DISTINCT (lesson_version_id, activity_id, material_version_id, chunk_id),
	FOREIGN KEY(lesson_version_id) REFERENCES content_lesson_version (id),
	FOREIGN KEY(material_version_id) REFERENCES content_material_version (id),
	FOREIGN KEY(chunk_id) REFERENCES content_source_chunk (id)
)""",
    """CREATE INDEX ix_content_lesson_source_lesson_version_id ON content_lesson_source (lesson_version_id)""",
    """CREATE TABLE content_question_draft_source (
	id UUID NOT NULL,
	question_id UUID NOT NULL,
	material_version_id UUID NOT NULL,
	chunk_id UUID,
	PRIMARY KEY (id),
	CONSTRAINT uq_question_draft_source UNIQUE NULLS NOT DISTINCT (question_id, material_version_id, chunk_id),
	FOREIGN KEY(question_id) REFERENCES content_question_draft (question_id),
	FOREIGN KEY(material_version_id) REFERENCES content_material_version (id),
	FOREIGN KEY(chunk_id) REFERENCES content_source_chunk (id)
)""",
    """CREATE INDEX ix_content_question_draft_source_question_id ON content_question_draft_source (question_id)""",
    """CREATE TABLE content_question_source (
	id UUID NOT NULL,
	question_version_id UUID NOT NULL,
	material_version_id UUID NOT NULL,
	chunk_id UUID,
	locator JSONB NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_question_source UNIQUE NULLS NOT DISTINCT (question_version_id, material_version_id, chunk_id),
	FOREIGN KEY(question_version_id) REFERENCES content_question_version (id),
	FOREIGN KEY(material_version_id) REFERENCES content_material_version (id),
	FOREIGN KEY(chunk_id) REFERENCES content_source_chunk (id)
)""",
    """CREATE INDEX ix_content_question_source_question_version_id ON content_question_source (question_version_id)""",
)

TABLES = ('content_lesson', 'content_question', 'content_question_import_batch', 'content_scene_asset', 'content_lesson_version', 'content_question_import_result', 'content_question_transfer_task', 'content_question_version', 'content_lesson_draft', 'content_lesson_question', 'content_lesson_question_origin', 'content_lesson_review', 'content_question_draft', 'content_question_export_version', 'content_question_review', 'content_lesson_draft_question', 'content_lesson_draft_question_origin', 'content_lesson_publication', 'content_question_publication', 'content_lesson_draft_source', 'content_lesson_source', 'content_question_draft_source', 'content_question_source')


def upgrade():
    connection = op.get_bind()
    for statement in DDL:
        connection.exec_driver_sql(statement)
    connection.execute(sa.text(GUARDS))


def downgrade():
    connection = op.get_bind()
    for function in ("c1_draft_origin_guard", "c1_insert_guard", "c1_history_guard"):
        connection.exec_driver_sql(f"DROP FUNCTION {function}() CASCADE")
    for name in reversed(TABLES):
        op.drop_table(name)
