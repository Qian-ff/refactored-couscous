"""Real kernel/output stress in disposable, labeled containers; never a ParseRunner fallback."""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
MiB = 1024 * 1024


async def command(*arguments, timeout=25, expected=0):
    process = await asyncio.create_subprocess_exec("docker", *arguments,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    async def read(stream):
        value = await stream.read(65537)
        if len(value) > 65536:
            raise RuntimeError("Trusted verification output exceeded its budget")
        return value
    try:
        stdout, stderr, code = await asyncio.wait_for(asyncio.gather(read(process.stdout), read(process.stderr),
                                                                    process.wait()), timeout)
        if expected is not None and code != expected:
            raise RuntimeError("Docker stress command failed: " + stderr.decode(errors="replace")[:500])
        return code, stdout
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


async def probe(image, code, *, expected=0, fixture_mounts=()):
    name = "labconnect-c02-stress-" + uuid4().hex
    owner = uuid4().hex
    arguments = ["create", "--name", name, "--label", "labconnect.c02.acceptance=" + owner,
        "--network=none", "--read-only", "--user=65532:65532", "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true", "--memory=402653184", "--memory-swap=402653184",
        "--cpus=1", "--pids-limit=64", "--log-driver=none", "--tmpfs",
        "/work:rw,noexec,nosuid,nodev,size=46137344,uid=65532,gid=65532,mode=0700",
        "--entrypoint", "python"]
    for mount in fixture_mounts:
        arguments += ["--mount", mount]
    arguments += [image, "-c", code]
    await command(*arguments)
    try:
        # Attach output is not retained by Docker's log driver. Test programs emit only bounded metadata.
        exit_code, raw = await command("start", "--attach", name, expected=expected)
        _code, metadata = await command("inspect", "--type", "container", "--format", "{{json .}}", name)
        inspected = json.loads(metadata)
        assert inspected["Config"]["Labels"]["labconnect.c02.acceptance"] == owner
        assert inspected["Image"] == image and not inspected["State"]["Running"]
        return exit_code, raw, inspected
    finally:
        _code, metadata = await command("inspect", "--type", "container", "--format", "{{json .Config.Labels}}", name)
        assert json.loads(metadata)["labconnect.c02.acceptance"] == owner
        await command("stop", "--time", "1", name)
        await command("rm", name)


async def main(args):
    image = json.loads((ROOT / "others/runtime/c02-public/image.json").read_text())["image"]
    report = {"image": image, "scope": "real-disposable-container-kernel-and-output-stress"}
    print("stress: actual 384MiB/no-swap OOM", flush=True)
    exit_code, _raw, inspected = await probe(image, "data=bytearray(700*1024*1024)", expected=137)
    assert exit_code == 137 and inspected["State"]["OOMKilled"]
    report["memory_oom_killed"] = True
    print("stress: actual PID bound", flush=True)
    _code, raw, _inspected = await probe(image, r'''
import errno,json,os,signal,time
children=[]
try:
    for attempt in range(100):
        try: child=os.fork()
        except OSError as error:
            assert error.errno==errno.EAGAIN
            print(json.dumps({'fork_denied':True,'children':len(children)}),flush=True)
            break
        if child==0:
            time.sleep(20)
            os._exit(0)
        children.append(child)
    else: raise AssertionError('PID limit did not stop forks')
finally:
    for child in children: os.kill(child,signal.SIGKILL)
    for child in children: os.waitpid(child,0)
''')
    pids = json.loads(raw)
    assert pids["fork_denied"] and pids["children"] < 64
    report["pids"] = pids
    print("stress: sealed input plus capped temporary memory", flush=True)
    _code, raw, _inspected = await probe(image, r'''
import errno,fcntl,json,os
descriptor=os.memfd_create('verified-input',os.MFD_ALLOW_SEALING)
for _ in range(20): os.write(descriptor,b'x'*(1024*1024))
seals=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL
fcntl.fcntl(descriptor,fcntl.F_ADD_SEALS,seals)
for operation in (lambda:os.write(descriptor,b'x'),lambda:os.ftruncate(descriptor,0)):
    try: operation()
    except OSError as error: assert error.errno==errno.EPERM
    else: raise AssertionError('Sealed input was mutable')
written=0
try:
    with open('/work/capacity','wb',buffering=0) as output:
        for _ in range(80): written+=output.write(b'x'*(1024*1024))
except OSError as error: assert error.errno==errno.ENOSPC
else: raise AssertionError('Temporary filesystem was not bounded')
assert written<=44*1024*1024
print(json.dumps({'input_sealed_bytes':20*1024*1024,'temporary_written_bytes':written,'enospc':True}))
''')
    report["temporary_and_seals"] = json.loads(raw)
    print("stress: actual runtime output-reader bounds", flush=True)
    _code, raw, _inspected = await probe(image, r'''
import asyncio,json,sys
from pathlib import Path
from container_entry import consume
async def check(maximum,channel):
    producer=await asyncio.create_subprocess_exec(sys.executable,'-c',
        'import sys;sys.'+channel+'.buffer.write(b"x"*'+str(maximum+65536)+')',
        stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    path=Path('/work/'+channel)
    rejected=False
    try:
        with path.open('wb') as output:
            try: await consume(getattr(producer,channel),maximum,output)
            except OverflowError: rejected=True
        assert rejected and path.stat().st_size<=maximum
    finally:
        if producer.returncode is None: producer.kill()
        await producer.communicate()
    return path.stat().st_size
async def main():
    values={'stdout_bytes':await check(16*1024*1024,'stdout'),'stderr_bytes':await check(65536,'stderr')}
    print(json.dumps(values))
asyncio.run(main())
''')
    report["output_caps"] = json.loads(raw)
    assert report["output_caps"]["stdout_bytes"] <= 16 * MiB and report["output_caps"]["stderr_bytes"] <= 65536
    print("stress: kernel CPU quota", flush=True)
    _code, raw, _inspected = await probe(image, r'''
import json,os,time
from pathlib import Path
cpu=Path('/sys/fs/cgroup/cpu.max').read_text().split()
assert int(cpu[0])/int(cpu[1])==1
children=[]
for _ in range(2):
    child=os.fork()
    if child==0:
        until=time.monotonic()+2
        while time.monotonic()<until: pass
        os._exit(0)
    children.append(child)
for child in children: os.waitpid(child,0)
print(json.dumps({'cpu_max':cpu,'cpu_stat':Path('/sys/fs/cgroup/cpu.stat').read_text()}))
''')
    report["cpu"] = json.loads(raw)
    report["passed"] = True
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    asyncio.run(main(parser.parse_args()))
