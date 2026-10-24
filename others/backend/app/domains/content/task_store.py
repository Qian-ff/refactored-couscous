"""Short PG transactions for a single globally fenced parser execution."""
from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlmodel import select

from app.domains.core.commands import refresh_identity, tenant_write_lock
from app.domains.content.background_identity import load_identity
from app.domains.content.models import ContentJob, ContentUpload, Library, Material, MaterialVersion, SourceChunk
from app.domains.content.quota import enforce_budget, quota_lock
from app.domains.content.services import editable_material, locked
from app.domains.content.uploads import db_now


def task_identity(db, job):
    identity = load_identity(db, job.owner_id, job.login_session_id, job.work_role)
    refresh_identity(db, identity)
    version = db.get(MaterialVersion, job.version_id)
    material = db.get(Material, version.material_id)
    editable_material(db, identity, material.id, material.library_id)
    library = db.get(Library, material.library_id)
    if job.library_id != library.id or job.school_id != library.school_id:
        raise HTTPException(403, "ACCESS_REVOKED")
    return identity


def lock_owner(db, job):
    identity = load_identity(db, job.owner_id, job.login_session_id, job.work_role)
    refresh_identity(db, identity)


def live(db, job, owner, generation):
    if (job.state != "running" or job.lease_owner != owner or job.generation != generation
            or job.lease_until is None or job.lease_until <= db_now(db)):
        raise HTTPException(409, "TASK_FENCED")
    task_identity(db, job)


def input_spec(db, job):
    version = db.get(MaterialVersion, job.version_id)
    if version.input_kind == "text":
        return {"format": "text", "encoding": "utf-8", "input": version.input_text.encode("utf-8"),
                "hash": version.content_hash, "bytes": len(version.input_text.encode("utf-8"))}
    upload = db.get(ContentUpload, version.upload_id)
    if (upload is None or upload.state != "sealed" or upload.library_id != job.library_id
            or upload.expected_hash != version.content_hash):
        raise HTTPException(409, "CORRUPT_FILE")
    return {"format": upload.format, "encoding": upload.encoding, "key": upload.file_key,
            "hash": version.content_hash, "bytes": upload.expected_bytes}


def claim(factory, owner):
    with factory() as db:
        first = db.exec(select(ContentJob).where(ContentJob.state == "queued").order_by(
            ContentJob.created_at, ContentJob.id).limit(1)).first()
        if first is None:
            return None
        tenant_write_lock(db, first.school_id)
        authorization_error = False
        try:
            lock_owner(db, first)
        except HTTPException:
            authorization_error = True
        quota_lock(db)
        blocked = db.exec(select(ContentJob.id).where(or_(ContentJob.state == "running", and_(
            ContentJob.execution_id.is_not(None), ContentJob.stop_confirmed.is_(False))))).first()
        if blocked:
            db.rollback()
            return None
        job = locked(db, ContentJob, first.id)
        if job.state != "queued":
            db.rollback()
            return None
        try:
            if authorization_error:
                raise HTTPException(403, "ACCESS_REVOKED")
            task_identity(db, job)
            specification = input_spec(db, job)
        except HTTPException as error:
            job.state, job.stage = "failed", "failed"
            job.error_code = "CORRUPT_FILE" if error.detail == "CORRUPT_FILE" else "ACCESS_REVOKED"
            job.finished_at, job.stop_confirmed, job.reserved_bytes = db_now(db), True, 0
            version = locked(db, MaterialVersion, job.version_id)
            if version.extraction_state != "succeeded":
                version.extraction_state = "failed"
                db.add(version)
            db.add(job)
            db.commit()
            return None
        job.state, job.stage = "running", "claimed"
        job.execution_id = uuid4()
        job.lease_owner, job.lease_until = owner, db_now(db) + timedelta(seconds=20)
        job.heartbeat_at, job.started_at = db_now(db), db_now(db)
        version = locked(db, MaterialVersion, job.version_id)
        if version.extraction_state == "succeeded":
            raise HTTPException(409, "成功版本不可覆盖")
        version.extraction_state = "running"
        db.add(version)
        db.add(job)
        result = {"job_id": job.id, "execution_id": job.execution_id, "generation": job.generation,
                  "version_id": job.version_id, "spec": specification}
        db.commit()
        return result


def heartbeat(factory, job_id, owner, generation, starting=False):
    with factory() as db:
        original = db.get(ContentJob, job_id)
        tenant_write_lock(db, original.school_id)
        lock_owner(db, original)
        job = locked(db, ContentJob, job_id)
        live(db, job, owner, generation)
        job.heartbeat_at, job.lease_until = db_now(db), db_now(db) + timedelta(seconds=20)
        if starting:
            job.stage = "starting"
        db.add(job)
        db.commit()


def save_snapshot(factory, job_id, owner, generation, result, raw_bytes, free_disk_bytes):
    with factory() as db:
        initial = db.get(ContentJob, job_id)
        tenant_write_lock(db, initial.school_id)
        lock_owner(db, initial)
        quota_lock(db)
        job = locked(db, ContentJob, job_id)
        live(db, job, owner, generation)
        version = locked(db, MaterialVersion, job.version_id)
        if version.extraction_state == "succeeded":
            raise HTTPException(409, "成功快照不可覆盖")
        if db.exec(select(SourceChunk.id).where(SourceChunk.material_version_id == version.id)).first():
            raise HTTPException(409, "解析快照已存在")
        for chunk in result.chunks:
            db.add(SourceChunk(material_version_id=version.id, ordinal=chunk.ordinal,
                               locator=chunk.locator.model_dump(), text=chunk.text, text_hash=chunk.text_hash))
        version.parser_version = result.parser_version
        version.warnings = result.warnings
        version.extraction_state = "succeeded"
        version.retained_bytes += raw_bytes
        job.state, job.stage = "succeeded", "cleaning"
        job.finished_at, job.stop_confirmed = db_now(db), True
        db.add(version)
        db.add(job)
        enforce_budget(db, job.school_id, free_disk_bytes)
        db.commit()


def fail(factory, job_id, execution_id, code, never_started=False, generation=None):
    with factory() as db:
        initial = db.get(ContentJob, job_id)
        if initial is None:
            return
        tenant_write_lock(db, initial.school_id)
        quota_lock(db)
        job = locked(db, ContentJob, job_id)
        if job.execution_id != execution_id or job.generation != generation:
            return
        if job.state != "succeeded":
            if job.state != "canceled":
                job.state = "failed"
                job.error_code = code
            job.finished_at, job.stage = db_now(db), "cleaning"
            version = locked(db, MaterialVersion, job.version_id)
            if version.extraction_state != "succeeded":
                version.extraction_state = "canceled" if job.state == "canceled" else "failed"
                db.add(version)
        if never_started:
            job.stop_confirmed, job.reserved_bytes = True, 0
            job.stage = job.state
            job.lease_owner, job.lease_until = None, None
        db.add(job)
        db.commit()


def cleaned(factory, job_id, execution_id):
    with factory() as db:
        original = db.get(ContentJob, job_id)
        tenant_write_lock(db, original.school_id)
        quota_lock(db)
        row = locked(db, ContentJob, job_id)
        if row.execution_id != execution_id:
            return
        row.stop_confirmed, row.reserved_bytes = True, 0
        row.lease_owner, row.lease_until, row.stage = None, None, row.state
        db.add(row)
        db.commit()


def stopped(factory, job_id, execution_id):
    with factory() as db:
        original = db.get(ContentJob, job_id)
        tenant_write_lock(db, original.school_id)
        row = locked(db, ContentJob, job_id)
        if row.execution_id == execution_id:
            row.stop_confirmed = True
            db.add(row)
            db.commit()


def recovery_candidate(factory, owner):
    with factory() as db:
        candidate = db.exec(select(ContentJob).where(ContentJob.execution_id.is_not(None),
            or_(ContentJob.lease_until.is_(None), ContentJob.lease_until <= db_now(db)),
            or_(ContentJob.state == "running", ContentJob.stop_confirmed.is_(False), ContentJob.reserved_bytes > 0),
        ).order_by(ContentJob.created_at, ContentJob.id).limit(1)).first()
        if candidate is None:
            return None
        tenant_write_lock(db, candidate.school_id)
        quota_lock(db)
        row = locked(db, ContentJob, candidate.id)
        if row.lease_until is not None and row.lease_until > db_now(db):
            db.rollback()
            return None
        if row.state == "running":
            row.state, row.error_code = "failed", "WORKER_INTERRUPTED"
            row.finished_at = db_now(db)
            version = locked(db, MaterialVersion, row.version_id)
            if version.extraction_state != "succeeded":
                version.extraction_state = "failed"
                db.add(version)
        row.generation += 1
        row.lease_owner, row.lease_until = owner, db_now(db) + timedelta(seconds=20)
        row.stage = "cleaning"
        db.add(row)
        result = {"job_id": row.id, "execution_id": row.execution_id}
        db.commit()
        return result
