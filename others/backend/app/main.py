"""FastAPI template application/operation-ID pattern; frontend served independently."""
from fastapi import FastAPI
from fastapi.routing import APIRoute
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, TimeoutError as DatabaseTimeout
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import engine
from app.domains.core.routes import router


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0", openapi_url="/api/v1/openapi.json",
              generate_unique_id_function=custom_generate_unique_id)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS.split(","),
                   allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
app.include_router(router, prefix="/api/v1")


@app.exception_handler(OperationalError)
@app.exception_handler(DatabaseTimeout)
async def database_unavailable(_request, _exception):
    return JSONResponse(status_code=503, content={"detail": "数据库暂不可用，请稍后重试"})


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "postgresql", "contract": "0.1.0"}
