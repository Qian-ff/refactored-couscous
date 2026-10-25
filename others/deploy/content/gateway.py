"""Exercise the actual adapted Caddy routes with a synthetic body-consuming upstream."""
import argparse
import http.client
import json
from pathlib import Path
import subprocess
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]


def docker(*args):
    result = subprocess.run(["docker", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[:1500])
    return result.stdout


def main(report):
    report = report.resolve()
    images = json.loads((ROOT / "others/deploy/cloud/images.lock.json").read_text())
    parser_image = json.loads((ROOT / "others/runtime/c02-public/image.json").read_text())["image"]
    adapted = json.loads(docker("run", "--rm", "--network=none", "--read-only", "--cap-drop=ALL",
        "--cap-add=NET_BIND_SERVICE", "--security-opt=no-new-privileges:true", "--memory=134217728", "--pids-limit=64",
        "--env", "PUBLIC_HOST=localhost", "--mount",
        f"type=bind,source={ROOT / 'others/deploy/cloud/Caddyfile'},target=/probe/Caddyfile,readonly",
        images["caddy"], "caddy", "adapt", "--config", "/probe/Caddyfile", "--adapter", "caddyfile"))
    # Keep all production matchers, body limits and upstream routes. Only transport changes for this local probe.
    server = adapted["apps"]["http"]["servers"]["srv0"]
    server["listen"] = [":8080"]
    server.pop("tls_connection_policies", None)
    server["automatic_https"] = {"disable": True}
    adapted["apps"].pop("tls", None)
    configuration = report.parent / "gateway-probe.json"
    configuration.write_text(json.dumps(adapted), encoding="utf-8")
    owner = uuid4().hex
    network, upstream, gateway = ["labconnect-c02-" + part + "-" + owner for part in ("net", "api", "gateway")]
    units = []
    # Docker Desktop does not publish loopback ports for an internal-only bridge.
    docker("network", "create", "--label", "labconnect.c02.acceptance=" + owner, network)
    try:
        fixture = r'''
from http.server import BaseHTTPRequestHandler,HTTPServer
class Handler(BaseHTTPRequestHandler):
 def do_PUT(self):
  left=int(self.headers.get('Content-Length','0'))
  while left:
   value=self.rfile.read(min(left,65536))
   if not value: break
   left-=len(value)
  self.send_response(200);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'ok')
 do_POST=do_PUT
 do_GET=do_PUT
 def log_message(self,*args): pass
HTTPServer(('0.0.0.0',8000),Handler).serve_forever()
'''
        common = ["--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges:true", "--memory=134217728",
                  "--memory-swap=134217728", "--cpus=1", "--pids-limit=64", "--log-driver=none",
                  "--network", network, "--label", "labconnect.c02.acceptance=" + owner]
        docker("create", "--name", upstream, *common, "--network-alias", "api",
               "--entrypoint", "python", parser_image, "-c", fixture)
        units.append(upstream)
        docker("start", upstream)
        docker("create", "--name", gateway, *common, "--cap-add=NET_BIND_SERVICE", "--publish", "127.0.0.1::8080",
               "--env", "XDG_CONFIG_HOME=/tmp/config", "--env", "XDG_DATA_HOME=/tmp/data", "--tmpfs", "/tmp:rw,size=16777216",
               "--mount", f"type=bind,source={configuration},target=/probe/config.json,readonly",
               images["caddy"], "caddy", "run", "--config", "/probe/config.json")
        units.append(gateway)
        docker("start", gateway)
        metadata = json.loads(docker("inspect", "--format", "{{json .NetworkSettings.Ports}}", gateway))
        port = int(metadata["8080/tcp"][0]["HostPort"])
        def request(method, path, size=0):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
            try:
                connection.request(method, path, body=b"x" * size,
                                   headers={"Host": "localhost", "Content-Type": "application/octet-stream"})
                response = connection.getresponse()
                response.read(1024)
                return response.status
            finally:
                connection.close()
        for _attempt in range(40):
            try:
                if request("GET", "/api/v1/health") == 200:
                    break
            except OSError:
                pass
            time.sleep(.25)
        else:
            raise AssertionError("Synthetic Caddy upstream did not start")
        upload = "/api/v1/content/uploads/CB11B16E-38C7-4DB4-B477-B8598365C870/bytes"
        cases = [("PUT", upload, 22020096, 200), ("PUT", upload, 22020097, 413),
                 ("POST", upload, 2000001, 413), ("PUT", upload + "/extra", 2000001, 413),
                 ("PUT", upload.replace("CB11B16E", "invalid"), 2000001, 413),
                 ("PUT", "/api/v1/content/other", 2000001, 413),
                 ("PUT", "/api/v1/other", 2000000, 200), ("PUT", "/api/v1/other", 2000001, 413),
                 ("GET", "/api/v1/openapi.json", 0, 404), ("GET", "/docs", 0, 404), ("GET", "/redoc", 0, 404)]
        results = []
        for method, path, size, expected in cases:
            status = request(method, path, size)
            assert status == expected, (method, path, size, status, expected)
            results.append({"method": method, "path": path, "bytes": size, "status": status})
        report.write_text(json.dumps({"scope": "real-local-caddy-with-synthetic-upstream-no-ECS",
                                     "image": images["caddy"], "cases": results, "passed": True}, indent=2) + "\n")
        print(f"PASS: {len(results)} real Caddy body-limit/method/path/documentation cases")
    finally:
        for unit in reversed(units):
            labels = json.loads(docker("inspect", "--format", "{{json .Config.Labels}}", unit))
            assert labels["labconnect.c02.acceptance"] == owner
            docker("stop", "--time", "1", unit)
            docker("rm", unit)
        labels = json.loads(docker("network", "inspect", "--format", "{{json .Labels}}", network))
        assert labels["labconnect.c02.acceptance"] == owner
        docker("network", "rm", network)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    main(parser.parse_args().report)
