"""Fixed sandbox receiver/CLI wrapper; input stays in the capped tmpfs, never the host."""
import argparse
import asyncio
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import sys

OUTPUT = Path("/output")
MAX_OUTPUT = 16 * 1024 * 1024
SAFE_ERRORS = {"TIMEOUT", "RESOURCE_LIMIT", "CORRUPT_FILE", "INVALID_ENCODING", "UNSUPPORTED_ENCODING",
               "ENCRYPTED_FILE", "NO_TEXT", "UNSUPPORTED_TYPE", "WORKER_INTERRUPTED", "INVALID_RESULT"}


def status(value):
    temporary = OUTPUT / "status.new"
    with temporary.open("w") as handle:
        json.dump(value, handle)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(OUTPUT / "status.json")


def receive(args):
    def expired(_signum, _frame):
        raise TimeoutError()
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(300)
    digest, size = hashlib.sha256(), 0
    maximum = (16 * 1024 * 1024 if args.task_kind == "question_export" else
               (1048576 if args.format == "csv" else 5242880) if args.task_kind == "question_import" else
               1048576 if args.format in {"txt", "text"} else 20 * 1024 * 1024)
    descriptor = os.memfd_create("labconnect-input", os.MFD_ALLOW_SEALING)
    with os.fdopen(os.dup(descriptor), "wb") as output:
        while True:
            prefix = sys.stdin.buffer.read(4)
            if len(prefix) != 4:
                raise ValueError()
            length = struct.unpack(">I", prefix)[0]
            if length > 65536:
                raise ValueError()
            if not length:
                break
            frame = sys.stdin.buffer.read(length)
            if len(frame) != length:
                raise ValueError()
            size += length
            if size > maximum:
                raise ValueError()
            digest.update(frame)
            output.write(frame)
        if not size or digest.hexdigest() != args.sha256:
            raise ValueError()
        output.flush()
        os.fsync(output.fileno())
    fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS,
                fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL)
    with (OUTPUT / "accepted.new").open("x") as accepted:
        receipt = {"kernel_seals": fcntl.fcntl(descriptor, fcntl.F_GET_SEALS),
                   "input_bytes": size, "input_sha256": digest.hexdigest()}
        if args.task_kind != "material_parse":
            work = os.statvfs("/work")
            receipt.update(task_kind=args.task_kind, work_tmpfs_bytes=work.f_frsize * work.f_blocks)
        json.dump(receipt, accepted)
        accepted.flush()
        os.fsync(accepted.fileno())
    (OUTPUT / "accepted.new").replace(OUTPUT / "accepted")
    signal.alarm(0)
    return descriptor


async def consume(stream, maximum, destination=None):
    """Bound actual child output while reading, before either memory or disk can grow."""
    count = 0
    while data := await stream.read(65536):
        count += len(data)
        if count > maximum:
            raise OverflowError()
        if destination:
            destination.write(data)


async def parse(args, descriptor):
    source = "/proc/self/fd/" + str(descriptor)
    command = ([sys.executable, "-m", "content.cli", "--input", source, "--format", args.format, "--encoding", args.encoding]
        if args.task_kind == "material_parse" else
        [sys.executable, "-m", "app.domains.content.questions.transfer_cli", "--input-fd", str(descriptor),
         "--operation", "import" if args.task_kind == "question_import" else "export", "--format", args.format])
    process = await asyncio.create_subprocess_exec(*command,
        pass_fds=(descriptor,),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONPATH": "/parser", "PYTHONDONTWRITEBYTECODE": "1",
             "PYTHONUNBUFFERED": "1", "LANG": "C.UTF-8", "TMPDIR": "/work", "TEMP": "/work", "TMP": "/work"})
    result = OUTPUT / "result.json"

    tasks = []
    try:
        with result.open("xb") as output:
            tasks = [asyncio.create_task(consume(process.stdout, MAX_OUTPUT, output)),
                     asyncio.create_task(consume(process.stderr, 65536)), asyncio.create_task(process.wait())]
            async with asyncio.timeout(60 if args.task_kind == "material_parse" else 30):
                await asyncio.gather(*tasks)
            output.flush()
            os.fsync(output.fileno())
        if process.returncode:
            try:
                failure = json.loads(result.read_bytes()[:4096])["error_code"]
            except (ValueError, KeyError, TypeError):
                failure = "CORRUPT_FILE"
            status({"state": "failed", "error_code": failure if failure in SAFE_ERRORS else "CORRUPT_FILE"})
            result.unlink(missing_ok=True)
            return 1
        status({"state": "succeeded"})
        return 0
    except TimeoutError:
        status({"state": "failed", "error_code": "TIMEOUT"})
        return 1
    except OverflowError:
        status({"state": "failed", "error_code": "RESOURCE_LIMIT"})
        return 1
    finally:
        os.close(descriptor)
        if process.returncode is None:
            process.kill()
            await process.wait()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("format", choices=("pdf", "pptx", "docx", "txt", "text", "csv", "xlsx"))
    parser.add_argument("encoding", choices=("utf-8", "gb18030"))
    parser.add_argument("sha256")
    parser.add_argument("task_kind", nargs="?", default="material_parse", choices=("material_parse", "question_import", "question_export"))
    args = parser.parse_args()
    if (args.task_kind == "material_parse") == (args.format in {"csv", "xlsx"}):
        parser.error("Format does not match the fixed task kind")
    try:
        return asyncio.run(parse(args, receive(args)))
    except TimeoutError:
        status({"state": "failed", "error_code": "TIMEOUT"})
    except Exception:
        status({"state": "failed", "error_code": "CORRUPT_FILE"})
    return 1


if __name__ == "__main__":
    sys.exit(main())
