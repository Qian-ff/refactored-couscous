"""Candidate staff API. A owns mounting, OpenAPI publication and generated clients."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter

from app.domains.content.questions import imports, lifecycle, queries, services, transfers
from app.domains.content.questions.http import CommandKey, Environment, Keyword, Limit, Offset, StaffIdentity
from app.domains.content.questions.schemas import CopyOrReference, Decision, ParentChange, QuestionChange, QuestionCreate, Revision, Submit
from app.domains.content.questions.views import BankView, CommandResult, DraftView, Page, PublicationView, ReviewView, VersionView
from app.domains.core.auth import Db

router = APIRouter(prefix="/content/questions", tags=["content-questions"])


@router.get("/banks", response_model=Page[BankView])
def banks(db: Db, identity: StaffIdentity, q: Keyword = "", offset: Offset = 0, limit: Limit = 50, include_inactive: bool = False):
    return queries.banks(db, identity, q, offset, limit, include_inactive)


@router.get("/drafts", response_model=Page[DraftView])
def drafts(db: Db, identity: StaffIdentity, q: Keyword = "", knowledge: Keyword = "", offset: Offset = 0, limit: Limit = 50, library_id: UUID | None = None):
    return queries.drafts(db, identity, q, knowledge, offset, limit, library_id)


@router.get("/drafts/{question_id}", response_model=DraftView)
def draft(db: Db, identity: StaffIdentity, question_id: UUID):
    return queries.draft_view(db, identity, question_id)


@router.post("/drafts", response_model=CommandResult, response_model_exclude_none=True, status_code=201)
def create(db: Db, identity: StaffIdentity, env: Environment, body: QuestionCreate, key: CommandKey):
    return services.create_question(db, identity, body, key, env.budget)


@router.patch("/drafts/{question_id}", response_model=CommandResult, response_model_exclude_none=True)
def change(db: Db, identity: StaffIdentity, env: Environment, question_id: UUID, body: QuestionChange, key: CommandKey):
    return services.change_question(db, identity, question_id, body, key, env.budget)


@router.post("/drafts/{question_id}/discard", response_model=CommandResult, response_model_exclude_none=True)
def discard(db: Db, identity: StaffIdentity, question_id: UUID, body: Revision, key: CommandKey):
    return services.discard_draft(db, identity, question_id, body, key)


@router.patch("/{question_id}/retirement", response_model=CommandResult, response_model_exclude_none=True)
def retire(db: Db, identity: StaffIdentity, question_id: UUID, body: ParentChange, key: CommandKey):
    return lifecycle.change_parent(db, identity, "question", question_id, body, key)


@router.get("/versions", response_model=Page[VersionView])
def versions(db: Db, identity: StaffIdentity, q: Keyword = "", knowledge: Keyword = "", offset: Offset = 0, limit: Limit = 50,
             library_id: UUID | None = None, question_id: UUID | None = None):
    return queries.versions(db, identity, q, knowledge, offset, limit, library_id, question_id)


@router.get("/versions/{version_id}", response_model=VersionView)
def version(db: Db, identity: StaffIdentity, version_id: UUID, library_id: UUID | None = None):
    return queries.version_view(db, identity, version_id, library_id)


@router.post("/drafts/{question_id}/submit", response_model=CommandResult, response_model_exclude_none=True)
def submit(db: Db, identity: StaffIdentity, env: Environment, question_id: UUID, body: Submit, key: CommandKey):
    return services.submit_question(db, identity, question_id, body, key, env.budget)


@router.get("/reviews", response_model=Page[ReviewView])
def reviews(db: Db, identity: StaffIdentity, offset: Offset = 0, limit: Limit = 50, library_id: UUID | None = None,
            state: Literal["submitted", "approved", "rejected"] | None = None):
    return queries.reviews(db, identity, offset, limit, library_id, state)


@router.get("/reviews/{review_id}", response_model=ReviewView)
def review(db: Db, identity: StaffIdentity, review_id: UUID):
    return queries.review_view(db, identity, review_id)


@router.post("/reviews/{review_id}/decision", response_model=CommandResult, response_model_exclude_none=True)
def decide(db: Db, identity: StaffIdentity, env: Environment, review_id: UUID, body: Decision, key: CommandKey):
    return services.decide_question(db, identity, review_id, body, key, env.budget)


@router.post("/reviews/{review_id}/publish", response_model=CommandResult, response_model_exclude_none=True)
def publish(db: Db, identity: StaffIdentity, env: Environment, review_id: UUID, body: Revision, key: CommandKey):
    return services.publish_question(db, identity, review_id, body, key, env.budget)


@router.get("/publications", response_model=Page[PublicationView])
def publications(db: Db, identity: StaffIdentity, library_id: UUID, offset: Offset = 0, limit: Limit = 50):
    return queries.publications(db, identity, library_id, offset, limit)


@router.post("/publications/{publication_id}/retire", response_model=CommandResult, response_model_exclude_none=True)
def unpublish(db: Db, identity: StaffIdentity, publication_id: UUID, body: Revision, key: CommandKey):
    return lifecycle.retire_publication(db, identity, "question", publication_id, body, key)


@router.post("/copies", response_model=CommandResult, response_model_exclude_none=True, status_code=201)
def copy(db: Db, identity: StaffIdentity, env: Environment, body: CopyOrReference, key: CommandKey):
    return services.copy_question(db, identity, body, key, env.budget)


@router.post("/references", response_model=CommandResult, response_model_exclude_none=True, status_code=201)
def reference(db: Db, identity: StaffIdentity, env: Environment, body: CopyOrReference, key: CommandKey):
    return services.reference_question(db, identity, body, key, env.budget)


@router.post("/imports", response_model=transfers.TransferResult, response_model_exclude_none=True, status_code=201)
def create_import(db: Db, identity: StaffIdentity, env: Environment, body: transfers.ImportCreate, key: CommandKey):
    return transfers.create_import(db, identity, body, key, env.budget, env.admission)


@router.get("/imports/{batch_id}", response_model=imports.BatchView)
def import_status(db: Db, identity: StaffIdentity, batch_id: UUID):
    return imports.batch_view(db, identity, batch_id)


@router.get("/imports/{batch_id}/rows", response_model=Page[imports.ImportRowView])
def import_rows(db: Db, identity: StaffIdentity, batch_id: UUID, offset: Offset = 0, limit: Limit = 50):
    return imports.preview_rows(db, identity, batch_id, offset, limit)


@router.post("/imports/{batch_id}/confirm", response_model=transfers.TransferResult, response_model_exclude_none=True)
def confirm_import(db: Db, identity: StaffIdentity, env: Environment, batch_id: UUID, body: imports.ImportConfirm, key: CommandKey):
    return imports.confirm_import(db, identity, batch_id, body, key, env.budget)


@router.get("/imports/{batch_id}/created", response_model=Page[imports.CreatedQuestion])
def import_created(db: Db, identity: StaffIdentity, batch_id: UUID, offset: Offset = 0, limit: Limit = 50):
    return imports.created_questions(db, identity, batch_id, offset, limit)


@router.post("/exports", response_model=transfers.TransferResult, response_model_exclude_none=True, status_code=201)
def create_export(db: Db, identity: StaffIdentity, env: Environment, body: transfers.ExportCreate, key: CommandKey):
    return transfers.create_export(db, identity, body, key, env.budget, env.admission)


@router.get("/tasks/{task_id}", response_model=transfers.TransferView)
def task(db: Db, identity: StaffIdentity, task_id: UUID):
    return transfers.task_view(db, identity, task_id)


@router.post("/tasks/{task_id}/cancel", response_model=transfers.TransferResult, response_model_exclude_none=True)
def cancel(db: Db, identity: StaffIdentity, task_id: UUID, body: transfers.TaskGeneration, key: CommandKey):
    return transfers.cancel_transfer(db, identity, task_id, body, key)


@router.post("/tasks/{task_id}/retry", response_model=transfers.TransferResult, response_model_exclude_none=True)
def retry(db: Db, identity: StaffIdentity, env: Environment, task_id: UUID, body: transfers.TaskGeneration, key: CommandKey):
    return transfers.retry_transfer(db, identity, task_id, body, key, env.budget, env.admission)
