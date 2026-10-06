# Experimental ANV implementation

Patch: `patches/0001-anv-experimental-gpu-reclaim.patch`, against Ubuntu Mesa source `25.2.8-0ubuntu0.24.04.2` after its complete distribution patch series.

`ANV_EXPERIMENTAL_GPU_RECLAIM=1` enables the change. It defaults off and applies only on Linux to Xe integrated GPUs without local VRAM. Other shared Intel code, HASVK, other Vulkan drivers and `os_get_available_system_memory()` are unchanged.

Both ANV memory initialization and refresh pass through the new helper. A copy of the Intel device information is queried through the existing Xe region-query function to recover `region_free` and capacity before the shared Intel host-availability clamp. The copy avoids changing shared device-info state or adding an opt-in behavior to its public utility API. This introduces one additional region query on the active experimental path; hardware results must account for the changed query timing.

The helper reads `/proc/meminfo` into one bounded buffer with one `read()` call and parses `MemAvailable` and `GPUReclaim` together. It rejects incomplete snapshots, duplicate relevant counters, negative values, wrong units, decimal/byte/sum overflow, and invalid region bounds. Missing `GPUReclaim` contributes zero. Failed input or region queries preserve the original clamped ANV value. It never adds `GPUActive`.

For valid enabled samples the new host availability is:

`min(MemAvailable + GPUReclaim, raw Xe region free, raw Xe region size)`.

The existing system-heap configuration, `ANV_SYS_MEM_LIMIT`, total heap cap, heap apportionment, 10% reserve, heap capacity and MiB rounding remain in the original budget code. Reclaim is not added to the already-clamped budget. The generic Vulkan physical-device base remains the first member of the ANV structure.

With the switch off and diagnostics off, the extra region query and meminfo read are skipped. `ANV_EXPERIMENTAL_GPU_RECLAIM_DEBUG=1` enables diagnostics through the first budget query per physical device: switch/validity, sampled counters, raw bounds, selected input and final heap budgets. Debugging an off-switch B run performs observational queries but does not replace its availability. Subsequent inference budget queries do not keep emitting these diagnostics.

## Validation and limits

The patch applies cleanly to the matched, distribution-patched source with whitespace checking. The production helper header is extracted directly from the patch and compiled in the focused C test with warnings as errors and undefined-behavior sanitization. Tests cover missing, reordered, duplicate, malformed and overflowing counters, ignored GPUActive, and retained raw-region bounds. The exact production integration helper is also compiled with mocked OS/Xe queries to test off-switch bypass, enabled bounds, conservative query/parser failure, observational off-switch diagnostics, and exclusion of local-VRAM/non-Xe devices.

The initial preparation had twelve passing local tests, including the existing evidence/privacy checks. Subsequent collection/lifecycle/rollback checks bring the total to 23. Aleš completed the full ANV build and hardware sequence; driver hashes and loaded process maps were verified. See [final result](experiment-results.md) for placement outcomes, host-pressure qualifications and rollback evidence.

The source and Ollama base are pinned, and Meson is version-pinned. Other build dependencies are obtained from Ubuntu's configured repositories and recorded in the image, rather than locked to a historical repository snapshot. The recipe therefore does not promise bit-identical future builds. It deliberately requires the observed libdrm development version and Vulkan-loader version; if an archive no longer offers them, return the build failure rather than silently substituting a newer stack. B and C use the same resulting image to control this variable.

The source-level Fedora check supports excluding the inspected TTM pool pages from MemAvailable. The counter remains global and sampled; another allocation can consume the allowance. The experiment retains original reserves and must still check failures, swapping and desktop behavior. It does not provide a memory reservation or solve multi-container admission control.
