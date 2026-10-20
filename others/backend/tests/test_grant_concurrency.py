from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.db import engine
from app.core.grants import add_role_grant
from app.models import Role, RoleGrant, School, User


def test_simultaneous_student_and_teacher_grants_are_serialized():
    school = School(code="guard-" + uuid4().hex[:12], name="Concurrency fixture")
    user = User(school_id=school.id, username="fixture", display_name="Fixture", hashed_password="not-a-login")
    school_id, user_id = school.id, user.id
    with Session(engine) as db:
        db.add(school)
        db.flush()
        db.add(user)
        db.commit()
    barrier = Barrier(2)

    def assign(role):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            try:
                add_role_grant(db, user_id=user_id, role=role)
                db.commit()
                return "saved"
            except ValueError:
                db.rollback()
                return "rejected"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(assign, role) for role in (Role.STUDENT, Role.TEACHER)]
            assert sorted(f.result(timeout=15) for f in futures) == ["rejected", "saved"]
        with Session(engine) as db:
            assert len(db.exec(select(RoleGrant).where(RoleGrant.user_id == user_id)).all()) == 1
    finally:
        with Session(engine) as db:
            db.exec(delete(RoleGrant).where(RoleGrant.user_id == user_id))
            db.delete(db.get(User, user_id))
            db.delete(db.get(School, school_id))
            db.commit()
