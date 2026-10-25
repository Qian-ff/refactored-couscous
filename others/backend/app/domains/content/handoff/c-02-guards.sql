-- Candidate for A's migration, not an installer. Requires the eight C tables first.
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
