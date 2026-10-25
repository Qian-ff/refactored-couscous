"""Real timeout and controller-crash recovery of this installation's owned Docker unit."""
import argparse
import asyncio
from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess

from verify import ROOT, completed, denied, docker, source, task
from app.core.content_runner import DockerParseRunner


def slow_pdf():
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    writer = PdfWriter()
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    for _ in range(500):
        page = writer.add_blank_page(width=300, height=300)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        contents = DecodedStreamObject()
        contents.set_data(b"BT /F1 12 Tf 20 200 Td " + b"(x) Tj " * 3000 + b"ET")
        page[NameObject("/Contents")] = contents
    output = BytesIO()
    writer.write(output)
    result = output.getvalue()
    assert 0 < len(result) <= 20 * 1024 * 1024
    return result


async def launcher(script, report_root, *arguments):
    shell = shutil.which("pwsh")
    assert shell
    with (report_root / (script.name + ".fault.stdout.txt")).open("wb") as stdout, \
            (report_root / (script.name + ".fault.stderr.txt")).open("wb") as stderr:
        result = await asyncio.to_thread(subprocess.run, [shell, "-NoProfile", "-File", str(script), *arguments],
                                         cwd=ROOT, stdout=stdout, stderr=stderr, timeout=60)
    assert result.returncode == 0, "Owned fault/recovery launcher failed"


async def main(args):
    runtime = ROOT / "others/runtime/c02-public"
    config = json.loads((runtime / "control.json").read_text())
    runner = DockerParseRunner(json.loads((runtime / "parser-client.json").read_text()))
    report = {"image": config["image"], "scope": "real-owned-execution-timeout-and-control-crash"}
    report_root = args.report.parent
    print("faults: pause an actual parser, enforce the real 60-second deadline", flush=True)
    data = slow_pdf()
    specification = task(data, "pdf")
    name = "labconnect-parse-" + config["instance"] + "-" + specification.execution_id.hex
    paused = False
    try:
        started = await runner.start(specification, source(data))
        assert started.state == "running", "Timeout fixture finished before fault injection"
        await docker("pause", name)
        paused = True
        for _second in range(61):
            await asyncio.sleep(1)
        await docker("unpause", name)
        paused = False
        state = await completed(runner, specification.execution_id)
        assert state.stop_confirmed and state.state in {"failed", "stopped"} and state.error_code == "TIMEOUT"
        report["deadline"] = {"waited_seconds": 61, "stop_confirmed": True, "error_code": state.error_code,
                              "input_bytes": len(data)}
    finally:
        if paused:
            await docker("unpause", name)
        await runner.stop(specification.execution_id)
        assert await runner.release(specification.execution_id)
    print("faults: terminate only the verified controller during actual input receipt", flush=True)
    waiting, resume = asyncio.Event(), asyncio.Event()
    data = b"Interrupted synthetic input"
    specification = task(data)
    async def held_source():
        waiting.set()
        yield data
        await resume.wait()
    pending = asyncio.create_task(runner.start(specification, held_source()))
    await asyncio.wait_for(waiting.wait(), 15)
    await launcher(Path(__file__).parent / "crash_for_acceptance.ps1", report_root,
                   "-Marker", str(runtime / "control-process.json"))
    resume.set()
    await denied(pending)
    # Authoritative socket absence, not a lock file or intent, permits the owned restart.
    for _attempt in range(50):
        try:
            _reader, writer = await asyncio.open_connection("127.0.0.1", 18767)
            writer.close()
        except OSError:
            break
        await asyncio.sleep(.1)
    else:
        raise AssertionError("Old controller is still listening; not restarted")
    await launcher(ROOT / "others/scripts/Start-ContentParser.ps1", report_root)
    recovered = await runner.inspect(specification.execution_id)
    assert recovered.stop_confirmed and recovered.state == "stopped"
    assert await runner.release(specification.execution_id)
    await denied(runner.start(specification, source(data)))
    assert await runner.release(specification.execution_id)
    report["crash_recovery"] = {"old_execution_stop_confirmed": True, "released": True, "late_start_rejected": True}
    fresh = task(b"Recovered parser")
    try:
        await runner.start(fresh, source(b"Recovered parser"))
        assert (await completed(runner, fresh.execution_id)).state == "succeeded"
        assert json.loads(await runner.result(fresh.execution_id))["chunks"]
        report["new_execution_after_recovery"] = True
    finally:
        await runner.stop(fresh.execution_id)
        assert await runner.release(fresh.execution_id)
    report["passed"] = True
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
