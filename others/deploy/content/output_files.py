"""Read untrusted parser outputs through pinned, non-following OS handles."""
from contextlib import ExitStack
import os
from pathlib import Path
import stat
from uuid import UUID


class UnsafeOutput(Exception):
    pass


def _windows_open(path, directory):
    import ctypes
    from ctypes import wintypes
    import msvcrt

    class Information(ctypes.Structure):
        _fields_ = [("attributes", wintypes.DWORD), ("created", wintypes.FILETIME),
                    ("accessed", wintypes.FILETIME), ("written", wintypes.FILETIME),
                    ("volume", wintypes.DWORD), ("size_high", wintypes.DWORD), ("size_low", wintypes.DWORD),
                    ("links", wintypes.DWORD), ("index_high", wintypes.DWORD), ("index_low", wintypes.DWORD)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                  wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetFileType.argtypes = [wintypes.HANDLE]
    kernel.GetFileType.restype = wintypes.DWORD
    kernel.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.POINTER(Information)]
    kernel.GetFileInformationByHandle.restype = wintypes.BOOL
    # No DELETE sharing pins the directory/name. A leaf also denies concurrent writers.
    handle = kernel.CreateFileW(str(path), 0x80000000, 3 if directory else 1, None, 3,
                                0x00200000 | (0x02000000 if directory else 0), None)
    if handle == wintypes.HANDLE(-1).value:
        code = ctypes.get_last_error()
        if code in {2, 3}:
            raise FileNotFoundError(str(path))
        raise UnsafeOutput() from None
    try:
        info = Information()
        if (not kernel.GetFileInformationByHandle(handle, ctypes.byref(info))
                or kernel.GetFileType(handle) != 1 or info.attributes & 0x400
                or bool(info.attributes & 0x10) != directory or (not directory and info.links != 1)):
            raise UnsafeOutput()
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        handle = None  # Descriptor owns the exact validated native handle now.
        return descriptor
    finally:
        if handle is not None:
            kernel.CloseHandle(handle)


def read_output(tasks: Path, execution_id: str, name: str, maximum: int, *, missing_ok=False):
    """No path-based read/stat after opening; reject unsafe objects before reading any bytes."""
    if str(UUID(execution_id)) != execution_id or name not in {"status.json", "result.json", "accepted"}:
        raise UnsafeOutput()
    try:
        with ExitStack() as stack:
            if os.name == "nt":
                for directory in (tasks, tasks / execution_id):
                    descriptor = _windows_open(directory, True)
                    stack.callback(os.close, descriptor)
                descriptor = _windows_open(tasks / execution_id / name, False)
            elif os.name == "posix":
                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
                parent = os.open(tasks, flags)
                stack.callback(os.close, parent)
                directory = os.open(execution_id, flags, dir_fd=parent)
                stack.callback(os.close, directory)
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory)
            else:
                raise UnsafeOutput()
            with os.fdopen(descriptor, "rb") as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= maximum:
                    raise UnsafeOutput()
                data = stream.read(maximum + 1)
                after = os.fstat(stream.fileno())
                fields = ("st_dev", "st_ino", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
                if (len(data) != before.st_size or len(data) > maximum
                        or any(getattr(before, field) != getattr(after, field) for field in fields)):
                    raise UnsafeOutput()
                return data
    except FileNotFoundError:
        if missing_ok:
            return None
        raise UnsafeOutput() from None
    except (OSError, ValueError) as error:
        raise UnsafeOutput() from error
