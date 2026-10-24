"""Short material commands. Public projections and streaming live outside these transactions."""
import hashlib
import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.core.auth import Identity
from app.domains.core.commands import check_revision, execute_command as core_execute_command, touch
from app.domains.core.policy import resource_access
from app.domains.content.access import descriptor, require_library, require_version, resolve_scope
from app.domains.content.models import (
    ContentJob, Library, Material, MaterialPublication, MaterialReview, MaterialVersion, now,
)
from app.domains.content.quota import enforce_budget, enforce_queue, quota_lock
from app.domains.content.schemas import (
    LibraryChange, LibraryCreate, ReviewDecision, ReviewSubmit, RevisionInput, TextMaterialCreate,
)


def locked(db, model, record_id):
    row = db.exec(select(model).where(model.id == record_id).with_for_update()
                  .execution_options(populate_existing=True)).first()
    if row is None:
        raise HTTPException(403, "对象不存在或无权操作")
    return row


def execute_command(db, identity, school_id, operation, key, payload, action,
                    authorize=None, authorize_replay=None):
    def current_authorization():
        # Pre-transaction lookups must not freeze old parent/library state in the identity map.
        db.expire_all()
        if authorize:
            authorize()
    return core_execute_command(db, identity, school_id, operation, key, payload, action,
                                current_authorization, authorize_replay)


def require_key(key):
    if not isinstance(key, str) or not 8 <= len(key) <= 128:
        raise HTTPException(422, "须提供8至128字符的Idempotency-Key")


def library_manager(db, identity, library_id):
    row = locked(db, Library, library_id)
    if not resource_access(db, identity, descriptor(row)).review:
        raise HTTPException(403, "无权管理此资料库")
    return row


def create_library(db: Session, identity: Identity, request: LibraryCreate, key: str):
    require_key(key)
    scope = resolve_scope(db, request.scope, request.parent_id)

    def authorize():
        current = resolve_scope(db, request.scope, request.parent_id)
        proposed = Library(scope=request.scope, audience=request.audience, title=request.title,
                           creator_id=identity.user.id, **current)
        if not resource_access(db, identity, descriptor(proposed)).review:
            raise HTTPException(403, "创建资料库须有目标范围审核管理权")

    def action():
        row = Library(scope=request.scope, audience=request.audience, title=request.title,
                      creator_id=identity.user.id, **resolve_scope(db, request.scope, request.parent_id))
        db.add(row)
        return {"library_id": str(row.id)}

    def replay(result):
        library_manager(db, identity, UUID(result["library_id"]))

    return execute_command(db, identity, scope["school_id"], "content.library.create", key,
                           request.model_dump(mode="json"), action, authorize, replay)


def change_library(db: Session, identity: Identity, library_id: UUID, request: LibraryChange, key: str):
    require_key(key)
    original = db.get(Library, library_id)
    if original is None:
        raise HTTPException(403, "资料库不存在或无权操作")

    def action():
        row = library_manager(db, identity, library_id)
        check_revision(row, request.revision)
        if request.title is not None:
            row.title = request.title
        if request.active is not None:
            row.active = request.active
        touch(row)
        db.add(row)
        return {"library_id": str(row.id)}

    return execute_command(db, identity, original.school_id, "content.library.change", key,
                           {"id": str(library_id), **request.model_dump()}, action,
                           lambda: library_manager(db, identity, library_id))


def editable_material(db, identity, material_id, library_id):
    material = locked(db, Material, material_id)
    if material.library_id != library_id or material.retired:
        raise HTTPException(403, "资料归属不符或已停用")
    library = db.get(Library, material.library_id)
    access = resource_access(db, identity, descriptor(library, creator_id=material.creator_id))
    if not library.active or not access.read or not (
            access.review or (access.submit and material.creator_id == identity.user.id)):
        raise HTTPException(403, "无权在此资料创建版本")
    return material


def create_text_version(db: Session, identity: Identity, request: TextMaterialCreate,
                        key: str, free_disk_bytes: int | None):
    require_key(key)
    library = require_library(db, identity, request.library_id, "submit")

    def authorize():
        require_library(db, identity, request.library_id, "submit")
        if request.material_id:
            editable_material(db, identity, request.material_id, request.library_id)

    def action():
        quota_lock(db)
        enforce_queue(db, identity.user.id)
        if request.material_id:
            material = editable_material(db, identity, request.material_id, request.library_id)
            if material.title != request.title:
                raise HTTPException(409, "版本标题须与现有资料一致，修改标题请使用资料管理操作")
        else:
            material = Material(library_id=request.library_id, creator_id=identity.user.id, title=request.title)
            db.add(material)
            db.flush()
        latest = db.exec(select(func.coalesce(func.max(MaterialVersion.version_no), 0)).where(
            MaterialVersion.material_id == material.id)).one()
        raw = request.text.encode("utf-8")
        metadata = request.source_metadata.model_dump()
        retained = len(raw) + len(json.dumps(metadata, ensure_ascii=False).encode("utf-8"))
        version = MaterialVersion(material_id=material.id, version_no=int(latest) + 1, input_kind="text",
                                  input_text=request.text, content_hash=hashlib.sha256(raw).hexdigest(),
                                  source_metadata=metadata, created_by=identity.user.id, retained_bytes=retained)
        db.add(version)
        db.flush()
        job = ContentJob(owner_id=identity.user.id, work_role=identity.work_role,
                         login_session_id=identity.login.id, school_id=library.school_id,
                         library_id=library.id, version_id=version.id)
        db.add(job)
        enforce_budget(db, library.school_id, free_disk_bytes)
        return {"material_id": str(material.id), "version_id": str(version.id), "job_id": str(job.id)}

    return execute_command(db, identity, library.school_id, "content.material.text", key,
                           request.model_dump(mode="json"), action, authorize,
                           lambda result: require_version(db, identity, UUID(result["version_id"])))


def warnings_hash(version: MaterialVersion):
    data = json.dumps(version.warnings, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def validate_publication_source(version, source: Library, target: Library, statement: str):
    if version.extraction_state != "succeeded":
        raise HTTPException(409, "资料尚未成功解析")
    if not statement.strip():
        raise HTTPException(422, "须声明整份原件的教学使用授权")
    if source.school_id is not None and target.school_id is not None and source.school_id != target.school_id:
        raise HTTPException(403, "不允许学校私库直接跨校共享")
    if target.scope == "platform_public":
        metadata = version.source_metadata
        if not (metadata.get("public_reuse_allowed") is True and metadata.get("license")
                and metadata.get("license_url")):
            raise HTTPException(409, "缺少明确的公开复用许可及来源记录")


def submit_review(db: Session, identity: Identity, request: ReviewSubmit, key: str):
    require_key(key)
    target = require_library(db, identity, request.target_library_id, "submit")

    def authorize():
        version, material, _projection = require_version(db, identity, request.version_id)
        editable_material(db, identity, material.id, material.library_id)
        current_target = require_library(db, identity, request.target_library_id, "submit")
        validate_publication_source(version, db.get(Library, material.library_id), current_target,
                                    request.authorization_statement)

    def action():
        version = locked(db, MaterialVersion, request.version_id)
        row = MaterialReview(version_id=version.id, target_library_id=target.id,
                             submitter_id=identity.user.id, warning_hash=warnings_hash(version),
                             authorization_statement=request.authorization_statement)
        db.add(row)
        return {"review_id": str(row.id)}

    return execute_command(db, identity, target.school_id, "content.review.submit", key,
                           request.model_dump(mode="json"), action, authorize)


def review_manager(db, identity, review_id):
    row = locked(db, MaterialReview, review_id)
    target = require_library(db, identity, row.target_library_id, "review")
    return row, target


def decide_review(db: Session, identity: Identity, review_id: UUID, request: ReviewDecision, key: str):
    require_key(key)
    initial = db.get(MaterialReview, review_id)
    if initial is None:
        raise HTTPException(403, "审核记录不存在或无权访问")
    target = require_library(db, identity, initial.target_library_id, "review")

    def action():
        row, current_target = review_manager(db, identity, review_id)
        check_revision(row, request.revision)
        if row.state != "submitted":
            raise HTTPException(409, "审核已决定，重新提审须新增记录")
        version, material, _projection = require_version(db, identity, row.version_id)
        if request.decision == "approved":
            validate_publication_source(version, db.get(Library, material.library_id), current_target,
                                        row.authorization_statement)
            if (not request.warnings_acknowledged or not request.original_authorized
                    or request.warning_hash != row.warning_hash or row.warning_hash != warnings_hash(version)):
                raise HTTPException(409, "须核对当前警告及整份原件开放授权")
        elif not request.reason or not request.reason.strip():
            raise HTTPException(422, "拒绝审核须填写原因")
        row.state = request.decision
        row.reason = request.reason
        row.original_authorized = request.original_authorized if request.decision == "approved" else False
        row.reviewer_id = identity.user.id
        row.decided_at = now()
        touch(row)
        db.add(row)
        return {"review_id": str(row.id)}

    return execute_command(db, identity, target.school_id, "content.review.decide", key,
                           {"id": str(review_id), **request.model_dump()}, action,
                           lambda: review_manager(db, identity, review_id))


def publish_review(db: Session, identity: Identity, review_id: UUID, request: RevisionInput, key: str):
    require_key(key)
    initial = db.get(MaterialReview, review_id)
    if initial is None:
        raise HTTPException(403, "审核记录不存在或无权访问")
    target = require_library(db, identity, initial.target_library_id, "review")

    def action():
        review, current_target = review_manager(db, identity, review_id)
        check_revision(review, request.revision)
        if review.state != "approved" or not review.original_authorized:
            raise HTTPException(409, "须先审核批准该确切版本")
        version, material, _projection = require_version(db, identity, review.version_id)
        if material.retired:
            raise HTTPException(409, "源资料已停用，不允许新发布")
        validate_publication_source(version, db.get(Library, material.library_id), current_target,
                                    review.authorization_statement)
        if review.warning_hash != warnings_hash(version):
            raise HTTPException(409, "警告快照不匹配，须重新审核")
        previous = db.exec(select(MaterialPublication).where(MaterialPublication.review_id == review.id)).first()
        if previous:
            if not previous.active:
                raise HTTPException(409, "旧发布已停用，须重新提审")
            return {"publication_id": str(previous.id)}
        publication = MaterialPublication(review_id=review.id, version_id=review.version_id,
                                          target_library_id=current_target.id, published_by=identity.user.id)
        db.add(publication)
        return {"publication_id": str(publication.id)}

    return execute_command(db, identity, target.school_id, "content.publication.create", key,
                           {"review_id": str(review_id), **request.model_dump()}, action,
                           lambda: review_manager(db, identity, review_id))


def retire_publication(db: Session, identity: Identity, publication_id: UUID, request: RevisionInput, key: str):
    require_key(key)
    original = db.get(MaterialPublication, publication_id)
    if original is None:
        raise HTTPException(403, "发布记录不存在或无权访问")
    target = require_library(db, identity, original.target_library_id, "review")

    def action():
        row = locked(db, MaterialPublication, publication_id)
        check_revision(row, request.revision)
        if not row.active:
            raise HTTPException(409, "发布已停用")
        row.active = False
        row.retired_at = now()
        touch(row)
        db.add(row)
        return {"publication_id": str(row.id)}

    return execute_command(db, identity, target.school_id, "content.publication.retire", key,
                           {"id": str(publication_id), **request.model_dump()}, action,
                           lambda: require_library(db, identity, original.target_library_id, "review"))
