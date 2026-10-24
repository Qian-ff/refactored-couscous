"""Authenticated bounded streaming; no DB connection is retained during file/network I/O."""
import hashlib
import os
from urllib.parse import quote

from fastapi import HTTPException
from starlette.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.domains.content.access import require_version
from app.domains.content.background_identity import load_identity
from app.domains.content.models import ContentUpload
from app.domains.content.uploads import _io


def allowed(factory, context, version_id, library_id=None):
    with factory() as db:
        identity = load_identity(db, *context)
        version, material, _projection = require_version(db, identity, version_id, library_id)
        if version.input_kind == "text":
            data = version.input_text.encode("utf-8")
            return {"data": data, "bytes": len(data), "hash": version.content_hash,
                    "name": material.title + ".txt", "format": "txt"}
        upload = db.get(ContentUpload, version.upload_id)
        if upload is None or upload.state != "sealed" or upload.expected_hash != version.content_hash:
            raise HTTPException(409, "CORRUPT_FILE")
        return {"key": upload.file_key, "bytes": upload.expected_bytes, "hash": version.content_hash,
                "name": upload.original_name, "format": upload.format}


def verified_file(storage, specification):
    stream = storage.open(specification["key"])
    try:
        if os.fstat(stream.fileno()).st_size != specification["bytes"]:
            raise HTTPException(409, "CORRUPT_FILE")
        digest = hashlib.sha256()
        count = 0
        while data := stream.read(262144):
            count += len(data)
            if count > specification["bytes"]:
                raise HTTPException(409, "CORRUPT_FILE")
            digest.update(data)
        if digest.hexdigest() != specification["hash"]:
            raise HTTPException(409, "CORRUPT_FILE")
        stream.seek(0)
        return stream
    except BaseException:
        stream.close()
        raise


def safe_name(value):
    name = "".join(c for c in value if ord(c) >= 32 and c not in '/\\:<>"|?*').strip(" .")
    return name[:200] or "material"


async def download(runtime, context, version_id, library_id=None):
    specification = await _io(allowed, runtime.factory, context, version_id, library_id)
    stream = None
    if "data" not in specification:
        try:
            stream = await _io(verified_file, runtime.require_storage(), specification,
                               dispose_on_cancel=lambda file: file.close())
        except OSError:
            raise HTTPException(503, "STORAGE_UNAVAILABLE") from None
    elif hashlib.sha256(specification["data"]).hexdigest() != specification["hash"]:
        raise HTTPException(409, "CORRUPT_FILE")

    async def body():
        try:
            offset = 0
            while offset < specification["bytes"]:
                # This reloads login/role/resource access; no session crosses a yield.
                await _io(allowed, runtime.factory, context, version_id, library_id)
                if stream:
                    data = await _io(stream.read, 262144)
                else:
                    data = specification["data"][offset:offset + 262144]
                if not data:
                    return
                offset += len(data)
                yield data
        except (HTTPException, OSError):
            # Content-Length makes a revoked/truncated transfer fail, rather than download an error body as a file.
            return
        finally:
            if stream:
                await _io(stream.close)

    name = quote(safe_name(specification["name"]), safe="")
    headers = {"Content-Disposition": f"attachment; filename=\"material.{specification['format']}\"; filename*=UTF-8''{name}",
               "Content-Length": str(specification["bytes"]), "Cache-Control": "private, no-store",
               "X-Content-Type-Options": "nosniff"}
    return StreamingResponse(body(), media_type="application/octet-stream", headers=headers,
                             background=BackgroundTask(stream.close) if stream else None)
