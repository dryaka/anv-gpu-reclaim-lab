# Case A — original image assessment

Evidence: private bundle `20261006T203843Z-case-A.tar.gz`, collected 6 October 2026, 20:38:43–20:47:45 UTC. All four requests and explicit unload checks completed. Case A reproduces partial GPU placement with a populated reclaim pool and is suitable for comparison with B.

| Request | MemAvailable before load (GiB) | GPUReclaim before load (GiB) | GPU layers | Load time (s) | Generated tokens | Evaluation rate (tokens/s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Initial | 16.85 | 21.95 | 37/66 | 17.52 | 98 | 0.628 |
| Reload 1 | 24.64 | 14.33 | 57/66 | 17.06 | 36 | 0.532 |
| Reload 2 | 17.52 | 21.52 | 38/66 | 18.01 | 58 | 0.652 |
| Reload 3 | 24.42 | 14.56 | 56/66 | 18.42 | 68 | 0.539 |

GiB values convert meminfo kB by dividing by 1,048,576. Layer counts come from `load_tensors: offloaded`, and durations/counts from completed API responses. All requests used the same model manifest, context 32,768, prompt, output cap 128 and keep-alive 30 minutes. Runner logs report default `n_threads=2`, batch/microbatch 512 and automatic flash attention. No 12-thread CPU override was introduced. Every response ended normally with `done_reason=stop`; output lengths differ, so total request durations are not directly comparable performance measurements.

Each loaded inventory confirms the original packaged ANV hash `9ecefd82942c76e227075e01a6dc78318cbb210e7fd86d2bde145501539422e4` in `/usr/lib/x86_64-linux-gnu/libvulkan_intel.so`, with Intel PTL Vulkan0 selected. Effective context stayed 32,768. The original image identity and model digest match the verified baseline. The experimental container was stopped during the case.

After each explicit stop, the collector confirmed an empty API model list and no `llama-server` in container process listing before making the next request. No pool shrinking or server restart occurred inside the measured sequence. Starting pool conditions were captured for each request, rather than assuming all reloads see identical state.

## Interpretation

MemAvailable and GPUReclaim oscillate while their sum stays approximately 38.8–39.0 GiB before the four loads. The lower MemAvailable samples coincide with 37/38 GPU layers, and the higher samples with 56/57. Runner fit logs report roughly 15–16 GiB versus 22 GiB of device availability, respectively. This is consistent with the suspected budget omission and provides a useful baseline; the disabled rebuild comparison and enabled switch are still needed to attribute any improvement to the patch.

Partial placement itself changes subsequent allocation/unload conditions. B need not reproduce the exact sequence of layer counts to match A; it must remain partial under comparable populated-pool conditions, with the intended disabled accounting and unchanged workload. Compare per-load counters and fit logs.

## Memory pressure and host evidence

The collector retained 543 memory samples. Global `pswpout` increased by 57,743 pages and `pswpin` by 1,910 pages: approximately 225.6 MiB out and 7.46 MiB in with the host's 4 KiB pages. Nonzero deltas occurred in 17 and 21 sample intervals respectively; the main swap-out bursts occurred during the initial load and reload 2. This is recorded swap activity, not a swap-free baseline. Global counters alone cannot attribute every page to the test. Final host swap occupancy was about 232.4 MiB; the container's final memory.swap.current was about 1.53 MiB.

Minimum sampled MemAvailable was about 9.45 GiB. Sampled cgroup OOM/oom_kill counters remained zero, and all readable leaf/ancestor memory.max, memory.high and memory.swap.max limits were `max`. The successfully collected kernel journal contains one perf sampling-rate adjustment; it reports no GPU reset or OOM event in this interval. Aleš subsequently confirmed that the desktop remained responsive as usual throughout Case A.

The operator observation completes the responsiveness record for A. Keep any pre-existing swap occupancy separate from new activity in B/C; compare counter deltas instead of resetting swap or dropping caches between cases.

## Next handoff

Run Case B on the same reviewed custom image with reclaim switch off. Keep the pool populated, other clients idle, and original server stopped. Return the B bundle and responsiveness observations for A and B. No rebuild, reclaim, cache drop or swap reset is needed.
