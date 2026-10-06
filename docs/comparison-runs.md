# Measured comparison runs

The switch-off smoke passed: the custom ANV library was mapped by `llama-server` with the reviewed hash, Intel PTL was selected, 17/17 small-model layers were offloaded, and inference completed. Diagnostic `enabled=0 valid=1` reports `selected=original` while roughly 22 GiB of GPU reclaim pool was present. This validates startup and the observed disabled calculation, not yet A/B equivalence or the enabled fix.

## Case A now

Pull the updated experiment branch. Stop the test server and start the original server:

```bash
git pull --ff-only
podman stop ollama-anv-test
podman start ollama
OLLAMA_HOST=http://127.0.0.1:11434 ollama ps
```

If `ollama ps` lists a model, stop that model explicitly before continuing. Then:

```bash
python3 scripts/run-reload-case.py --case A
```

The collector refuses to generate if either a model or runner is already present, the other server is running, the image identity changed, or the selected model manifest differs. It does not download models, rebuild images, change container configuration, restart servers or shrink the pool.

A case makes four identical requests: initial load and three reloads. After each request it collects process maps/cgroups and logs, explicitly calls `ollama stop`, and confirms both an empty API model list and exit of `llama-server` before the next request. After the final request it also stops the model, leaving the pool populated and server available. No container restart occurs within a case. Keep clients idle during measurement.

The fixed request matches the verified loaded baseline: ThinkingCap Q6_K, context 32,768, the same prompt, output cap 128 and keep-alive 30 minutes. No CPU-thread, GPU-layer, batch, cache or fit override is added. Host memory/vmstat and available cgroup memory/OOM counters are sampled about once per second through requests, unloads and evidence collection. Event timestamps distinguish timed requests from subsequent probes. Container log stdout/stderr are retained as raw bytes. Kernel journal access may be unavailable; the command status and error are saved rather than claiming a clean kernel.

Observe the desktop. Press Ctrl+C if it becomes persistently unresponsive or sustained swapping makes it impractical to use. The collector stops the attempted model and packages available evidence. If cleanup cannot confirm exit, stop the case server manually and report that outcome. Do not change reserves or force layer placement to rescue a failing run.

Attach the printed case `.tar.gz` bundle and say whether desktop responsiveness remained acceptable. The assistant checks starting pool size, swap deltas, OOM/reset evidence, offload/context and generation timing before the next case. A successful script exit means all four requests and unload checks completed; it does not mean the patch passed. Partial offload in A/B is the behavior being measured.

## B and C after A review

B uses the existing reviewed custom image with switch 0. Once A evidence is accepted:

```bash
podman stop ollama
podman start ollama-anv-test
python3 scripts/run-reload-case.py --case B
```

Do not rebuild the image. C uses the same image ID with switch 1, applied by recreating the test container between cases. Its exact handoff follows B review. Keep the same model mount, SELinux level, IGPU setting and ANV system-memory limit. There is no reclaim or container recreation between measured stop/reload cycles.

If an inadequate pool prevents A/B from exercising the issue, report an inconclusive case. Any seed load or shrink preparation is a separate recorded action before a new case, never an alteration inside its measured sequence. Do not run D until A–C establish the core result.
