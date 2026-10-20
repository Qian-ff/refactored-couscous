"""One checked-in version source; runtime identity is captured at process startup."""
import json
import os
from pathlib import Path

from app.core.provenance import identity
from app.core.config import settings

ROOT = Path(__file__).resolve().parents[4]
VERSION = json.loads((ROOT / "others/config/application.json").read_text(encoding="utf-8"))["version"]


def development_identity() -> dict[str, str]:
    return identity(ROOT, "api")


BUILD = development_identity() if settings.APP_ENV != "production" else {
    "source_sha": os.environ.get("LABCONNECT_SOURCE_SHA", "unrecorded"), "contract": VERSION}
