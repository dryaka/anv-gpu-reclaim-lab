# Case D — four-GiB memory holder

Evidence bundle `20261006T213758Z-case-D.tar.gz`, collected 6 October 2026, 21:37:58–21:41:38 UTC. Aleš reports normal desktop responsiveness. The initial load and one measured explicit stop/reload both completed with 66/66 layers on GPU, context 32,768 and the same model/request settings as C.

| Request | MemAvailable before load (GiB) | GPUReclaim before load (GiB) | GPU layers | Load time (s) | Generated tokens | Evaluation rate (tokens/s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Initial under holder | 30.42 | 4.63 | 66/66 | 18.46 | 46 | 0.493 |
| Reload under holder | 28.03 | 6.92 | 66/66 | 20.49 | 35 | 0.495 |

The same custom driver and image were retained, with enabled accounting and the original container stopped. Diagnostics report `enabled=1 valid=1`, adding the reclaim allowance within the Xe region bound. First recorded post-reserve budgets were 33,857,470,464 and 33,784,070,144 bytes. Loaded API records report size=size_vram=25,304,152,144 bytes. No pool shrinking or server restart occurred inside D.

## Holder validation

The private anonymous allocation was exactly 4,294,967,296 bytes, touched page by page and held across both requests and the intervening stop/reload. At readiness and every subsequent readable status sample, VmRSS remained 4,219,052 KiB (about 4.02 GiB including Python overhead) and VmSwap stayed zero. The holder was neither pinned nor locked. Recorded CPU counters increased from 12 user/79 system ticks to 12 user/80 system ticks, demonstrating negligible ongoing CPU activity after the one-time allocation/touch.

Before allocation, MemAvailable was about 34.42 GiB; after readiness it was 30.42 GiB. GPUReclaim stayed close to 4.63 GiB through allocation. After the final model stop, the collector sent SIGTERM to the holder (exit code -15, expected cleanup). Its status disappeared, and MemAvailable rose from approximately 11.89 to 15.91 GiB after release. The allocation was therefore actually resident during the test and subsequently freed.

## Memory pressure and host observations

There are 221 memory samples. Global pswpout increased by 80,438 pages (about 314.2 MiB with 4 KiB pages), and pswpin by 3,786 pages (about 14.79 MiB). Global activity cannot be entirely attributed to the test. The holder itself did not swap. The sampled minimum MemAvailable was about 8.49 GiB. Final container swap usage was about 2.08 MiB; cgroup OOM/oom_kill counters remained zero.

All evidence commands succeeded. The kernel journal returned no entries for the interval, and no reset/OOM event was recorded. Aleš's normal-responsiveness observation supplies the desktop check. There is still swap activity, so this is not a swap-free pressure test.

## Meaning and remaining work

D demonstrates successful full offload and inference while a verified 4 GiB low-CPU resident workload is held. Its measured reload starts with a smaller pool than C's strongest large-pool reload; D is a reduced-headroom check, not another equally severe reproduction of the budget omission. It cannot establish behavior under larger workloads, simultaneous models, stricter cgroups or other kernels/GPUs.

The placement goal has been met in C and D. The increased global swap-out in C remains a qualification; no throughput improvement or production suitability follows from layer counts alone. Rollback E and the final result/limitation review remain outstanding.
