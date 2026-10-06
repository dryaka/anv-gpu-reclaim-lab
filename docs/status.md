# Experiment status and next handoff

Updated: 6 October 2026, after review of the completed local build.

| Plan step | State |
| --- | --- |
| 1–2 — inventory and source binding | Complete. Baseline: context 32,768, 66/66 layers on GPU. |
| 3 — opt-in implementation | Local helper tests pass; full patched ANV compilation succeeded on Aleš's host. |
| 4–6 — build and evidence review | Complete. Missing XRandR build dependency fixed; source/patch identity, build options, ICD and runtime dependencies verified. |
| 7 — switch-off smoke | Next action — Aleš. |
| 8–13 — comparisons, analysis and decision | Pending smoke verification. |

## Reviewed build

Private bundle: `20261006T200701Z-build.tar.gz`.

- Build commit: `b14f909fe917567629c5fc5a4176feb37e381d4f`.
- Image tag: `localhost/ollama-anv-test:b14f909fe917`.
- Image ID: `2687fe2ef85d0b19e60318e731e4af0309370cb8c81efd4233609eb72866bda6`.
- ANV library SHA-256: `0efddde0239a00350d75491fc49e46e5a155e3f5ed5f18f0ebe48620542b0d37`.
- Patch SHA-256: `d59b3f8d7608fec6a34cb3eca715b5c391e5c13c7bdc9e1321df8f90f114e157`.

The release build selects only Intel Vulkan, with X11/Wayland and LLVM enabled. The ICD references `/opt/mesa-anv-test/lib/libvulkan_intel.so`; all recorded runtime dependencies resolve. Build success does not establish actual runner driver selection, GPU access, or reclaim behavior.

## Aleš: switch-off smoke

Pull the updated branch, then use the container-start commands in [build/runtime handoff](build-and-runtime.md). Run:

```bash
python3 scripts/smoke-test.py
```

Attach the printed smoke `.tar.gz` bundle. The script stops the small smoke model after collecting loaded-runner evidence. Keep the original container for rollback. The built image stays the same despite newer documentation/collector commits; no rebuild is required.

## Acceptance remains unchanged

A–C each use one initial load plus three manual stop/reload cycles under a populated reuse pool. B/C use the same custom image with the switch off/on; CPU thread selection remains at its default and context is fixed at 32,768. D is a bounded memory holder with low CPU activity, sized after A–C. The initial baseline verifies source binding and full loading with ample headroom; it is not evidence that the reload problem is fixed.
