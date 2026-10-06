# Experiment status and next handoff

Updated: 6 October 2026, after the uploaded inventory.

| Plan step | State |
| --- | --- |
| 1 — environment inventory | Received and assessed. Operator memory tests used defaults; separate CPU test used 12 threads, which will not be carried into this comparison. |
| 2 — loaded driver, matched source and kernel/limits check | Exact Ubuntu Mesa source and exact Fedora kernel source checked; image digests, packaged ANV hash and resource limits recorded. Device exposure and loaded-runner binding remain open. |
| 3 — opt-in ANV implementation | Pending runtime binding; no experimental patch exists yet. |
| 4 — build and comparison bundle | Pending step 3. Read-only inventory and pinned Mesa source-fetch tooling are ready. |
| 5–13 — build, hardware tests, analysis and decision | Not started. |

## Aleš: two remaining read-only checks

```bash
podman exec ollama sh -c 'id; ls -ld /dev/dri; ls -l /dev/dri'
podman exec ollama ollama show hf.co/bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF:Q6_K --parameters
```

Return the output here. These do not load a model, change the service or replace the container. The first resolves missing device evidence in the inspect summary; the second establishes saved model parameters underlying request defaults. See [inventory assessment](inventory-assessment.md).

Actual ANV process maps remain to be captured during an appropriate existing or small-model baseline run after device access is resolved. Do not load the large model just for these checks. Preserve the current working container.

Raw machine evidence remains outside this public repository. The uploaded inventory has not been committed. Selected package, hash and resource observations are in `versions/environment.json`; exact Fedora source evidence is in `versions/fedora-kernel-source.json`.

## Assistant: next work

1. Resolve device access and bind the actual runner library to the confirmed package/source.
2. Implement and test the default-off ANV patch, preserving raw Xe/heap bounds, reserves and rounding.
3. Provide the multi-stage Containerfile, driver verification, identical A–C request/cycle tools and rollback commands.

The unchanged matrix is one initial load plus three manual stop/reload cycles for each of A, B and C. Context will be explicitly fixed at 32,768 for the comparison; the separate 12-thread CPU test is not imported. Case D remains a bounded anonymous-memory holder with low CPU activity, sized after A–C results. No timeout-driven scenario is required.
