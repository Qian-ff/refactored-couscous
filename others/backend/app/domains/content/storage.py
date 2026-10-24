"""Private, opaque file keys only. A configures and protects the root directory."""
import os
import re
import shutil
from pathlib import Path

from fastapi import HTTPException
from uuid import UUID

from app.domains.content.upload_fence import UploadFence

KEY = re.compile(r"[0-9a-f]{32}\.(?:part|blob)\Z")


class PrivateStorage:
    def __init__(self, root: Path):
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise HTTPException(503, "STORAGE_UNAVAILABLE")
        self.fence = UploadFence(self.root)

    def path(self, key: str):
        if not KEY.fullmatch(key):
            raise HTTPException(400, "非法资料标识")
        path = self.root / key
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise HTTPException(503, "STORAGE_UNAVAILABLE")
        return path

    def create(self, key: str, guard):
        path = self.path(key)
        guard.require(self.root, UUID(hex=key[:32]))
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        return os.fdopen(os.open(path, flags, 0o600), "wb")

    def open(self, key: str):
        path = self.path(key)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        descriptor = os.open(path, flags)
        try:
            import stat
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise HTTPException(503, "STORAGE_UNAVAILABLE")
            return os.fdopen(descriptor, "rb")
        except BaseException:
            os.close(descriptor)
            raise

    def seal(self, temporary_key: str, final_key: str, guard):
        # Atomic no-replace publication on the same private volume; recovery also checks .part.
        temporary, final = self.path(temporary_key), self.path(final_key)
        guard.require(self.root, UUID(hex=temporary_key[:32]))
        guard.require(self.root, UUID(hex=final_key[:32]))
        os.link(temporary, final, follow_symlinks=False)
        temporary.unlink()
        if os.name == "posix":
            directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)

    def flush(self, file, guard):
        guard.require(self.root, guard.upload_id)
        file.flush()
        os.fsync(file.fileno())

    def remove_unreferenced(self, key: str, guard):
        # Callers must first prove no version references this upload and its writer has stopped.
        path = self.path(key)
        guard.require(self.root, UUID(hex=key[:32]))
        path.unlink(missing_ok=True)

    def free_bytes(self):
        return shutil.disk_usage(self.root).free
