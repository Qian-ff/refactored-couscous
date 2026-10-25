"""Fixed question/lesson domains share B's resource predicates, never client descriptors."""
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import and_, false, literal, or_, true
from sqlalchemy.orm import aliased
from sqlmodel import select

from app.domains.content.access import columns, descriptor, require_library
from app.domains.content.models import Library
from app.domains.content.questions import models as q
from app.domains.content.lessons import models as lesson
from app.domains.core.models import Course, LoginSession, RoleGrant, School, User
from app.domains.core.policy import resource_access
from app.domains.core.resource_query import read_resource_predicate

Kind = Literal["question", "lesson"]


@dataclass(frozen=True)
class Tables:
    parent: type
    draft: type
    version: type
    review: type
    publication: type
    parent_key: str


DOMAINS = {
    "question": Tables(q.Question, q.QuestionDraft, q.QuestionVersion, q.QuestionReview, q.QuestionPublication, "question_id"),
    "lesson": Tables(lesson.Lesson, lesson.LessonDraft, lesson.LessonVersion, lesson.LessonReview, lesson.LessonPublication, "lesson_id"),
}


def staff(identity):
    if identity.work_role not in {"teacher", "administrator"}:
        raise HTTPException(403, "题库与内容管理仅供当前教职身份使用")


def live_identity(db, identity):
    """Refresh only security records; never expire unrelated B2 pending assessment changes."""
    from app.domains.content.background_identity import load_identity
    user_id, login_id, work_role = identity.user.id, identity.login.id, identity.work_role
    db.flush()
    user = db.get(User, user_id, populate_existing=True)
    db.get(LoginSession, login_id, populate_existing=True)
    if user is not None and user.school_id is not None:
        db.get(School, user.school_id, populate_existing=True)
    db.exec(select(RoleGrant).where(RoleGrant.user_id == user_id).execution_options(populate_existing=True)).all()
    return load_identity(db, user_id, login_id, work_role)


def draft_query(identity, kind: Kind):
    t = DOMAINS[kind]
    allowed = false() if identity.work_role not in {"teacher", "administrator"} else read_resource_predicate(
        identity, columns(Library, creator_id=t.parent.creator_id, published=false()))
    return select(t.draft).join(t.parent, t.parent.id == getattr(t.draft, t.parent_key)).join(
        Library, Library.id == t.parent.library_id).where(Library.active.is_(True), allowed)


def applies_to_course(target, course):
    return or_(target.scope == "platform_public", and_(target.school_id == course.school_id, or_(
        target.scope == "school",
        and_(target.scope == "college", target.college_id == course.college_id),
        and_(target.scope == "catalog", target.catalog_id == course.catalog_id),
        and_(target.scope == "course", target.course_id == course.id))))


def covers_library(published, requested):
    """A college grant does not cover an entire cross-college catalog."""
    return or_(published.scope == "platform_public", and_(published.school_id == requested.school_id, or_(
        and_(published.scope == "school", literal(requested.scope != "platform_public")),
        and_(published.scope == "college", literal(requested.scope in {"college", "course"}),
             published.college_id == requested.college_id),
        and_(published.scope == "catalog", literal(requested.scope in {"catalog", "course"}),
             published.catalog_id == requested.catalog_id),
        and_(published.scope == "course", literal(requested.scope == "course"), published.course_id == requested.course_id))))


def version_query(identity, kind: Kind, library_id=None, *, published_only=False, course=None, target_library=None):
    t = DOMAINS[kind]
    if not published_only and (course is not None or target_library is not None):
        raise ValueError("目标适用性筛选只用于已发布版本")
    if identity.work_role not in {"teacher", "administrator"}:
        return select(t.version).where(false())
    target = aliased(Library)
    publication = select(t.publication.id).join(t.review, t.review.id == t.publication.review_id).join(
        target, target.id == t.publication.target_library_id).where(
        t.publication.version_id == t.version.id, t.publication.active.is_(True), target.active.is_(True),
        t.review.state == "approved", t.review.version_id == t.version.id,
        t.review.target_library_id == target.id,
        target.id == library_id if library_id else true(),
        applies_to_course(target, course) if course is not None else true(),
        covers_library(target, target_library) if target_library is not None else true(),
        target.audience == "all" if course is not None and kind == "lesson" else true(),
        # Published reads do not need draft ownership; an outer creator column would
        # become an unrelated FROM inside the policy's nested catalog EXISTS.
        read_resource_predicate(identity, columns(target, creator_id=literal(None), published=true())),
    ).correlate(t.version, t.parent).exists()
    allowed = publication
    if not published_only:
        source = and_(Library.active.is_(True), Library.id == library_id if library_id else true(),
                      read_resource_predicate(identity, columns(Library, creator_id=t.parent.creator_id, published=false())))
        review_target = aliased(Library)
        reviewing = select(t.review.id).join(review_target, review_target.id == t.review.target_library_id).where(
            t.review.version_id == t.version.id, t.review.state.in_(["submitted", "approved"]),
            review_target.active.is_(True), review_target.id == library_id if library_id else true(),
            read_resource_predicate(identity, columns(review_target, creator_id=literal(None), published=false())),
        ).correlate(t.version).exists()
        allowed = or_(source, publication, reviewing)
    return select(t.version).join(t.parent, t.parent.id == getattr(t.version, t.parent_key)).join(
        Library, Library.id == t.parent.library_id).where(allowed)


def locked_draft(db, kind: Kind, parent_id):
    """Low-level row lock after command authorization; draft PKs are their parent keys."""
    t = DOMAINS[kind]
    row = db.exec(select(t.draft).where(getattr(t.draft, t.parent_key) == parent_id).with_for_update()
                  .execution_options(populate_existing=True)).first()
    if row is None:
        raise HTTPException(403, "对象不存在或无权操作")
    return row


def require_draft(db, identity, kind: Kind, parent_id, *, edit=False, allow_retired=False):
    staff(identity)
    t = DOMAINS[kind]
    row = db.exec(draft_query(identity, kind).where(getattr(t.draft, t.parent_key) == parent_id)
                  .execution_options(populate_existing=True)).first()
    if row is None:
        raise HTTPException(403, "草稿不存在或无权访问")
    parent = db.get(t.parent, parent_id, populate_existing=True)
    library = db.get(Library, parent.library_id, populate_existing=True)
    access = resource_access(db, identity, descriptor(library, creator_id=parent.creator_id))
    if edit and (not access.read or not (access.review or (access.submit and parent.creator_id == identity.user.id))
                 or (parent.retired and not allow_retired)):
        raise HTTPException(403, "无权修改草稿或主记录已停用")
    return row, parent, library


def require_parent(db, identity, kind: Kind, parent_id, *, edit=False, allow_retired=False):
    staff(identity)
    parent = db.get(DOMAINS[kind].parent, parent_id, populate_existing=True)
    if parent is None:
        raise HTTPException(403, "内容不存在或无权访问")
    library = db.get(Library, parent.library_id, populate_existing=True)
    access = resource_access(db, identity, descriptor(library, creator_id=parent.creator_id))
    if not library.active or not access.read or (edit and (not (
            access.review or (access.submit and parent.creator_id == identity.user.id))
            or (parent.retired and not allow_retired))):
        raise HTTPException(403, "无权访问或修改源范围内容")
    return parent, library


def require_version(db, identity, kind: Kind, version_id, library_id=None, *, published_only=False, course=None, target_library=None):
    staff(identity)
    t = DOMAINS[kind]
    row = db.exec(version_query(identity, kind, library_id, published_only=published_only, course=course, target_library=target_library).where(
        t.version.id == version_id).execution_options(populate_existing=True)).first()
    if row is None:
        raise HTTPException(403, "版本不存在或当前无权访问")
    parent = db.get(t.parent, getattr(row, t.parent_key), populate_existing=True)
    source = db.get(Library, parent.library_id, populate_existing=True)
    if not published_only and (library_id is None or library_id == source.id) and source.active and resource_access(
            db, identity, descriptor(source, creator_id=parent.creator_id)).read:
        return row, parent, source
    bindings = db.exec(select(t.publication, t.review, Library).join(
        t.review, t.review.id == t.publication.review_id).join(Library, Library.id == t.publication.target_library_id).where(
            t.publication.version_id == version_id, t.publication.active.is_(True),
            t.review.state == "approved", t.review.version_id == version_id,
            t.review.target_library_id == t.publication.target_library_id, Library.active.is_(True),
            Library.id == library_id if library_id else true(),
            applies_to_course(Library, course) if course is not None else true(),
            covers_library(Library, target_library) if target_library is not None else true(),
            Library.audience == "all" if course is not None and kind == "lesson" else true(),
        ).order_by(t.publication.id).execution_options(populate_existing=True)).all()
    for _binding, _review, target in bindings:
        if resource_access(db, identity, descriptor(target, creator_id=parent.creator_id, published=True)).read:
            return row, parent, target
    if not published_only:
        reviews = db.exec(select(t.review, Library).join(Library, Library.id == t.review.target_library_id).where(
            t.review.version_id == version_id, t.review.state.in_(["submitted", "approved"]), Library.active.is_(True),
            Library.id == library_id if library_id else true()).order_by(t.review.id)
            .execution_options(populate_existing=True)).all()
        for _review, target in reviews:
            if resource_access(db, identity, descriptor(target)).review:
                return row, parent, target
    raise HTTPException(403, "版本授权已改变")


def require_teaching_course(db, identity, course_id):
    staff(identity)
    course = db.get(Course, course_id, populate_existing=True)
    if course is None or course.archived:
        raise HTTPException(403, "教学班不存在或已归档")
    school = db.get(School, course.school_id, populate_existing=True)
    if school is None or not school.is_active:
        raise HTTPException(403, "教学班所属学校已停用")
    proposed = Library(scope="course", school_id=course.school_id, college_id=course.college_id,
                       catalog_id=course.catalog_id, course_id=course.id, audience="all", title="", creator_id=identity.user.id)
    if not resource_access(db, identity, descriptor(proposed)).review:
        raise HTTPException(403, "无权在该班发布学习任务")
    return course


def review_manager(db, identity, kind: Kind, review_id):
    staff(identity)
    row = db.get(DOMAINS[kind].review, review_id, populate_existing=True)
    if row is None:
        raise HTTPException(403, "审核记录不存在或无权访问")
    db.get(Library, row.target_library_id, populate_existing=True)
    return row, require_library(db, identity, row.target_library_id, "review")


def has_retained_public_grant(db, kind, version_id):
    """Immutable proof for an existing licensed copy; never authorizes selecting a retired publication."""
    t = DOMAINS[kind]
    return db.exec(select(t.publication.id).join(t.review, t.review.id == t.publication.review_id).join(
        Library, Library.id == t.publication.target_library_id).where(t.publication.version_id == version_id,
        t.review.version_id == version_id, t.review.target_library_id == Library.id,
        t.review.state == "approved", Library.scope == "platform_public").limit(1)).first() is not None


def public_source_ids(db, kind, copied_from):
    """Only retain exact private FK locators already contained in an approved public ancestor.

    This neither publishes a changed body nor grants access to the original material.
    Writers separately validate the complete immutable ancestor chain and its license.
    """
    t = DOMAINS[kind]
    source_type = q.QuestionSource if kind == "question" else lesson.LessonSource
    source_key = "question_version_id" if kind == "question" else "lesson_version_id"
    seen, result = set(), set()
    while copied_from is not None:
        if copied_from in seen or len(seen) >= 32:
            raise HTTPException(409, "复制来源链无效或超过32层")
        seen.add(copied_from)
        version = db.get(t.version, copied_from)
        if version is None:
            raise HTTPException(409, "复制来源固定版本不可用")
        if has_retained_public_grant(db, kind, copied_from):
            rows = db.exec(select(source_type).where(getattr(source_type, source_key) == copied_from)).all()
            result.update((row.material_version_id, row.chunk_id) for row in rows)
        copied_from = version.copied_from_version_id
    return frozenset(result)


def copy_source(db, identity, kind, version_id, target):
    version, parent, projection = require_version(db, identity, kind, version_id, published_only=True)
    source = db.get(Library, parent.library_id, populate_existing=True)
    if source.school_id is not None and target.school_id is not None and source.school_id != target.school_id:
        # A new cross-school selection requires a currently active public grant, not merely a license checkbox.
        version, parent, projection = require_version(db, identity, kind, version_id,
                                                      published_only=True, target_library=target)
        if projection.scope != "platform_public":
            raise HTTPException(403, "跨校复用须经有效公共发布授权")
    return version, parent, projection
