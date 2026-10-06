#!/usr/bin/env python3
"""Collect a switch-off small-model smoke test from the already started test container."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

CONTAINER = 'ollama-anv-test'
MODEL = 'lfm2.5-thinking:1.2b'
IMAGE_ID = '2687fe2ef85d0b19e60318e731e4af0309370cb8c81efd4233609eb72866bda6'
BASE = 'http://127.0.0.1:11435'


def api(path, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    with urlopen(Request(BASE + path, data=body, headers={'Content-Type': 'application/json'}), timeout=600) as response:
        return json.load(response)


def capture_command(output, name, args, check=True):
    """Keep original command bytes; decode only the returned display/JSON text."""
    try:
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        data = result.stdout
        returncode = result.returncode
    except subprocess.TimeoutExpired as exc:
        data = (exc.stdout or b'') + b'\nCollector: command timed out.\n'
        returncode = 124
    except OSError as exc:
        data = f'Collector: {type(exc).__name__}: {exc}\n'.encode('utf-8')
        returncode = 125
    (output / name).write_bytes(data)
    if check and returncode:
        raise RuntimeError(f'{name}: command failed with status {returncode}')
    return data.decode('utf-8', errors='replace')


def main():
    os.umask(0o077)
    repo = Path(__file__).resolve().parent.parent
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = repo.parent / 'anv-gpu-reclaim-evidence' / (stamp + '-smoke-off')
    out.mkdir(parents=True, exist_ok=False)

    def capture(name, args, check=True):
        return capture_command(out, name, args, check)

    attempted = False
    try:
        inspected = json.loads(capture('container-inspect.json', ['podman', 'inspect', CONTAINER]))[0]
        env = dict(item.split('=', 1) for item in inspected['Config']['Env'] if '=' in item)
        if inspected['Image'].removeprefix('sha256:') != IMAGE_ID:
            raise RuntimeError('Test container does not use the reviewed image')
        if env.get('ANV_EXPERIMENTAL_GPU_RECLAIM') != '0' or env.get('ANV_EXPERIMENTAL_GPU_RECLAIM_DEBUG') != '1':
            raise RuntimeError('Expected reclaim switch 0 and diagnostic switch 1')
        for attempt in range(30):
            try:
                api('/api/version')
                break
            except OSError:
                if attempt == 29:
                    raise
                time.sleep(1)
        if api('/api/ps').get('models'):
            raise RuntimeError('Stop existing test-container models before running this smoke test')
        if MODEL not in [m.get('name') for m in api('/api/tags').get('models', [])]:
            raise RuntimeError(f'{MODEL} is not installed; no model was downloaded')
        capture('devices.txt', ['podman', 'exec', CONTAINER, 'sh', '-c', 'id; ls -l /dev/dri'])
        capture('vulkaninfo.txt', ['podman', 'exec', CONTAINER, 'vulkaninfo', '--summary'])
        request = {'model': MODEL, 'prompt': 'Reply with one short sentence: the GPU memory test is ready.',
                   'stream': False, 'keep_alive': '30m', 'options': {'num_ctx': 4096, 'num_predict': 32}}
        (out / 'request.json').write_text(json.dumps(request, indent=2) + '\n')
        attempted = True
        response = api('/api/generate', request)
        (out / 'response.json').write_text(json.dumps(response, indent=2) + '\n')
        if not response.get('done'):
            raise RuntimeError('Inference did not finish successfully')
        (out / 'loaded-models.json').write_text(json.dumps(api('/api/ps'), indent=2) + '\n')
        capture('inventory-collector.txt', [sys.executable, str(repo / 'scripts/collect-inventory.py'),
                                          '--container', CONTAINER, '--output', str(out / 'loaded-inventory')])
        print('Inference completed. Return evidence for driver/offload verification.')
    finally:
        if attempted:
            capture('stop-model.txt', ['podman', 'exec', CONTAINER, 'ollama', 'stop', MODEL], check=False)
        capture('container.log', ['podman', 'logs', CONTAINER], check=False)
        bundle = out.with_suffix('.tar.gz')
        with tarfile.open(bundle, 'w:gz') as archive:
            archive.add(out, arcname=out.name)
        print(f'Smoke evidence: {bundle}')


if __name__ == '__main__':
    main()
