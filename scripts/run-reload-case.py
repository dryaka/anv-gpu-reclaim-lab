#!/usr/bin/env python3
"""A–C: initial load and three stop/reloads. E: one rollback request. No shrinking or server restarts."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request

MODEL = 'hf.co/bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF:Q6_K'
MODEL_DIGEST = 'c44571a7ec4632c3d7494a7317a9c70949ce475d2acce2586046d585f244839f'
IMAGES = {'E': '7fe01b0ef22e342fcbcb61e89d39de511609f078c30754a3a0bee7bb0f20a5c2',
          'A': '7fe01b0ef22e342fcbcb61e89d39de511609f078c30754a3a0bee7bb0f20a5c2',
          'B': '2687fe2ef85d0b19e60318e731e4af0309370cb8c81efd4233609eb72866bda6',
          'C': '2687fe2ef85d0b19e60318e731e4af0309370cb8c81efd4233609eb72866bda6'}


def utc():
    return datetime.now(timezone.utc).isoformat()


def request_body():
    return {'model': MODEL, 'prompt': 'Reply with one short sentence: the GPU memory test is ready.',
            'stream': False, 'keep_alive': '30m', 'options': {'num_ctx': 32768, 'num_predict': 128}}


def read(path):
    try:
        return Path(path).read_text()
    except OSError as exc:
        return {'error': type(exc).__name__}


def command(args, timeout=60):
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or b'', (exc.stderr or b'') + b'\nCollector: command timed out\n'
    except OSError as exc:
        return 125, b'', str(exc).encode()


def run_cycles(runner, loads=4):
    for index in range(loads):
        runner.generate(index)
        runner.stop(index)


class CaseRunner:
    def __init__(self, case, output):
        self.case, self.output = case, output
        self.container = 'ollama' if case in ('A', 'E') else 'ollama-anv-test'
        self.other = 'ollama-anv-test' if case in ('A', 'E') else 'ollama'
        self.base = 'http://127.0.0.1:' + ('11434' if case in ('A', 'E') else '11435')
        self.root = Path(__file__).resolve().parent.parent
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.report = {'case': case, 'started_utc': utc(), 'request': request_body(), 'events': [], 'runs': []}
        self.cgroup = None
        self.attempted = False

    def save(self, name, value):
        (self.output / name).write_text(json.dumps(value, indent=2) + '\n')

    def api(self, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(self.base + path, data=body, headers={'Content-Type': 'application/json'})
        with self.opener.open(request, timeout=900 if path == '/api/generate' else 15) as response:
            return json.load(response)

    def capture(self, name, args, check=True):
        code, stdout, stderr = command(args)
        (self.output / (name + '.stdout')).write_bytes(stdout)
        (self.output / (name + '.stderr')).write_bytes(stderr)
        self.report.setdefault('commands', []).append({'name': name, 'returncode': code, 'utc': utc()})
        if check and code:
            raise RuntimeError(f'{name} failed ({code}); see captured output')
        return code, stdout.decode('utf-8', errors='replace')

    def sample(self):
        value = {'utc': utc(), 'monotonic_seconds': time.monotonic(),
                 'meminfo': read('/proc/meminfo'), 'vmstat': read('/proc/vmstat')}
        if self.cgroup:
            value['cgroup'] = {n: read(self.cgroup / n) for n in
                               ('memory.current', 'memory.swap.current', 'memory.events', 'memory.events.local')}
        return value

    def event(self, name, index=None):
        self.report['events'].append({'event': name, 'run': index, **self.sample()})

    def inspect(self, container, required=True):
        code, text = self.capture('inspect-' + container, ['podman', 'inspect', '--type', 'container', container], check=required)
        return json.loads(text)[0] if code == 0 else None

    def preflight(self):
        current = self.inspect(self.container)
        if not current['State']['Running']:
            raise RuntimeError('Start the case server before running this collector')
        other = self.inspect(self.other)
        if other and other['State']['Running']:
            raise RuntimeError(f'Stop {self.other} during measured comparisons')
        if current['Image'].removeprefix('sha256:') != IMAGES[self.case]:
            raise RuntimeError('Unexpected image identity; do not rebuild/change images between cases')
        env = dict(x.split('=', 1) for x in current['Config']['Env'] if '=' in x)
        if env.get('OLLAMA_IGPU_ENABLE') != '1' or env.get('ANV_SYS_MEM_LIMIT') != '90':
            raise RuntimeError('Expected OLLAMA_IGPU_ENABLE=1 and ANV_SYS_MEM_LIMIT=90')
        if self.case not in ('A', 'E'):
            expected = '1' if self.case == 'C' else '0'
            if env.get('ANV_EXPERIMENTAL_GPU_RECLAIM') != expected or env.get('ANV_EXPERIMENTAL_GPU_RECLAIM_DEBUG') != '1':
                raise RuntimeError('Unexpected experiment/diagnostic switch state')
            if env.get('VK_DRIVER_FILES') != '/opt/mesa-anv-test/share/vulkan/icd.d/intel_icd.json':
                raise RuntimeError('Custom ICD selection changed')
        for attempt in range(30):
            try:
                version = self.api('/api/version')
                break
            except OSError:
                if attempt == 29:
                    raise
                time.sleep(1)
        if version.get('version') != '0.34.4':
            raise RuntimeError('Unexpected Ollama version')
        if self.api('/api/ps').get('models') or self.has_runner():
            raise RuntimeError('A model/runner is already present; stop it explicitly before the case')
        installed = self.api('/api/tags')
        self.save('installed-models.json', installed)
        matched = [x for x in installed.get('models', []) if MODEL in (x.get('name'), x.get('model'))]
        if len(matched) != 1 or matched[0].get('digest') != MODEL_DIGEST:
            raise RuntimeError('Selected model is absent or its manifest changed; no model was pulled')
        self.save('model-show.json', self.api('/api/show', {'model': MODEL}))
        pid = current['State']['Pid']
        membership = read(f'/proc/{pid}/cgroup')
        if isinstance(membership, str):
            for line in membership.splitlines():
                if line.startswith('0::'):
                    relative = Path(line[3:].lstrip('/'))
                    if '..' not in relative.parts:
                        self.cgroup = Path('/sys/fs/cgroup') / relative
        self.capture('repo-commit', ['git', '-C', str(self.root), 'rev-parse', 'HEAD'])
        self.event('case-start')

    def has_runner(self):
        _, text = self.capture('top-latest', ['podman', 'top', self.container, 'pid', 'comm'])
        return any(line.split()[-1:] == ['llama-server'] for line in text.splitlines()[1:])

    def generate(self, index):
        print(f'Case {self.case}: {"initial load" if index == 0 else "reload " + str(index)}', flush=True)
        self.event('request-start', index)
        started = utc()
        self.attempted = True
        response = self.api('/api/generate', request_body())
        self.event('request-finished', index)
        self.save(f'run-{index}-response.json', response)
        if not response.get('done') or response.get('error') or response.get('eval_count', 0) <= 0:
            raise RuntimeError('Generation did not complete successfully')
        loaded = self.api('/api/ps')
        self.save(f'run-{index}-loaded.json', loaded)
        entries = [m for m in loaded.get('models', []) if MODEL in (m.get('name'), m.get('model'))]
        if len(entries) != 1 or entries[0].get('context_length') != 32768 or entries[0].get('digest') != MODEL_DIGEST:
            raise RuntimeError('Loaded context/model differs from the fixed workload')
        self.report['runs'].append({'index': index, 'started_utc': started, 'finished_utc': utc(),
                                   'loaded': entries[0], **{k: response.get(k) for k in
                                   ('load_duration', 'prompt_eval_count', 'prompt_eval_duration', 'eval_count', 'eval_duration', 'done_reason')}})
        # Probes are outside the timed request, while its runner is still loaded.
        self.capture(f'run-{index}-inventory', [sys.executable, str(self.root / 'scripts/collect-inventory.py'),
                      '--container', self.container, '--output', str(self.output / f'run-{index}-inventory')])
        self.capture(f'run-{index}-logs', ['podman', 'logs', '--since', started, self.container])

    def stop(self, index):
        self.event('stop-start', index)
        self.capture(f'run-{index}-stop', ['podman', 'exec', self.container, 'ollama', 'stop', MODEL])
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if not self.api('/api/ps').get('models') and not self.has_runner():
                self.event('unloaded-and-runner-exited', index)
                self.attempted = False
                return
            time.sleep(1)
        raise RuntimeError('Model/runner did not unload within 60 seconds; no further reload attempted')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('A', 'B', 'C', 'E'), required=True)
    parser.add_argument('--note', default='', help='Operator notes; also report responsiveness after the run')
    args = parser.parse_args()
    os.umask(0o077)
    root = Path(__file__).resolve().parent.parent
    output = root.parent / 'anv-gpu-reclaim-evidence' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-case-' + args.case)
    output.mkdir(parents=True, exist_ok=False)
    runner = CaseRunner(args.case, output)
    runner.report['operator_note'] = args.note
    finished = threading.Event()
    samples = []

    def sampler():
        while not finished.is_set():
            samples.append(runner.sample())
            finished.wait(1)

    thread = threading.Thread(target=sampler, daemon=True)
    success = False
    try:
        runner.preflight()
        print('Observe responsiveness; Ctrl+C stops this case and collects available evidence.', flush=True)
        thread.start()
        run_cycles(runner, loads=1 if args.case == 'E' else 4)
        success = True
    except KeyboardInterrupt:
        runner.report['error'] = 'Operator interrupted'
    except Exception as exc:
        runner.report['error'] = str(exc)
    finally:
        if runner.attempted:
            # Explicitly stop on failure too; interrupting an HTTP client alone does not unload the runner.
            try:
                runner.stop('cleanup')
            except Exception as exc:
                runner.report['cleanup_error'] = str(exc)
        finished.set()
        if thread.is_alive():
            thread.join(timeout=2)
        samples.append(runner.sample())
        runner.capture('case-logs', ['podman', 'logs', '--since', runner.report['started_utc'], runner.container], check=False)
        runner.capture('kernel-log', ['journalctl', '-k', '--since', runner.report['started_utc'], '--no-pager'], check=False)
        runner.report.update({'completed': success, 'finished_utc': utc()})
        runner.save('case.json', runner.report)
        runner.save('memory-samples.json', samples)
        bundle = output.with_suffix('.tar.gz')
        with bundle.open('xb') as handle, tarfile.open(fileobj=handle, mode='w:gz') as archive:
            archive.add(output, arcname=output.name)
        print(f'Evidence: {bundle}', flush=True)
        print('Return the bundle and desktop responsiveness notes. Do not commit raw evidence.')
        if runner.report.get('error'):
            print('Case stopped:', runner.report['error'], file=sys.stderr)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
