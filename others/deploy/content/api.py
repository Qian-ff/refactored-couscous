"""Run the candidate API with runtime-only credentials, without loading main's owner .env."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--profile", choices=("c02", "c1"), default="c02")
    parser.add_argument("--seed-test", action="store_true")
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--port", type=int, default=8002, choices=(8002,))
    args = parser.parse_args()
    if args.profile == "c1" and args.config.resolve() != (ROOT / "others/runtime/c1-public/api-runtime.json").resolve():
        raise RuntimeError("Use the fixed ignored C1 API configuration")
    configuration = json.loads(args.config.read_text(encoding="utf-8"))
    if set(configuration) != {"database_url", "secret_key", "content_runtime", "synthetic_password"}:
        raise RuntimeError("Use the separate C02 API runtime configuration, never an owner configuration")
    # No inherited database, provider, cloud, control-server or management credentials.
    allowed = {key: value for key, value in os.environ.items() if key.upper() in
               {"PATH", "SYSTEMROOT", "WINDIR", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP"}}
    os.environ.clear()
    os.environ.update(allowed)
    os.environ.update(DATABASE_URL=configuration["database_url"], SECRET_KEY=configuration["secret_key"],
                      LABCONNECT_CONTENT_RUNTIME=configuration["content_runtime"], APP_ENV="development")
    sys.path.insert(0, str(ROOT / "others/backend"))
    sys.path.insert(0, str(ROOT / "others/scripts"))
    if args.profile == "c1":
        from c1_candidate_env import fingerprint, paths, validate
    else:
        from content_candidate_env import fingerprint, paths, validate
    primary = validate()
    project, environment, _python = paths("backend")
    if json.loads((environment / ("c1-inputs.json" if args.profile == "c1" else "c02-inputs.json")).read_text())["fingerprint"] != fingerprint(project):
        raise RuntimeError("Candidate backend dependencies changed; prepare before starting API")
    os.environ["LABCONNECT_SHARED_ROOT"] = str(primary)
    from app.core.db import engine
    from app.core.content_runtime import require_runtime_role
    from sqlalchemy.engine import make_url
    if args.profile == "c1":
        url = make_url(configuration["database_url"])
        if url.host not in {"127.0.0.1", "localhost"} or url.database != "safelab_c1_test":
            raise RuntimeError("C1 candidate API is restricted to the dedicated local test profile")
    with engine.connect() as connection:
        require_runtime_role(connection)
    if args.seed_test:
        url = make_url(configuration["database_url"])
        if url.host not in {"127.0.0.1", "localhost"} or url.database != ("safelab_c1_test" if args.profile == "c1" else "safelab_c02_test"):
            raise RuntimeError("Synthetic seeding is restricted to the dedicated local C02 test database")
        from app.seed import seed
        from sqlmodel import Session
        with Session(engine) as session:
            seed(session, configuration["synthetic_password"])
            session.commit()
    import uvicorn
    async def serve():
        server = uvicorn.Server(uvicorn.Config("app.main:app", host="127.0.0.1", port=args.port))
        running = asyncio.create_task(server.serve())
        while not server.started and not running.done():
            await asyncio.sleep(.1)
        if running.done():
            await running
            raise RuntimeError("Candidate API did not bind its assigned port")
        checked = await asyncio.to_thread(subprocess.run, [sys.executable, str(ROOT / "others/scripts/provenance.py"),
            "--surface", "api", "--verify-url", "http://127.0.0.1:8002"], cwd=ROOT, timeout=10)
        if checked.returncode:
            server.should_exit = True
            await running
            raise RuntimeError("API source verification failed")
        print("C02 real API: http://127.0.0.1:8002/docs ; material UI is a separate D1 delivery", flush=True)
        if args.open_browser:
            import webbrowser
            await asyncio.to_thread(webbrowser.open, "http://127.0.0.1:8002/docs")
        await running
    asyncio.run(serve())


if __name__ == "__main__":
    main()
