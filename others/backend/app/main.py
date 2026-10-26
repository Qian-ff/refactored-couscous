"""FastAPI template application/operation-ID pattern; frontend served independently."""
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.routing import APIRoute
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, TimeoutError as DatabaseTimeout
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import engine
from app.core.release import BUILD, ROOT, VERSION
from app.core.content_runtime import lifespan
from app.domains.content.routes import router as content_router
from app.domains.content.questions.routes import router as questions_router
from app.domains.content.lessons.routes import router as lessons_router
from app.domains.content.runtime import get_runtime
from app.domains.core.routes import router
from app.domains.core.class_routes import router as class_router
from app.domains.core.import_routes import router as import_router
from app.domains.core.management_routes import router as management_router


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(title=settings.PROJECT_NAME, version=VERSION,
              openapi_url=None if settings.APP_ENV == "production" else "/api/v1/openapi.json",
              generate_unique_id_function=custom_generate_unique_id, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS.split(","),
                   allow_credentials=True, allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"],
                   allow_headers=["Authorization", "Content-Type", "X-Work-Role", "Idempotency-Key", "If-Match"],
                   expose_headers=["Content-Disposition", "Content-Length"])
app.include_router(router, prefix="/api/v1")
app.include_router(questions_router, prefix="/api/v1")
app.include_router(lessons_router, prefix="/api/v1")
app.include_router(management_router, prefix="/api/v1")
app.include_router(class_router, prefix="/api/v1")
app.include_router(import_router, prefix="/api/v1")
app.include_router(content_router, prefix="/api/v1", dependencies=[Depends(get_runtime)])
MIGRATION_HEAD = ScriptDirectory.from_config(Config(str(ROOT / "others/backend/alembic.ini"))).get_current_head()


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, exception):
    # Pydantic's raw errors may include passwords or a whole CSV in input/context.
    details = [{key: value for key, value in error.items() if key in {"type", "loc", "msg"}}
               for error in exception.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(details)})


@app.exception_handler(OperationalError)
@app.exception_handler(DatabaseTimeout)
async def database_unavailable(_request, _exception):
    return JSONResponse(status_code=503, content={"detail": "数据库暂不可用，请稍后重试"})


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        exists = connection.execute(text("SELECT to_regclass('public.alembic_version')")).scalar_one()
        installed = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none() if exists else None
    if installed != MIGRATION_HEAD:
        return JSONResponse(status_code=503, content={"detail": "数据库版本未就绪，请先完成迁移"})
    return {"status": "ok", "database": "postgresql", "contract": VERSION, "migration": installed}


if settings.APP_ENV != "production":
    @app.get("/api/v1/dev/identity", tags=["system"], include_in_schema=False)
    def dev_identity() -> dict[str, str]:
        return BUILD
