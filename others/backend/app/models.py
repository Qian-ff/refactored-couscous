"""A-owned metadata import point: new domain tables must be registered with their migration."""
from app.domains.core.models import (AccountInvitation, College, CommandReceipt, CoreAuditEvent, Course,
                                    CourseCatalog, CourseStaff, Enrollment, EnrollmentRequest, LoginSession,
                                    Major, Role, RoleGrant, School, User)
from sqlmodel import SQLModel
from app.domains.content.models import (Library, Material, ContentUpload, MaterialVersion, SourceChunk,
                                       MaterialReview, MaterialPublication, ContentJob)
from app.domains.content.questions.models import (Question, QuestionDraft, QuestionDraftSource, QuestionVersion,
    QuestionSource, QuestionReview, QuestionPublication, ImportBatch, ImportCreatedQuestion, TransferTask, ExportVersion)
from app.domains.content.lessons.models import (SceneAsset, Lesson, LessonDraft, LessonVersion, LessonDraftSource,
    LessonSource, LessonDraftQuestion, LessonQuestion, LessonDraftQuestionOrigin, LessonQuestionOrigin,
    LessonReview, LessonPublication)

__all__ = ["SQLModel", "School", "College", "Major", "User", "RoleGrant", "Role", "CourseCatalog", "Course",
           "CourseStaff", "Enrollment", "LoginSession", "EnrollmentRequest", "AccountInvitation",
           "CoreAuditEvent", "CommandReceipt", "Library", "Material", "ContentUpload", "MaterialVersion",
           "SourceChunk", "MaterialReview", "MaterialPublication", "ContentJob",
           "Question", "QuestionDraft", "QuestionDraftSource", "QuestionVersion", "QuestionSource",
           "QuestionReview", "QuestionPublication", "ImportBatch", "ImportCreatedQuestion", "TransferTask",
           "ExportVersion", "SceneAsset", "Lesson", "LessonDraft", "LessonVersion", "LessonDraftSource",
           "LessonSource", "LessonDraftQuestion", "LessonQuestion", "LessonDraftQuestionOrigin",
           "LessonQuestionOrigin", "LessonReview", "LessonPublication"]
