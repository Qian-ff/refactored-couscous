"""A-owned metadata import point: new domain tables must be registered with their migration."""
from app.domains.core.models import (College, Course, CourseCatalog, CourseStaff, Enrollment, LoginSession,
                                    Role, RoleGrant, School, User)
from sqlmodel import SQLModel

__all__ = ["SQLModel", "School", "College", "User", "RoleGrant", "Role", "CourseCatalog", "Course", "CourseStaff", "Enrollment", "LoginSession"]
