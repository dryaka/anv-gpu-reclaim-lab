# Experiment status and next handoff

Updated: 6 October 2026, after Case A evidence review.

| Plan step | State |
| --- | --- |
| 1–2 — inventory and source binding | Complete. Baseline: context 32,768, 66/66 layers on GPU. |
| 3 — opt-in implementation | Local helper tests pass; full patched ANV compilation succeeded on Aleš's host. |
| 4–6 — build and evidence review | Complete. Missing XRandR build dependency fixed; source/patch identity, build options, ICD and runtime dependencies verified. |
| 7–8 — switch-off smoke and review | Complete. Custom driver, switch-off calculation, 17/17 offload and successful generation confirmed. |
| 9 — A/B/C comparisons | A reproduced partial offload on all four loads. B is the next action; C pending. |
| 10–13 — analysis, pressure test, rollback and decision | Pending comparisons. |

## Reviewed build

Private bundle: `20261006T200701Z-build.tar.gz`.

- Build commit: `b14f909fe917567629c5fc5a4176feb37e381d4f`.
- Image tag: `localhost/ollama-anv-test:b14f909fe917`.
- Image ID: `2687fe2ef85d0b19e60318e731e4af0309370cb8c81efd4233609eb72866bda6`.
- ANV library SHA-256: `0efddde0239a00350d75491fc49e46e5a155e3f5ed5f18f0ebe48620542b0d37`.
- Patch SHA-256: `d59b3f8d7608fec6a34cb3eca715b5c391e5c13c7bdc9e1321df8f90f114e157`.

The release build selects only Intel Vulkan, with X11/Wayland and LLVM enabled. The ICD references `/opt/mesa-anv-test/lib/libvulkan_intel.so`; all recorded runtime dependencies resolve. Build success does not establish actual runner driver selection, GPU access, or reclaim behavior.

## Aleš: Case B

[Case A assessment](case-A-assessment.md) records 37/66, 57/66, 38/66 and 56/66 GPU layers at fixed context 32,768. All requests and unload checks completed. Some swap activity occurred; no cgroup OOM or GPU reset was recorded. Operator responsiveness notes are still needed.

Run the disabled custom image comparison:

```bash
git pull --ff-only
podman stop ollama
podman start ollama-anv-test
python3 scripts/run-reload-case.py --case B
```

Attach the B bundle and desktop responsiveness observations for A/B. Keep the pool populated; do not shrink it, rebuild the image, reset swap or drop caches. See [comparison runs](comparison-runs.md).

## Acceptance remains unchanged

A–C each use one initial load plus three manual stop/reload cycles under a populated reuse pool. B/C use the same custom image with the switch off/on; CPU thread selection remains at its default and context is fixed at 32,768. D is a bounded memory holder with low CPU activity, sized after A–C. The initial baseline verifies source binding and full loading with ample headroom; it is not evidence that the reload problem is fixed.

## Switch-off smoke evidence

Bundle `20261006T202401Z-smoke-off.tgz` confirms the reviewed custom ANV hash in `llama-server` process maps. Vulkan enumeration selects Intel PTL, and diagnostics report `enabled=0 valid=1` with `selected=original`, despite a populated GPU reclaim pool. The small LFM model generated 32 tokens, all in its thinking field, then reached the output cap; this does not indicate a load or inference failure. API reports size equal to size_vram, context 4,096. The manual stop command exited successfully.

The collector failed afterward while decoding non-UTF-8 bytes from `podman logs`, so runner logs and automatic packaging are missing. The uploaded bundle was recovered manually. The collector now retains command output as original bytes, decodes returned text with replacement, and handles command timeout/spawn failures without preventing final packaging during best-effort cleanup. A regression test covers invalid UTF-8 and timed-out log capture. The recovered `container.log` completes smoke review: runner selects Vulkan0 Intel PTL, offloads 17/17 layers, and reports a final budget of 16,257,122,304 bytes while ignoring the additional reclaim allowance with the switch off. It generated 32 tokens at 23.41 tokens/s with context 4,096; no allocation/inference failure is reported in that log. This is not a complete host kernel health check.
