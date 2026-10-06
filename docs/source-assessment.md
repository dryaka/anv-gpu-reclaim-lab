# Matching-source assessment

Date: 6 October 2026. This is preparation evidence, not a hardware result.

## Mesa package match

The operator reports `mesa-vulkan-drivers:amd64 25.2.8-0ubuntu0.24.04.2` in the existing Ollama image. Ubuntu publishes this exact binary version and its source descriptor at [packages.ubuntu.com](https://packages.ubuntu.com/noble/mesa-vulkan-drivers).

The corresponding upstream archive and Ubuntu packaging archive were downloaded from Ubuntu's archive. Their SHA-256 hashes match the descriptor. `dpkg-source --no-check -x` extracted the source and applied all seven distribution patches successfully. GPG signature authentication was not performed. The descriptor, archive and inspected-file hashes are retained in `versions/mesa-source.json`.

The source version is resolved. The uploaded inventory subsequently confirmed the packaged library hash, an empty `dpkg -V` result and its runtime dependencies. The runner has not yet been bound to that package because no model was loaded. Unset `VK_DRIVER_FILES` and `VK_ICD_FILENAMES` do not establish which library the runner loaded; process maps are still needed.

The agreed GitLab source workflow needs one refinement: use the exact Ubuntu source package with its distribution patches for the first build. A bare upstream tag would omit patches present in the installed package. Upstream GitLab remains the source of record; its commit pin can be added separately, but the build input is pinned by the Ubuntu archive hashes. No moving tag or current `latest` image should become a build input.

## Confirmed budget path in the patched Ubuntu source

Line numbers below refer to the extracted source with Ubuntu patches applied; file hashes are in the source manifest.

| File / function | Observed behavior |
| --- | --- |
| `src/intel/dev/xe/intel_device_info.c`, `intel_device_info_xe_query_regions`, lines 85–110 | Reads Xe memory regions. System-region free memory is `region->total_size - region->used`. The comment says Xe reports `used == 0` without elevated privileges. |
| `src/intel/dev/intel_device_info.c`, `intel_device_info_adjust_memory`, lines 1675–1686 | Replaces the free-system-memory estimate with the minimum of the existing region free value, region capacity and `os_get_available_system_memory()` result. |
| Same file, `intel_device_info_update_memory_info`, lines 1948–1965 | Queries the KMD then applies the host-memory clamp when the query succeeds. |
| `src/intel/vulkan/anv_physical_device.c`, `anv_init_meminfo` / `anv_update_meminfo`, lines 2076–2108 | Copies the adjusted free value into `device->sys.available`. Initialization also restricts heap size independently. |
| Same file, `anv_restrict_sys_heap_size`, around lines 2023–2073 | Applies the existing kernel-size handling and `ANV_SYS_MEM_LIMIT` bounds. |
| Same file, `anv_get_memory_budget`, lines 3002–3069 | Refreshes memory info, caps system availability by the total system heap size, apportions it across heaps, keeps 90% of available memory, caps the budget by heap capacity and rounds down to MiB. |

Ubuntu's ANV patch changes mmap alignment and introduces a page-size field. It does not replace the memory-availability clamp or budget calculation. The other patches affect GLX, build/tests and compiler/util code; all must still be retained in the matched build.

**Implementation implication:** adding `GPUReclaim` to `device->sys.available` after the shared Intel adjustment would have lost the original region-free bound. The ANV opt-in path must retain or freshly query that raw bound and use a single sampled `MemAvailable + GPUReclaim` input before independent caps. It must preserve initialization as well as later refresh behavior and fall back on query/parser failure. Shared utility behavior for other drivers remains unchanged. Kernel source confirmation is now complete for the identified package; actual loaded-driver binding remains pending.

## Kernel accounting check

The upstream Linux stable `v7.2.8` source was read through its GitHub mirror:

- [`mm/show_mem.c`](https://github.com/gregkh/linux/blob/v7.2.8/mm/show_mem.c), blob `43aca5a2ac990ab338e99e57f7fc4e36789fb52e`: `si_mem_available()` includes free pages minus reserves, adjusted file LRU pages, reclaimable slab and `NR_KERNEL_MISC_RECLAIMABLE`. It does not add `NR_GPU_RECLAIM`.
- [`drivers/gpu/drm/ttm/ttm_pool.c`](https://github.com/gregkh/linux/blob/v7.2.8/drivers/gpu/drm/ttm/ttm_pool.c), blob `6142f90d43e2e121ce3a66dfeeff361353f4cd85`: the normal non-DMA pool path moves pages between `NR_GPU_ACTIVE` and `NR_GPU_RECLAIM`; taking pages out of the pool reverses that transfer. Those transitions do not also increment `NR_KERNEL_MISC_RECLAIMABLE`.
- [`fs/proc/meminfo.c`](https://github.com/torvalds/linux/blob/v7.2/fs/proc/meminfo.c), blob `b2813ff13cb23bb26985bd6cfd6cd6a46cdb49ca`: exports `MemAvailable` via `si_mem_available()` and the two GPU counters separately. This file was inspected at `v7.2`, not represented as the installed Fedora build.

### Exact Fedora package check completed

The uploaded inventory identifies `kernel-7.2.8-200.fc44.src.rpm`. That exact source RPM was downloaded from [Fedora's Koji package archive](https://kojipkgs.fedoraproject.org/packages/kernel/7.2.8/200.fc44/src/kernel-7.2.8-200.fc44.src.rpm) and its payload inspected. The source RPM, tarball, spec, distribution patch and inspected-file SHA-256 values are retained in `versions/fedora-kernel-source.json`. No RPM signature authentication was performed.

The spec applies `patch-7.2-redhat.patch` and the optional `linux-kernel-test.patch`. The test patch is empty. The Red Hat patch does not change `mm/show_mem.c`, `fs/proc/meminfo.c`, `drivers/gpu/drm/ttm/ttm_pool.c` or `include/linux/mmzone.h`, and has no changes to the GPU or miscellaneous-reclaim counters. The corresponding files extracted from the source RPM's `linux-7.2.8.tar.xz` were inspected directly.

In those exact package sources, `si_mem_available()` excludes `NR_GPU_RECLAIM`, and the inspected normal non-DMA TTM reuse-pool transitions account it separately from `NR_KERNEL_MISC_RECLAIMABLE`. The proposed allowance therefore does not double-count those pool pages through that source path. Hardware validation of actual reuse, placement and memory pressure is still required; this check is not evidence that arbitrary host-wide reclaimable memory is guaranteed to satisfy an ANV allocation.

`GPUReclaim` is host-wide. It is a sampled reclaimable-pool allowance, not an allocation guarantee or a container-specific reservation. Cgroup leaf and ancestor limits, GPU type and the raw Xe bound still matter.
