"""Read exact deployed image/role/content capability; called after trusted HTTPS succeeds."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def inspect(image):
    return json.loads(subprocess.check_output(['docker', 'inspect', image], text=True))[0]


def main(sha):
    if not re.fullmatch('[0-9a-f]{40}', sha):
        raise RuntimeError('Invalid expected release SHA')
    root = Path('/opt/labconnect')
    manifest = json.loads((root / 'current/manifest.json').read_text())
    if manifest['source_sha'] != sha or manifest['contract'] != '0.5.0':
        raise RuntimeError('Expected source/contract differs from deployed release')
    for service, label in [('api', 'api'), ('web', 'web'), ('content-control', 'control')]:
        actual = inspect('labconnect-cloud-' + service + '-1')
        if (not actual['State']['Running'] or actual['Image'] != manifest['image_ids'][label]
                or actual['Config']['Labels'].get('org.opencontainers.image.revision') != sha):
            raise RuntimeError('Actual container image/source mismatch: ' + service)
        if service != 'web' and any(actual['HostConfig'].get('PortBindings', {}).values()):
            raise RuntimeError('API/control must not expose host ports')
    if any(inspect('labconnect-cloud-db-1')['HostConfig'].get('PortBindings', {}).values()):
        raise RuntimeError('Database must not expose host ports')
    parser = inspect(manifest['image_ids']['parser'])
    if parser['Config']['Labels'].get('labconnect.parse.source-sha') != sha:
        raise RuntimeError('Parser image source mismatch')
    result = json.loads(subprocess.check_output(['docker', 'exec', 'labconnect-cloud-api-1',
        '.venv/bin/python', '/opt/labconnect/others/deploy/cloud/content_setup.py', 'verify'], text=True))
    if (result['source_sha'] != sha or result['parser_image'] != manifest['image_ids']['parser']
            or not result['socket_configured'] or not result['runtime_nonowner']):
        raise RuntimeError('Actual API content/role/source mismatch')
    subprocess.run(['docker', 'exec', 'labconnect-cloud-content-control-1', 'python',
        'others/deploy/content/probe.py', '--config', '/run/labconnect-content/parser-client.json'],
        check=True, stdout=subprocess.DEVNULL)
    value = {'source_sha': sha, 'status': 'trusted_https_and_content_capabilities_verified',
             'verified_at': datetime.now(timezone.utc).isoformat(), **result,
             'normal_content_flow_verified': False}
    temporary = root / 'deployment.pending.json'
    temporary.write_text(json.dumps(value) + '\n')
    os.replace(temporary, root / 'deployment.json')
    print(json.dumps(value))


if __name__ == '__main__':
    main(sys.argv[1])
