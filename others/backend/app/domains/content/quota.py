"""Short-transaction, deployment-wide accounting. No file I/O under the quota lock."""
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, text
from sqlmodel import Session, select

from app.domains.content.models import ContentJob, ContentUpload, Library, Material, MaterialVersion

SCHOOL_BYTES = 1024**3
GLOBAL_BYTES = 5 * 1024**3
DISK_FLOOR = 1024**3
PARSE_RESERVATION = 32 * 1024**2


def quota_lock(db: Session):
    # Called after execute_command's tenant lock; all C write paths must keep this order.
    db.execute(text("SELECT pg_advisory_xact_lock(716238904113)"))


def validate_budget(total: int, scoped: int, outstanding: int, free_disk_bytes: int | None):
    if free_disk_bytes is None:
        raise HTTPException(503, "STORAGE_UNAVAILABLE：尚未配置存储容量探针")
    if scoped > SCHOOL_BYTES or total > GLOBAL_BYTES:
        raise HTTPException(413, "STORAGE_QUOTA_EXCEEDED：资料存储额度不足")
    if free_disk_bytes - outstanding < DISK_FLOOR:
        raise HTTPException(507, "STORAGE_FULL：磁盘预留空间不足")


def accounting_queries(school_id: UUID | None):
    upload = select(func.coalesce(func.sum(ContentUpload.reserved_bytes + ContentUpload.retained_bytes), 0))
    version = select(func.coalesce(func.sum(MaterialVersion.retained_bytes), 0)).select_from(MaterialVersion).join(
        Material, Material.id == MaterialVersion.material_id).join(Library, Library.id == Material.library_id)
    job = select(func.coalesce(func.sum(ContentJob.reserved_bytes), 0))
    outstanding_upload = select(func.coalesce(func.sum(ContentUpload.reserved_bytes), 0))
    outstanding_job = select(func.coalesce(func.sum(ContentJob.reserved_bytes), 0))
    scoped = (upload.where(ContentUpload.school_id == school_id), version.where(Library.school_id == school_id),
              job.where(ContentJob.school_id == school_id))
    return (upload, version, job), scoped, (outstanding_upload, outstanding_job)


def enforce_budget(db: Session, school_id: UUID | None, free_disk_bytes: int | None):
    """Caller holds quota_lock and has staged all new reservations before this check."""
    db.flush()
    global_queries, scoped_queries, reservation_queries = accounting_queries(school_id)
    sums = [sum(int(db.exec(query).one()) for query in queries)
            for queries in (global_queries, scoped_queries, reservation_queries)]
    validate_budget(*sums, free_disk_bytes)


def enforce_queue(db: Session, owner_id: UUID):
    queued = select(func.count()).select_from(ContentJob).where(ContentJob.state == "queued")
    if int(db.exec(queued).one()) >= 50 or int(db.exec(queued.where(ContentJob.owner_id == owner_id)).one()) >= 5:
        raise HTTPException(409, "QUEUE_FULL：处理队列已满，请稍后重试")
