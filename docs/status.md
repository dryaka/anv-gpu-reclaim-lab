# Experiment status and next handoff

Updated: 6 October 2026, after the device and saved-parameter checks.

| Plan step | State |
| --- | --- |
| 1 — environment inventory | Received and assessed. Memory tests used defaults; the separate 12-thread CPU choice is excluded. |
| 2 — loaded driver, matched source and kernel/limits check | Exact Mesa and Fedora sources, image/config digest binding, resource limits, visible GPU device nodes and absence of saved parameter overrides confirmed. Actual loaded-runner ANV library remains to be verified. |
| 3 — opt-in ANV implementation | Pending loaded-runner binding; no experimental patch exists yet. |
| 4 — build and comparison bundle | Pending step 3. Inventory, source-fetch and loaded-baseline identity-check tools are ready. |
| 5–13 — build, hardware tests, analysis and decision | Not started. |

## Aleš: loaded baseline identity check

Run from the repository, with no model currently loaded and no other inference requests during collection:

```bash
git fetch origin
git switch experiment/anv-gpu-reclaim
git pull --ff-only
python3 scripts/check-loaded-baseline.py
```

This is now an intentional model load, using the installed Q6_K test model. It requests a 32,768 context and at most 128 output tokens, leaves thread/batch/GPU selection and other inference options at their defaults, and keeps the runner loaded for up to 30 minutes so its library maps can be captured. No model is pulled, no memory is manually reclaimed, and no existing loaded model is stopped by the script. It refuses to proceed if another model is loaded, the model is absent or the Ollama version has changed.

The 262,144 context reported by `ollama show` is the model's maximum, not evidence of the actual runtime allocation. Both container and host CLI `show --parameters` returned no saved overrides. The baseline's explicit 32,768 request is recorded separately from the earlier default-based tests.

The script samples host memory/vmstat about once per second during the request, collects inventory/process maps while the runner remains loaded, and records both stdout and stderr from container logs since the check began. It saves the request, response and API model status as well. A completed generation does not by itself establish correct offload or library identity; the assistant will inspect the evidence.

It prints an evidence directory and a `.tar.gz` bundle outside Git. Review and attach the bundle here; do not commit it to this public repository. The check is preparation evidence, not case A or a substitute for the three-reload matrix.

After the script has finished collecting, stop the model manually:

```bash
OLLAMA_HOST=http://127.0.0.1:11434 ollama stop hf.co/bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF:Q6_K
```

If the desktop becomes persistently unresponsive or a GPU/OOM error occurs, interrupt the script and stop the model manually; interrupting the API client does not guarantee unload. Preserve the evidence for diagnosis. Do not force more GPU layers or remove reserves to make the check complete.

## Assistant: next work

1. Check effective context, placement and loaded ANV hash against the confirmed package/source.
2. Implement and test the default-off ANV patch, preserving raw Xe/heap bounds, reserves and rounding.
3. Provide the multi-stage Containerfile, driver verification, identical A–C request/cycle tools and rollback commands. Recover or verify the actual device mapping when specifying the test-container launch; observing device nodes did not recover the original creation command.

A–C remain one initial load plus three manual stop/reload cycles each. The separate 12-thread CPU setting is not imported. Case D is a bounded anonymous-memory holder with low CPU activity, sized after A–C results. No timeout-driven scenario is required.
