# Experiment status and next handoff

Updated: 6 October 2026, after loaded-baseline verification and patch preparation.

| Plan step | State |
| --- | --- |
| 1 — environment inventory | Complete for this preparation. Defaults recorded; separate 12-thread CPU setting excluded. |
| 2 — loaded driver, matched source and kernel/limits | Complete. Actual ANV hash matches the package/source; exact Fedora accounting and image config digest checked. Baseline uses context 32,768 with 66/66 offload. |
| 3 — opt-in ANV implementation | Patch written and locally reviewed; parser/arithmetic tests and exact-source patch application pass. Full driver compilation is the next validation. |
| 4 — build and evidence bundle | Containerfile, build collector, runtime design and rollback instructions ready. Exact smoke/cycle execution tooling will be finalized after build review, before hardware comparisons. |
| 5 — local image build | Next action — Aleš. |
| 6–13 — build review, smoke, comparisons, analysis and decision | Pending the build. |

## Aleš: build and return evidence

Stop the baseline model manually if it is still loaded, then build from the clean updated branch:

```bash
ollama stop hf.co/bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF:Q6_K
git fetch origin
git switch experiment/anv-gpu-reclaim
git pull --ff-only
bash scripts/build-image.sh
```

This compiles the experimental image and collects source, patch, package, image and dependency evidence. It does not start the experimental service or replace the normal container. It uses four build jobs by default and includes LLVM 20 development dependencies. Let the host settle after compilation before memory measurements.

Attach the printed build `.tar.gz` bundle here. If the build fails, attach its `build.log`. See [build/runtime handoff](build-and-runtime.md) for details. The assistant will review compiler/dependency evidence before the switch-off driver smoke check.

The complete ANV driver has not been compiled in the assistant's environment, which lacks a container engine. The build recipe deliberately fails on unavailable pinned compatibility packages instead of silently changing the stack; return that error for diagnosis if encountered.

## Acceptance remains unchanged

A–C each use one initial load plus three manual stop/reload cycles under a populated reuse pool. B/C use the same custom image with the switch off/on; CPU thread selection remains at its default and context is fixed at 32,768. D is a bounded memory holder with low CPU activity, sized after A–C. The initial baseline verifies source binding and full loading with ample headroom; it is not evidence that the reload problem is fixed.
