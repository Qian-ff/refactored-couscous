"""A-owned private storage, non-owner database checks and scheduler lifecycle."""
from contextlib import asynccontextmanager
import asyncio
import json
import os
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.core.content_runner import DockerParseRunner, C1_PROTOCOL
from app.core.db import engine
from app.core.config import settings
from app.domains.content.runtime import ContentRuntime
from app.domains.content.scheduler import ContentScheduler
from app.domains.content.storage import PrivateStorage


def require_runtime_role(connection):
    flags = connection.execute(text("SELECT rolsuper,rolcreaterole,rolcreatedb,rolbypassrls "
                                    "FROM pg_roles WHERE rolname=current_user")).one()
    owner = connection.execute(text("SELECT EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n "
        "ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p') "
        "AND pg_has_role(current_user,c.relowner,'MEMBER'))")).scalar_one()
    tables = connection.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public' "
        "AND tablename IN ('content_library','content_material','content_upload','content_material_version',"
        "'content_source_chunk','content_material_review','content_material_publication','content_job')")).scalar_one()
    if any(flags) or owner or tables != 8:
        raise RuntimeError("CONTENT_DATABASE_ROLE_UNSAFE")


def build_runtime():
    runtime = ContentRuntime(factory=lambda: Session(engine))
    filename = os.environ.get("LABCONNECT_CONTENT_RUNTIME")
    if not filename:
        runtime.unavailable_reason = "CONTENT_UNCONFIGURED"
        return runtime
    try:
        config = json.loads(Path(filename).read_text(encoding="utf-8"))
        if set(config) != {"storage_root", "parser_client"}:
            raise ValueError()
        root, parser = Path(config["storage_root"]), Path(config["parser_client"])
        if not root.is_absolute() or not parser.is_absolute():
            raise ValueError()
        with engine.connect() as connection:
            require_runtime_role(connection)
        runtime.storage = PrivateStorage(root)
        runtime.runner = DockerParseRunner(json.loads(parser.read_text(encoding="utf-8")))
        if runtime.runner.configuration["protocol"] == C1_PROTOCOL:
            with engine.connect() as connection:
                count = connection.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public' AND "
                    "(tablename LIKE 'content_question%' OR tablename LIKE 'content_lesson%' OR tablename='content_scene_asset')")).scalar_one()
                if count != 23:
                    raise RuntimeError("CONTENT_C1_SCHEMA_UNAVAILABLE")
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, HTTPException, SQLAlchemyError):
        runtime.storage = None
        runtime.unavailable_reason = "CONTENT_RUNTIME_UNAVAILABLE"
    return runtime


@asynccontextmanager
async def lifespan(application):
    runtime = build_runtime()
    application.state.content_runtime = runtime
    transfer = None
    if (runtime.storage is not None and isinstance(runtime.runner, DockerParseRunner)
            and runtime.runner.configuration["protocol"] == C1_PROTOCOL):
        from app.core.content_transfer_runtime import TransferDriver, environment
        application.state.c1_environment = lambda: environment(runtime)
        transfer = TransferDriver(runtime)
    stop = asyncio.Event()
    worker = None
    if runtime.storage is not None and settings.APP_ENV != "test":
        scheduler = ContentScheduler(runtime.factory, runtime.storage, runtime.runner, transfer)
        application.state.content_scheduler = scheduler
        worker = asyncio.create_task(scheduler.serve(stop), name="content-scheduler")
    try:
        yield
    finally:
        stop.set()
        if worker:
            # Scheduler cancellation fences old results and awaits actual stop/release confirmation.
            await asyncio.wait_for(worker, 35)
