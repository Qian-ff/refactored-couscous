"""Candidate router; only A mounts it after migration and real integration checks."""
import asyncio
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request
from starlette.responses import StreamingResponse

from app.domains.core.auth import CurrentIdentity, Db
from app.domains.content import downloads, jobs, management_queries, queries, services, uploads
from app.domains.content.runtime import Runtime
from app.domains.content.schemas import (
    LibraryChange, LibraryCreate, MaterialChange, PublicationCreate, ReviewDecision, ReviewSubmit,
    RevisionInput, TextMaterialCreate, UploadCreate,
)
from app.domains.content.uploads import _io
from app.domains.content.upload_fence import FenceUnavailable
from app.domains.content.views import (
    Capabilities, ChunkPage, CommandResult, JobView, LibraryView, Page, PublicationView, ReviewView,
    SubmitTarget, UploadView, VersionView,
)

router = APIRouter(prefix="/content", tags=["content"])
CommandKey = Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=2147483647)]
Keyword = Annotated[str, Query(max_length=100)]


@router.get("/capabilities", response_model=Capabilities)
async def capabilities(identity: CurrentIdentity, runtime: Runtime):
    available = False
    try:
        status = await asyncio.wait_for(runtime.runner.capabilities(), 5)
        status.require_supported()
        available = True
    except Exception:
        pass
    return Capabilities(parser_available=available, storage_available=runtime.storage is not None)


@router.get("/libraries", response_model=Page[LibraryView])
def list_libraries(db: Db, identity: CurrentIdentity, q: Keyword = "", offset: Offset = 0, limit: Limit = 50,
                   include_inactive: bool = False):
    return queries.libraries(db, identity, q, offset, limit, include_inactive)


@router.get("/submit-targets", response_model=list[SubmitTarget])
def submit_targets(db: Db, identity: CurrentIdentity, q: Keyword = "", offset: Offset = 0, limit: Limit = 50):
    return queries.targets(db, identity, q, offset, limit)


@router.post("/libraries", response_model=CommandResult, response_model_exclude_none=True, status_code=201)
def create_library(db: Db, identity: CurrentIdentity, body: LibraryCreate, key: CommandKey):
    return services.create_library(db, identity, body, key)


@router.patch("/libraries/{library_id}", response_model=CommandResult, response_model_exclude_none=True)
def change_library(db: Db, identity: CurrentIdentity, library_id: UUID, body: LibraryChange, key: CommandKey):
    return services.change_library(db, identity, library_id, body, key)


@router.post("/materials/text", response_model=CommandResult, response_model_exclude_none=True, status_code=201)
def create_text(db: Db, identity: CurrentIdentity, runtime: Runtime, body: TextMaterialCreate, key: CommandKey):
    free = runtime.free_bytes()
    return services.create_text_version(db, identity, body, key, free)


@router.get("/materials", response_model=Page[VersionView])
def list_materials(db: Db, identity: CurrentIdentity, q: Keyword = "", offset: Offset = 0, limit: Limit = 50,
                   library_id: UUID | None = None, course_id: UUID | None = None,
                   file_type: Literal["pdf", "pptx", "docx", "txt", "text"] | None = None,
                   created_after: datetime | None = None, created_before: datetime | None = None):
    return queries.versions(db, identity, q, offset, limit, library_id=library_id, newest_only=True,
                            course_id=course_id, file_type=file_type, created_after=created_after, created_before=created_before)


@router.patch("/materials/{material_id}", response_model=CommandResult, response_model_exclude_none=True)
def change_material(db: Db, identity: CurrentIdentity, material_id: UUID, body: MaterialChange, key: CommandKey):
    return services.change_material(db, identity, material_id, body, key)


@router.get("/materials/{material_id}/versions", response_model=Page[VersionView])
def material_versions(db: Db, identity: CurrentIdentity, material_id: UUID, offset: Offset = 0, limit: Limit = 50,
                       library_id: UUID | None = None):
    return queries.versions(db, identity, "", offset, limit, library_id=library_id, material_id=material_id)


@router.get("/versions/{version_id}", response_model=VersionView)
def version_detail(db: Db, identity: CurrentIdentity, version_id: UUID, library_id: UUID | None = None):
    return queries.version_view(db, identity, version_id, library_id)


@router.get("/versions/{version_id}/chunks", response_model=ChunkPage)
def version_chunks(db: Db, identity: CurrentIdentity, version_id: UUID, after: Offset = 0, limit: Limit = 50,
                    library_id: UUID | None = None):
    return queries.chunks(db, identity, version_id, after, limit, library_id)


@router.get("/versions/{version_id}/download", response_model=None, response_class=StreamingResponse, responses={
    200: {"content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}},
})
async def download_version(db: Db, identity: CurrentIdentity, runtime: Runtime, version_id: UUID,
                           library_id: UUID | None = None):
    context = (identity.user.id, identity.login.id, identity.work_role)
    db.close()
    return await downloads.download(runtime, context, version_id, library_id)


@router.post("/versions/{version_id}/reparse", response_model=CommandResult, response_model_exclude_none=True)
def reparse_version(db: Db, identity: CurrentIdentity, runtime: Runtime, version_id: UUID, key: CommandKey):
    free = runtime.free_bytes()
    return jobs.reparse_version(db, identity, version_id, key, free)


@router.post("/uploads", response_model=CommandResult, response_model_exclude_none=True, status_code=201)
def create_upload(db: Db, identity: CurrentIdentity, runtime: Runtime, body: UploadCreate, key: CommandKey):
    free = runtime.free_bytes()
    return uploads.create_upload(db, identity, body, key, free)


@router.get("/uploads/{upload_id}", response_model=UploadView)
def upload_status(db: Db, identity: CurrentIdentity, upload_id: UUID):
    return uploads.upload_status(db, identity, upload_id)


@router.put("/uploads/{upload_id}/bytes", response_model=CommandResult, response_model_exclude_none=True,
            openapi_extra={"requestBody": {"required": True, "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
async def upload_bytes(request: Request, db: Db, identity: CurrentIdentity, runtime: Runtime, upload_id: UUID,
                       content_type: Annotated[str, Header()] = "application/octet-stream",
                       content_length: Annotated[int | None, Header(ge=1)] = None):
    if content_length is not None and content_length > 20971520:
        raise HTTPException(413, "上传字节超过20MiB上限")
    if content_type.split(";", 1)[0].strip().lower() != "application/octet-stream":
        raise HTTPException(415, "须以application/octet-stream传输原始字节")
    storage = runtime.require_storage()
    context = (identity.user.id, identity.login.id, identity.work_role)
    db.close()
    return await uploads.receive_upload(runtime.factory, storage, context, upload_id, request.stream())


@router.post("/uploads/{upload_id}/cancel", response_model=CommandResult, response_model_exclude_none=True)
async def cancel_upload(db: Db, identity: CurrentIdentity, runtime: Runtime, upload_id: UUID, key: CommandKey):
    result = uploads.cancel_upload(db, identity, upload_id, key)
    db.close()
    if runtime.storage:
        try:
            await _io(uploads.cleanup_idle_upload, runtime.factory, runtime.storage, upload_id)
        except (OSError, FenceUnavailable):
            raise HTTPException(503, "STORAGE_CLEANUP_FAILED：预留空间保持占用") from None
    return result


@router.get("/jobs", response_model=Page[JobView])
def list_jobs(db: Db, identity: CurrentIdentity, offset: Offset = 0, limit: Limit = 50, version_id: UUID | None = None):
    return management_queries.own_jobs(db, identity, offset, limit, version_id)


@router.get("/jobs/{job_id}", response_model=JobView)
def job_status(db: Db, identity: CurrentIdentity, job_id: UUID):
    return jobs.job_view(db, identity, job_id)


@router.post("/jobs/{job_id}/cancel", response_model=CommandResult, response_model_exclude_none=True)
def cancel_job(db: Db, identity: CurrentIdentity, job_id: UUID, key: CommandKey):
    return jobs.cancel_job(db, identity, job_id, key)


@router.post("/jobs/{job_id}/retry", response_model=CommandResult, response_model_exclude_none=True)
def retry_job(db: Db, identity: CurrentIdentity, runtime: Runtime, job_id: UUID, key: CommandKey):
    free = runtime.free_bytes()
    return jobs.retry_job(db, identity, job_id, key, free)


@router.get("/material-reviews", response_model=Page[ReviewView])
def list_reviews(db: Db, identity: CurrentIdentity, offset: Offset = 0, limit: Limit = 50,
                  library_id: UUID | None = None, state: Literal["submitted", "approved", "rejected"] | None = None,
                  version_id: UUID | None = None):
    return management_queries.reviews(db, identity, offset, limit, library_id, state, version_id)


@router.get("/material-reviews/{review_id}", response_model=ReviewView)
def review_detail(db: Db, identity: CurrentIdentity, review_id: UUID):
    return management_queries.review_view(db, identity, review_id)


@router.post("/material-reviews", response_model=CommandResult, response_model_exclude_none=True, status_code=201)
def submit_review(db: Db, identity: CurrentIdentity, body: ReviewSubmit, key: CommandKey):
    return services.submit_review(db, identity, body, key)


@router.post("/material-reviews/{review_id}/decision", response_model=CommandResult, response_model_exclude_none=True)
def decide_review(db: Db, identity: CurrentIdentity, review_id: UUID, body: ReviewDecision, key: CommandKey):
    return services.decide_review(db, identity, review_id, body, key)


@router.get("/material-publications", response_model=Page[PublicationView])
def list_publications(db: Db, identity: CurrentIdentity, library_id: UUID, offset: Offset = 0, limit: Limit = 50,
                      version_id: UUID | None = None):
    return management_queries.publications(db, identity, library_id, offset, limit, version_id)


@router.post("/material-publications", response_model=CommandResult, response_model_exclude_none=True, status_code=201)
def publish_review(db: Db, identity: CurrentIdentity, body: PublicationCreate, key: CommandKey):
    return services.publish_review(db, identity, body.review_id, RevisionInput(revision=body.revision), key)


@router.post("/material-publications/{publication_id}/retire", response_model=CommandResult, response_model_exclude_none=True)
def retire_publication(db: Db, identity: CurrentIdentity, publication_id: UUID, body: RevisionInput, key: CommandKey):
    return services.retire_publication(db, identity, publication_id, body, key)
