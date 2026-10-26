"""Source retirement and target publication retirement have separate authorities."""
from fastapi import HTTPException

from app.domains.content.access import require_library
from app.domains.content.models import now
from app.domains.content.questions.policy import DOMAINS, require_parent, staff
from app.domains.content.services import execute_command, locked, require_key
from app.domains.core.commands import check_revision, touch


def change_parent(db, identity, kind, parent_id, request, key):
    staff(identity)
    require_key(key)
    _parent, initial = require_parent(db, identity, kind, parent_id, edit=True, allow_retired=True)

    def authorize():
        parent, _library = require_parent(db, identity, kind, parent_id, edit=True, allow_retired=True)
        require_library(db, identity, parent.library_id, "review")

    def action():
        parent = locked(db, DOMAINS[kind].parent, parent_id)
        check_revision(parent, request.revision)
        parent.retired = request.retired
        touch(parent)
        db.add(parent)
        return {kind + "_id": str(parent.id), "revision": parent.revision, "retired": parent.retired}

    return execute_command(db, identity, initial.school_id, f"content.{kind}.retire", key,
                           {"id": str(parent_id), **request.model_dump()}, action, authorize)


def retire_publication(db, identity, kind, publication_id, request, key):
    staff(identity)
    require_key(key)
    publication_type = DOMAINS[kind].publication
    original = db.get(publication_type, publication_id)
    if original is None:
        raise HTTPException(403, "发布记录不存在或无权操作")
    target_id = original.target_library_id
    initial = require_library(db, identity, target_id, "review")

    def action():
        publication = locked(db, publication_type, publication_id)
        check_revision(publication, request.revision)
        if not publication.active:
            raise HTTPException(409, "发布已停用，重新开放须新增审核记录")
        publication.active, publication.retired_at = False, now()
        touch(publication)
        db.add(publication)
        return {"publication_id": str(publication.id), "revision": publication.revision, "active": False}

    return execute_command(db, identity, initial.school_id, f"content.{kind}.unpublish", key,
                           {"id": str(publication_id), **request.model_dump()}, action,
                           lambda: require_library(db, identity, target_id, "review"))
