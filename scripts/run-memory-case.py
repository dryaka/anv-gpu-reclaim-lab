#!/usr/bin/env python3
"""Case D: hold 4 GiB of touched anonymous memory through one explicit reload."""
import argparse
import importlib.util
import json
import mmap
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tarfile
import threading
import time

spec = importlib.util.spec_from_file_location('reload_case', Path(__file__).with_name('run-reload-case.py'))
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
HOLDER_BYTES = 4 * 1024**3


def holder():
    parent = os.getppid()
    allocation = mmap.mmap(-1, HOLDER_BYTES, flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
                           prot=mmap.PROT_READ | mmap.PROT_WRITE)
    # Touch every base page once; no allocation growth, mlock or CPU stress loop.
    for offset in range(0, HOLDER_BYTES, os.sysconf('SC_PAGE_SIZE')):
        allocation[offset] = 1
    print(json.dumps({'pid': os.getpid(), 'allocated_bytes': HOLDER_BYTES,
                      'status': lab.read('/proc/self/status')}), flush=True)
    try:
        while os.getppid() == parent:
            time.sleep(1)
    finally:
        allocation.close()


def memory_kib(meminfo, key):
    for line in meminfo.splitlines():
        if line.startswith(key + ':'):
            return int(line.split()[1])
    raise RuntimeError(f'{key} is missing')


def run_sequence(runner):
    # C ends unloaded: first establish D's loaded state with the holder present.
    runner.generate(0)
    runner.stop(0)
    runner.generate(1)
    runner.stop(1)


def stop_holder(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--holder', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--note', default='', help='Optional operator note')
    args = parser.parse_args()
    if args.holder:
        holder()
        return 0
    os.umask(0o077)
    stamp = lab.datetime.now(lab.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    root = Path(__file__).resolve().parent.parent
    output = root.parent / 'anv-gpu-reclaim-evidence' / (stamp + '-case-D')
    output.mkdir(parents=True, exist_ok=False)
    # Reuse the enabled Case C identity/switch preflight; D has its own sequence.
    runner = lab.CaseRunner('C', output)
    runner.report.update({'case': 'D', 'operator_note': args.note, 'holder_bytes': HOLDER_BYTES,
                          'purpose': 'one explicit reload with a bounded low-CPU memory holder'})
    process = None
    samples = []
    finished = threading.Event()
    original_sample = runner.sample

    def sample():
        value = original_sample()
        if process is not None:
            value['holder_pid'] = process.pid
            value['holder_status'] = lab.read(f'/proc/{process.pid}/status')
            value['holder_stat'] = lab.read(f'/proc/{process.pid}/stat')
        return value

    runner.sample = sample

    def sampler():
        while not finished.is_set():
            samples.append(sample())
            finished.wait(1)

    thread = threading.Thread(target=sampler, daemon=True)
    success = False
    try:
        runner.preflight()
        runner.case = 'D'
        before = runner.sample()['meminfo']
        # Start only with ample currently available headroom; this is an allocation guard,
        # not a memory reservation or a promise of full model placement.
        if not isinstance(before, str) or memory_kib(before, 'MemAvailable') < 12 * 1024**2:
            raise RuntimeError('Less than 12 GiB MemAvailable before holder allocation; return evidence for reassessment')
        print('Case D: allocating and touching a fixed 4 GiB memory holder.', flush=True)
        print('Observe responsiveness; Ctrl+C stops the model and frees the holder.', flush=True)
        runner.event('before-holder')
        thread.start()
        with (output / 'holder.stderr').open('wb') as error_log:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--holder'],
                                       stdout=subprocess.PIPE, stderr=error_log, start_new_session=True)
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                if not selector.select(timeout=60):
                    raise RuntimeError('Memory holder did not become ready within 60 seconds')
                ready = process.stdout.readline()
            if not ready:
                raise RuntimeError('Memory holder exited before readiness; see holder.stderr')
            details = json.loads(ready)
            runner.save('holder-ready.json', details)
            if process.poll() is not None:
                raise RuntimeError('Memory holder exited before the model test')
            resident = memory_kib(details['status'], 'VmRSS') * 1024
            if resident < HOLDER_BYTES * 0.95:
                raise RuntimeError('Holder has less than 95% of its requested resident footprint; return evidence')
            runner.event('holder-ready')
            run_sequence(runner)
            if process.poll() is not None:
                raise RuntimeError('Memory holder exited during the model test')
            success = True
    except KeyboardInterrupt:
        runner.report['error'] = 'Operator interrupted'
    except Exception as exc:
        runner.report['error'] = str(exc)
    finally:
        if runner.attempted:
            try:
                runner.stop('cleanup')
            except Exception as exc:
                runner.report['cleanup_error'] = str(exc)
        runner.event('before-holder-release')
        stop_holder(process)
        if process is not None:
            runner.report['holder_exit_code'] = process.returncode
            process.stdout.close()
        runner.event('holder-released')
        finished.set()
        if thread.is_alive():
            thread.join(timeout=2)
        samples.append(sample())
        runner.capture('case-logs', ['podman', 'logs', '--since', runner.report['started_utc'], runner.container], check=False)
        runner.capture('kernel-log', ['journalctl', '-k', '--since', runner.report['started_utc'], '--no-pager'], check=False)
        runner.report.update({'completed': success, 'finished_utc': lab.utc()})
        runner.save('case.json', runner.report)
        runner.save('memory-samples.json', samples)
        bundle = output.with_suffix('.tar.gz')
        with bundle.open('xb') as handle, tarfile.open(fileobj=handle, mode='w:gz') as archive:
            archive.add(output, arcname=output.name)
        print(f'Evidence: {bundle}', flush=True)
        print('Return the bundle and responsiveness note. The holder has been released.')
        if runner.report.get('error'):
            print('Case stopped:', runner.report['error'], file=sys.stderr)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
