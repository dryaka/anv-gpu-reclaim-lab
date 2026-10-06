# Case C — enabled reclaim accounting

Private evidence bundle `20261006T212133Z-case-C.tar.gz`, collected 6 October 2026, 21:21:33–21:30:05 UTC. Aleš reports no desktop experience degradation. All four requests and confirmed explicit unloads completed.

| Request | MemAvailable before load (GiB) | GPUReclaim before load (GiB) | GPU layers | Load time (s) | Generated tokens | Evaluation rate (tokens/s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Initial | 18.64 | 20.02 | 66/66 | 17.47 | 49 | 0.509 |
| Reload 1 | 36.68 | 2.39 | 66/66 | 17.72 | 52 | 0.500 |
| Reload 2 | 36.35 | 2.65 | 66/66 | 17.72 | 36 | 0.500 |
| Reload 3 | 15.81 | 23.26 | 66/66 | 16.46 | 63 | 0.462 |

The same reviewed image and ANV hash used in B were used in C. Every runner reports `enabled=1 valid=1`. The selected input is MemAvailable plus GPUReclaim, within the independently queried raw Xe region bound. The initial input rises from 20,013,342,720 to 41,510,453,248 bytes, giving a rounded post-reserve budget of 37,358,665,728 bytes. Reload 3 is the strongest reload check: original input 16,953,962,496 bytes plus approximately 24,972,800,000 bytes in the reclaim pool yields selected input approximately 41,926,700,000 bytes and final budget 37,734,055,936 bytes. The raw region-free bound stays above the selected input. Configured heap limits and ten-percent reserve remain applied.

Model digest and request settings match A/B. Effective context is 32,768 with default two CPU threads. Every API model record reports size=size_vram=25,304,152,144 bytes, consistent with the 66/66 layer logs. Original and preserved switch-off servers are stopped. No manual shrink or server restart occurred between measured requests.

A/B choose partial placement under populated pools; C stays fully offloaded. C's first two unloads leave smaller pools and higher MemAvailable, so reloads 1/2 alone would weakly test the omission. Reload 3 again starts with a large pool and low MemAvailable, and still selects full offload. Together with switch diagnostics and the identical B/C image, that supports the causal accounting explanation.

## Host measurements and limits

There are 512 sampled memory records. Global pswpout increases by 217,627 pages, about 850.1 MiB; pswpin increases by 2,454 pages, about 9.59 MiB with 4 KiB pages. New swap-out is concentrated in the initial run (445.2 MiB) and reload 3 (404.7 MiB). Reload 1 adds about 0.23 MiB; reload 2 adds none. The largest sampled swap-out interval is about 96.5 MiB. These are global counters and cannot by themselves assign all activity to the test.

The minimum sampled MemAvailable is about 11.56 GiB. Cgroup OOM/oom_kill counters remain zero. Final container swap usage is about 1.82 MiB. All evidence commands completed successfully, and the kernel journal records a perf sampling-rate adjustment without a GPU reset/OOM event during the interval. Aleš reports normal desktop behavior.

The placement objective is met, including all three reloads. Host acceptance remains qualified: C records more swap-out than A (~225.6 MiB) and B (~208.0 MiB), despite normal responsiveness and no OOM/reset. Do not infer that the patch eliminates memory pressure, improves token speed or is ready for permanent use. Token rate is about 0.46–0.51/s; generated lengths differ, and this experiment targets reload placement rather than performance tuning.

## Bounded workload handoff

Use a 4 GiB low-CPU anonymous memory holder for D, with a pre-allocation guard requiring at least 12 GiB current MemAvailable. The measured C minimum suggests a moderate first pressure test, not a capacity guarantee. Record actual holder residency/swap, budget decisions, pool changes and host swap deltas. D follows the same model request and includes one explicit reload while the holder remains present. E then verifies rollback to the original container. A final decision requires D/E and review of swap behavior and limitations.
