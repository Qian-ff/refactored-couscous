"""Private controller health/cleanup command. Capability output is not sandbox test evidence."""
import argparse
import asyncio
import hashlib
from dataclasses import asdict
import json
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "others/backend"))
from app.core.content_runner import DockerParseRunner  # noqa: E402


async def main(args):
    runner = DockerParseRunner(json.loads(args.config.read_text()))
    result = {"reachable": True, "capabilities": asdict(await runner.capabilities()), "sandbox_verified": False}
    if not args.cleanup_root:
        reader, writer = await runner._open("capabilities")
        try:
            actual = await runner._response(reader)
            expected = hashlib.sha256((Path(__file__).parent / "control.py").read_bytes()).hexdigest()
            image = json.loads((args.config.parent / "image.json").read_text())["image"]
            if actual.get("controller_sha256") != expected or result["capabilities"]["image_digest"] != image:
                raise RuntimeError("Parser controller source/image differs; preserve and restart the owned service")
        finally:
            writer.close()
    if args.cleanup_root:
        for path in (args.cleanup_root / "journal").glob("*.json"):
            record = json.loads(path.read_text())
            if record.get("released"):
                continue
            execution = UUID(record["execution_id"])
            stopped = await runner.stop(execution)
            if not stopped.stop_confirmed or not await runner.release(execution):
                raise RuntimeError("Execution cleanup was not confirmed")
        result["all_owned_executions_released"] = True
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--cleanup-root", type=Path)
    asyncio.run(main(parser.parse_args()))
