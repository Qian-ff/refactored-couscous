"""Stable, nonblocking kernel file locks. Business cleanup never removes lock files."""
import errno
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID


class FenceUnavailable(RuntimeError):
    def __init__(self):
        super().__init__("UPLOAD_FENCE_UNAVAILABLE")


def _windows_lock(descriptor, unlock=False):
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class Overlapped(ctypes.Structure):
        _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t),
                    ("Offset", wintypes.DWORD), ("OffsetHigh", wintypes.DWORD), ("hEvent", wintypes.HANDLE)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = wintypes.HANDLE(msvcrt.get_osfhandle(descriptor))
    overlap = Overlapped()
    if unlock:
        function = kernel.UnlockFileEx
        function.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(Overlapped)]
        function.restype = wintypes.BOOL
        success = function(handle, 0, 1, 0, ctypes.byref(overlap))
    else:
        function = kernel.LockFileEx
        function.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                             wintypes.DWORD, ctypes.POINTER(Overlapped)]
        function.restype = wintypes.BOOL
        success = function(handle, 3, 0, 1, 0, ctypes.byref(overlap))
    if not success:
        if not unlock and ctypes.get_last_error() == 33:  # ERROR_LOCK_VIOLATION
            return False
        raise FenceUnavailable()
    return True


def _lock(descriptor, unlock=False):
    if os.name == "nt":
        return _windows_lock(descriptor, unlock)
    if os.name == "posix":
        import fcntl
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN if unlock else fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if not unlock and error.errno in {errno.EAGAIN, errno.EACCES}:
                return False
            raise FenceUnavailable() from None
        return True
    raise FenceUnavailable()


class UploadGuard:
    def __init__(self, descriptor, path, root, upload_id):
        self.descriptor, self.path, self.root, self.upload_id = descriptor, path, root, upload_id

    def require(self, root, upload_id):
        if self.descriptor is None or self.root != root or self.upload_id != upload_id:
            raise FenceUnavailable()
        try:
            opened = os.fstat(self.descriptor)
            current = self.path.stat(follow_symlinks=False)
            if (opened.st_ino, opened.st_dev) != (current.st_ino, current.st_dev) or current.st_nlink != 1:
                raise FenceUnavailable()
        except OSError:
            raise FenceUnavailable() from None

    def close(self):
        if self.descriptor is not None:
            descriptor, self.descriptor = self.descriptor, None
            try:
                _lock(descriptor, unlock=True)
            finally:
                os.close(descriptor)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


@dataclass(frozen=True)
class FenceAttempt:
    status: Literal["acquired", "busy", "unavailable"]
    guard: UploadGuard | None = None


class UploadFence:
    def __init__(self, root: Path):
        self.root = root.resolve(strict=True)

    def try_acquire(self, upload_id: UUID):
        descriptor = None
        try:
            if not isinstance(upload_id, UUID):
                raise FenceUnavailable()
            directory = self.root / ".upload-locks"
            directory.mkdir(mode=0o700, exist_ok=True)
            if directory.is_symlink() or (hasattr(directory, "is_junction") and directory.is_junction()):
                raise FenceUnavailable()
            path = directory / (upload_id.hex + ".lock")
            if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
                raise FenceUnavailable()
            descriptor = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
                                 | getattr(os, "O_CLOEXEC", 0), 0o600)
            os.set_inheritable(descriptor, False)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise FenceUnavailable()
            if not _lock(descriptor):
                os.close(descriptor)
                return FenceAttempt("busy")
            guard = UploadGuard(descriptor, path, self.root, upload_id)
            guard.require(self.root, upload_id)
            return FenceAttempt("acquired", guard)
        except (OSError, FenceUnavailable):
            if descriptor is not None:
                os.close(descriptor)
            return FenceAttempt("unavailable")
