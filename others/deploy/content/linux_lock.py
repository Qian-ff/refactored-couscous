"""Run the exact UploadFence implementation against a disposable Linux Docker data volume."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from stress import ROOT, command, probe


async def main(args):
    image = json.loads((ROOT / "others/runtime/c02-public/image.json").read_text())["image"]
    volume, owner = "labconnect-c02-lock-" + uuid4().hex, uuid4().hex
    source = ROOT / "others/backend/app/domains/content/upload_fence.py"
    await command("volume", "create", "--label", "labconnect.c02.acceptance=" + owner, volume)
    try:
        # Trusted setup changes only the empty volume created above. Parsing never receives CHOWN.
        await command("run", "--rm", "--user=0:0", "--network=none", "--read-only", "--cap-drop=ALL", "--cap-add=CHOWN",
            "--security-opt=no-new-privileges:true", "--memory=67108864", "--memory-swap=67108864",
            "--cpus=1", "--pids-limit=64", "--mount", "type=volume,source=" + volume + ",target=/shared",
            "--entrypoint", "python", image, "-c", "import os;os.chmod('/shared',0o700);os.chown('/shared',65532,65532)")
        _code, raw, _metadata = await probe(image, r'''
import json,subprocess,sys
from pathlib import Path
from uuid import UUID
sys.path.insert(0,'/probe')
from fence import UploadFence
upload=UUID('cb11b16e-38c7-4db4-b477-b8598365c870')
first=UploadFence(Path('/shared')).try_acquire(upload)
assert first.status=='acquired'
files=list(Path('/shared').rglob('*.lock'))
assert len(files)==1
inode=files[0].stat().st_ino
code="import sys;from pathlib import Path;from uuid import UUID;sys.path.insert(0,'/probe');from fence import UploadFence;r=UploadFence(Path('/shared')).try_acquire(UUID('cb11b16e-38c7-4db4-b477-b8598365c870'));print(r.status);r.guard.close() if r.guard else None"
blocked=subprocess.run([sys.executable,'-c',code],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
assert blocked.stdout.strip()==b'busy'
first.guard.close()
released=subprocess.run([sys.executable,'-c',code],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
assert released.stdout.strip()==b'acquired'
assert files[0].exists() and files[0].stat().st_ino==inode
print(json.dumps({'linux_flock':True,'separate_process_exclusion':True,'stable_lock_inode':True}))
''', fixture_mounts=("type=volume,source=" + volume + ",target=/shared",
                    "type=bind,source=" + str(source) + ",target=/probe/fence.py,readonly"))
        report = {"image": image, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "scope": "real-linux-docker-data-volume", **json.loads(raw)}
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report))
    finally:
        _code, raw = await command("volume", "inspect", "--format", "{{json .Labels}}", volume)
        assert json.loads(raw)["labconnect.c02.acceptance"] == owner
        await command("volume", "rm", volume)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    asyncio.run(main(parser.parse_args()))
