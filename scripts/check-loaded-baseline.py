#!/usr/bin/env python3
"""Load the existing test model once and collect runner identity evidence."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request


MODEL = "hf.co/bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF:Q6_K"
BASE_URL = "http://127.0.0.1:11434"


def request_body():
    # No thread, batch, GPU-layer, fit, cache, or attention override.
    return {"model": MODEL, "prompt": "Reply with one short sentence: the GPU memory test is ready.",
            "stream": False, "keep_alive": "30m", "options": {"num_ctx": 32768, "num_predict": 128}}


def api(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(BASE_URL + path, data=data,
                                     headers={"Content-Type": "application/json"})
    # This experiment talks directly to the local server, without proxy routing.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=900 if payload is not None else 15) as response:
        return json.load(response)


def sample_memory():
    values = {"utc": datetime.now(timezone.utc).isoformat(), "monotonic_seconds": time.monotonic()}
    for name in ("meminfo", "vmstat"):
        try:
            values[name] = Path("/proc/" + name).read_text()
        except OSError as exc:
            values[name] = {"error": type(exc).__name__}
    return values


def command(argv, timeout):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=timeout)
        return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"returncode": None, "stdout": "", "stderr": type(exc).__name__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New evidence directory; default is outside Git")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or root.parent / "anv-gpu-reclaim-evidence" / (stamp + "-loaded-baseline")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    # The evidence can contain machine paths and logs; keep its files private.
    import os
    old_umask = os.umask(0o077)
    report = {"purpose": "loaded-driver identity check; not the A-C comparison", "request": request_body()}
    started = datetime.now(timezone.utc).isoformat()
    report["started_utc"] = started
    samples = [sample_memory()]
    done = threading.Event()

    def sampler():
        while not done.wait(1):
            samples.append(sample_memory())

    thread = threading.Thread(target=sampler, daemon=True)
    success = False
    load_attempted = False
    try:
        report["version"] = api("/api/version")
        if report["version"].get("version") != "0.34.4":
            raise RuntimeError("Ollama version changed; reassess the image before loading")
        report["models_before"] = api("/api/ps")
        if report["models_before"].get("models"):
            raise RuntimeError("A model is already loaded; stop it manually before this fresh-load check")
        report["installed_models"] = api("/api/tags")
        if not any(MODEL in (entry.get("name"), entry.get("model"))
                   for entry in report["installed_models"].get("models", [])):
            raise RuntimeError("The selected model is not installed; this script does not pull models")
        print("Loading the existing Q6_K test model with context 32768 and default thread selection.", flush=True)
        print("Observe the desktop; interrupt if it becomes impractical to use.", flush=True)
        thread.start()
        load_attempted = True
        report["response"] = api("/api/generate", report["request"])
        report["models_after"] = api("/api/ps")
        response = report["response"]
        success = response.get("done") is True and not response.get("error") and response.get("eval_count", 0) > 0
        if not success:
            report["error"] = "Request did not return a completed generation with evaluated tokens"
    except KeyboardInterrupt:
        report["error"] = "Operator interrupted; interrupting the client does not guarantee runner unload"
    except Exception as exc:
        report["error"] = str(exc)
    finally:
        done.set()
        if thread.is_alive():
            thread.join(timeout=2)
        samples.append(sample_memory())
        (output / "memory-samples.json").write_text(json.dumps(samples, indent=2) + "\n")
        if load_attempted:
            print("Collecting process maps, package identity and cgroups while the runner remains loaded.", flush=True)
            collected = command([sys.executable, str(root / "scripts/collect-inventory.py"),
                                        "--container", "ollama", "--output", str(output / "inventory")],
                                       timeout=120)
            report["inventory_collection"] = collected
            logs = command(["podman", "logs", "--since", started, "ollama"], timeout=30)
            (output / "container-stdout.log").write_text(logs["stdout"])
            (output / "container-stderr.log").write_text(logs["stderr"])
            report["container_logs_returncode"] = logs["returncode"]
        report["request_completed"] = success
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        (output / "baseline.json").write_text(json.dumps(report, indent=2) + "\n")
        bundle = output.parent / (output.name + ".tar.gz")
        # Refuse to overwrite a previous evidence bundle.
        with bundle.open("xb") as bundle_file, tarfile.open(fileobj=bundle_file, mode="w:gz") as archive:
            archive.add(output, arcname=output.name)
        print("Evidence:", output.resolve())
        print("Bundle:", bundle.resolve())
        print("Review the directory before sharing; do not commit raw evidence to the public repository.")
        if load_attempted:
            print("The model remains loaded for up to 30 minutes. Stop it manually after collection:")
            print("OLLAMA_HOST=http://127.0.0.1:11434 ollama stop " + MODEL)
        if report.get("error"):
            print("Check failed:", report["error"], file=sys.stderr)
        os.umask(old_umask)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
