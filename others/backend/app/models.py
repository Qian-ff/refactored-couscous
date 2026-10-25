"""A-owned metadata import point: new domain tables must be registered with their migration."""
from app.domains.core.models import (AccountInvitation, College, CommandReceipt, CoreAuditEvent, Course,
                                    CourseCatalog, CourseStaff, Enrollment, EnrollmentRequest, LoginSession,
                                    Major, Role, RoleGrant, School, User)
from sqlmodel import SQLModel
from app.domains.content.models import (Library, Material, ContentUpload, MaterialVersion, SourceChunk,
                                       MaterialReview, MaterialPublication, ContentJob)

__all__ = ["SQLModel", "School", "College", "Major", "User", "RoleGrant", "Role", "CourseCatalog", "Course",
           "CourseStaff", "Enrollment", "LoginSession", "EnrollmentRequest", "AccountInvitation",
           "CoreAuditEvent", "CommandReceipt", "Library", "Material", "ContentUpload", "MaterialVersion",
           "SourceChunk", "MaterialReview", "MaterialPublication", "ContentJob"]
