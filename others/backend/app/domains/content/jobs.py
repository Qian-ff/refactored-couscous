"""Short persisted task transitions, including cancellation fencing and explicit retries."""
from uuid import UUID
import json

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlmodel import select

from app.domains.core.policy import resource_access
from app.domains.content.access import descriptor, require_version
from app.domains.content.models import ContentJob, Library, Material, MaterialVersion
from app.domains.content.quota import enforce_budget, enforce_queue, quota_lock
from app.domains.content.services import editable_material, execute_command, locked, require_key
from app.domains.content.uploads import db_now


def job_access(db, identity, job_id):
    job = db.get(ContentJob, job_id)
    if job is None:
        raise HTTPException(403, "无权读取处理任务")
    library = db.get(Library, job.library_id)
    manager = library is not None and resource_access(db, identity, descriptor(library)).review
    owner = job.owner_id == identity.user.id and job.work_role == identity.work_role
    if not owner and not manager:
        raise HTTPException(403, "无权读取处理任务")
    require_version(db, identity, job.version_id)
    return job


def job_view(db, identity, job_id):
    row = job_access(db, identity, job_id)
    return {"job_id": str(row.id), "version_id": str(row.version_id), "state": row.state, "stage": row.stage,
            "error_code": row.error_code, "created_at": row.created_at, "started_at": row.started_at,
            "finished_at": row.finished_at}


def cancel_job(db, identity, job_id, key):
    require_key(key)
    original = job_access(db, identity, job_id)

    def action():
        quota_lock(db)
        row = locked(db, ContentJob, job_id)
        if row.state in {"queued", "running"}:
            row.state, row.stage = "canceled", "stopping" if row.execution_id else "canceled"
            row.generation += 1
            row.finished_at = db_now(db)
            if row.execution_id is None:
                row.reserved_bytes = 0
                row.stop_confirmed = True
            version = locked(db, MaterialVersion, row.version_id)
            if version.extraction_state != "succeeded":
                version.extraction_state = "canceled"
                db.add(version)
            db.add(row)
        return {"job_id": str(row.id)}

    return execute_command(db, identity, original.school_id, "content.job.cancel", key,
                           {"id": str(job_id)}, action, lambda: job_access(db, identity, job_id))


def retry_job(db, identity, job_id, key, free_disk_bytes):
    require_key(key)
    original = job_access(db, identity, job_id)

    def authorize():
        job = job_access(db, identity, job_id)
        version = db.get(MaterialVersion, job.version_id)
        material = db.get(Material, version.material_id)
        editable_material(db, identity, material.id, material.library_id)

    def action():
        quota_lock(db)
        old = locked(db, ContentJob, job_id)
        version = locked(db, MaterialVersion, old.version_id)
        if old.state not in {"failed", "canceled"} or version.extraction_state == "succeeded":
            raise HTTPException(409, "成功资料须重解析为新版本，当前任务不可重试")
        active = db.exec(select(ContentJob.id).where(ContentJob.version_id == version.id, or_(
            ContentJob.state.in_(["queued", "running"]),
            (ContentJob.execution_id.is_not(None) & ContentJob.stop_confirmed.is_(False)),
            ContentJob.reserved_bytes > 0))).first()
        if active:
            raise HTTPException(409, "旧处理或清理尚未结束，暂不能重试")
        enforce_queue(db, identity.user.id)
        job = ContentJob(owner_id=identity.user.id, login_session_id=identity.login.id, work_role=identity.work_role,
                         school_id=old.school_id, library_id=old.library_id, version_id=version.id)
        version.extraction_state = "queued"
        db.add(version)
        db.add(job)
        enforce_budget(db, old.school_id, free_disk_bytes)
        return {"job_id": str(job.id), "version_id": str(version.id)}

    return execute_command(db, identity, original.school_id, "content.job.retry", key,
                           {"id": str(job_id)}, action, authorize,
                           lambda result: job_access(db, identity, UUID(result["job_id"])))


def reparse_version(db, identity, version_id, key, free_disk_bytes):
    require_key(key)
    original, material, _projection = require_version(db, identity, version_id)
    library = db.get(Library, material.library_id)

    def authorize():
        version, parent, _projection = require_version(db, identity, version_id)
        editable_material(db, identity, parent.id, parent.library_id)
        if version.extraction_state != "succeeded":
            raise HTTPException(409, "尚未成功的版本请重试原任务")

    def action():
        quota_lock(db)
        parent = locked(db, Material, material.id)
        source = locked(db, MaterialVersion, original.id)
        enforce_queue(db, identity.user.id)
        latest = db.exec(select(func.max(MaterialVersion.version_no)).where(
            MaterialVersion.material_id == parent.id)).one()
        version = MaterialVersion(material_id=parent.id, version_no=int(latest) + 1,
                                  input_kind=source.input_kind, upload_id=source.upload_id,
                                  input_text=source.input_text, content_hash=source.content_hash,
                                  source_metadata=source.source_metadata, allow_cloud=False,
                                  retained_bytes=(len(source.input_text.encode("utf-8")) + len(json.dumps(
                                      source.source_metadata, ensure_ascii=False).encode("utf-8")))
                                  if source.input_kind == "text" else 0,
                                  created_by=identity.user.id)
        db.add(version)
        db.flush()
        job = ContentJob(owner_id=identity.user.id, login_session_id=identity.login.id, work_role=identity.work_role,
                         school_id=library.school_id, library_id=library.id, version_id=version.id)
        db.add(job)
        enforce_budget(db, library.school_id, free_disk_bytes)
        return {"version_id": str(version.id), "job_id": str(job.id)}

    return execute_command(db, identity, library.school_id, "content.version.reparse", key,
                           {"id": str(version_id)}, action, authorize,
                           lambda result: require_version(db, identity, UUID(result["version_id"])))
