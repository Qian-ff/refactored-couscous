"""Short-transaction, deployment-wide accounting. No file I/O under the quota lock."""
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, text, or_, and_
from sqlmodel import Session, select

from app.domains.content.models import ContentJob, ContentUpload, Library, Material, MaterialVersion
from app.domains.content.questions.models import (Question, QuestionDraft, QuestionVersion, QuestionReview,
    QuestionPublication, ImportBatch, ImportCreatedQuestion, TransferTask, ExportVersion)
from app.domains.content.lessons.models import SceneAsset, Lesson, LessonDraft, LessonVersion, LessonReview, LessonPublication

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
    added, added_scoped, reservations = c1_accounting_queries(school_id)
    return (upload, version, job, *added), (*scoped, *added_scoped), (outstanding_upload, outstanding_job, *reservations)


def c1_accounting_queries(school_id):
    global_queries, scoped = [], []
    # Canonical fields already count source/activity/origin payloads in these parents.
    for model, parent, key in ((QuestionDraft, Question, QuestionDraft.question_id),
                               (QuestionVersion, Question, QuestionVersion.question_id),
                               (LessonDraft, Lesson, LessonDraft.lesson_id),
                               (LessonVersion, Lesson, LessonVersion.lesson_id)):
        query = select(func.coalesce(func.sum(model.retained_bytes + 256), 0)).select_from(model).join(
            parent, parent.id == key).join(Library, Library.id == parent.library_id)
        global_queries.append(query)
        scoped.append(query.where(Library.school_id == school_id))
    for model, amount in ((SceneAsset, SceneAsset.retained_bytes + 256),
                           (ImportBatch, ImportBatch.retained_bytes + 256),
                           (TransferTask, TransferTask.retained_bytes + TransferTask.reserved_bytes + 256),
                           (Question, 128), (Lesson, 128),
                           (QuestionReview, 256 + func.octet_length(QuestionReview.authorization_statement)
                            + func.coalesce(func.octet_length(QuestionReview.reason), 0)),
                           (LessonReview, 256 + func.octet_length(LessonReview.authorization_statement)
                            + func.coalesce(func.octet_length(LessonReview.reason), 0)),
                           (QuestionPublication, 256), (LessonPublication, 256)):
        library_key = model.target_library_id if model in (QuestionReview, LessonReview, QuestionPublication, LessonPublication) else model.library_id
        query = select(func.coalesce(func.sum(amount), 0) if not isinstance(amount, int) else func.count() * amount).select_from(model).join(
            Library, Library.id == library_key)
        global_queries.append(query)
        scoped.append(query.where(Library.school_id == school_id))
    for model, parent, key in ((ExportVersion, TransferTask, ExportVersion.task_id),
                               (ImportCreatedQuestion, ImportBatch, ImportCreatedQuestion.batch_id)):
        query = select(func.count() * 128).select_from(model).join(parent, parent.id == key).join(
            Library, Library.id == parent.library_id)
        global_queries.append(query)
        scoped.append(query.where(Library.school_id == school_id))
    reservation = select(func.coalesce(func.sum(TransferTask.reserved_bytes), 0))
    return global_queries, scoped, [reservation]


def enforce_budget(db: Session, school_id: UUID | None, free_disk_bytes: int | None):
    """Caller holds quota_lock and has staged all new reservations before this check."""
    db.flush()
    global_queries, scoped_queries, reservation_queries = accounting_queries(school_id)
    sums = [sum(int(db.exec(query).one()) for query in queries)
            for queries in (global_queries, scoped_queries, reservation_queries)]
    validate_budget(*sums, free_disk_bytes)


def enforce_queue(db: Session, owner_id: UUID):
    queries = [select(func.count()).select_from(model).where(model.state == "queued") for model in (ContentJob, TransferTask)]
    if (sum(int(db.exec(query).one()) for query in queries) >= 50 or
            sum(int(db.exec(query.where(model.owner_id == owner_id)).one()) for model, query in zip((ContentJob, TransferTask), queries)) >= 5):
        raise HTTPException(409, "QUEUE_FULL：处理队列已满，请稍后重试")


def pending_receiver(db, owner_id):
    upload = db.exec(select(ContentUpload.id).where(ContentUpload.owner_id == owner_id,
        or_(ContentUpload.state.in_(["created", "receiving"]), ContentUpload.lease_owner.is_not(None)))).first()
    transfer = db.exec(select(TransferTask.id).where(TransferTask.owner_id == owner_id, TransferTask.kind == "import",
        or_(TransferTask.state.in_(["created", "receiving"]), and_(TransferTask.input_sealed.is_(False), TransferTask.lease_owner.is_not(None))))).first()
    return upload is not None or transfer is not None


def receiving_slots(db, *, exclude_upload=None):
    uploads = select(func.count()).select_from(ContentUpload).where(ContentUpload.lease_owner.is_not(None))
    if exclude_upload is not None:
        uploads = uploads.where(ContentUpload.id != exclude_upload)
    transfers = select(func.count()).select_from(TransferTask).where(TransferTask.kind == "import",
        TransferTask.input_sealed.is_(False), TransferTask.lease_owner.is_not(None))
    return int(db.exec(uploads).one()) + int(db.exec(transfers).one())
