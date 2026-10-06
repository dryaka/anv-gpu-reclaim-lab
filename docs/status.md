# Experiment status and next handoff

Updated: 6 October 2026.

| Plan step | State |
| --- | --- |
| 1 — environment inventory | Partial: kernel release, image ID, runtime OS and package versions received. |
| 2 — loaded driver, matched source and kernel/limits check | In progress: exact Ubuntu source extracted and inspected; upstream stable kernel paths checked. Loaded library, Fedora delta and runtime configuration remain unresolved. |
| 3 — opt-in ANV implementation | Pending step 2; no experimental patch exists yet. |
| 4 — build and comparison bundle | Pending step 3. Read-only inventory and pinned source-fetch tooling are ready. |
| 5–13 — build, hardware tests, analysis and decision | Not started. |

## Aleš: collect the remaining inventory

Clone the repository and select the experiment branch:

```bash
git clone git@github.com:dryaka/anv-gpu-reclaim-lab.git
cd anv-gpu-reclaim-lab
git switch experiment/anv-gpu-reclaim
python3 scripts/collect-inventory.py --container ollama
```

The collector requires Python 3 and the existing Podman CLI. It records command failures rather than installing anything. It leaves services and model state as they are. Run it while the existing container is in its normal state; if a model is already loaded, its process maps may establish the loaded driver. If no runner is present, the output explicitly marks selection unconfirmed. Do not load the large model merely for inventory.

It prints the path to `inventory.json` in a sibling evidence directory outside the repository. Review the file before returning it to the assistant. It includes local paths and device/process details. Arbitrary environment variables, proxies, credentials, labels, full command lines and full inspect output are excluded. Known environment values and paths can still contain identifying information, so the file is not automatically safe for public publication.

The report should provide:

- The image's registry digest when available. The supplied local image ID is retained separately; it cannot be substituted for a registry manifest digest.
- Installed Mesa/source versions, packaged library hashes, manifests, dependencies and readable loaded-library maps.
- Host DRM driver and GPU PCI identity, Fedora source RPM name and available kernel configuration.
- Container mounts, device settings, SELinux settings, relevant environment and resource settings, plus leaf/ancestor cgroup memory limits where readable.
- Host/container memory-counter snapshots. These are inventory snapshots, not timed experiment evidence.

Also provide **the inference options currently used with the selected model** (thread count, batch size, context, request/API options or Modelfile settings), with credentials removed. Container inspection cannot reveal options supplied per request. The intended context remains 32,768; no thread count is assumed from earlier experiments.

If the mapped driver is unavailable, the assistant will request a focused check at an appropriate existing or small-model run. Do not install `vulkaninfo` or change the running image for this inventory. Later driver-selection probes will remain outside timed measurements.

## Assistant: next work after the handoff

1. Bind the observed library to its package/source and immutable image; check actual limits and launch settings.
2. Resolve the Fedora kernel source and verify no double-counting of TTM pool memory.
3. Implement and test the default-off ANV patch, preserving Xe/heap bounds, reserves and rounding.
4. Provide the multi-stage Containerfile, driver verification, identical A–C request/cycle tools and rollback commands.

The unchanged matrix is one initial load plus three manual stop/reload cycles for each of A, B and C. Case D remains a bounded anonymous-memory holder with low CPU activity, sized only after A–C results. No timeout-driven reload scenario is required.
