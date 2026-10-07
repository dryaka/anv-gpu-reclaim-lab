# Case B — custom ANV with switch off

Evidence: private bundle `20261006T205535Z-case-B.tar.gz`, collected 6 October 2026, 20:55:35–21:02:28 UTC. Aleš reports that the desktop remained responsive as usual. All four fixed requests and explicit unload checks completed.

| Request | MemAvailable before load (GiB) | GPUReclaim before load (GiB) | GPU layers | Load time (s) | Generated tokens | Evaluation rate (tokens/s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Initial | 18.23 | 20.80 | 41/66 | 20.87 | 52 | 0.615 |
| Reload 1 | 23.61 | 15.66 | 54/66 | 18.57 | 41 | 0.563 |
| Reload 2 | 19.24 | 20.07 | 43/66 | 18.36 | 38 | 0.620 |
| Reload 3 | 19.16 | 20.11 | 43/66 | 18.58 | 51 | 0.605 |

GiB values convert meminfo kB by dividing by 1,048,576. Every loaded inventory confirms the reviewed custom ANV library hash `0efddde0239a00350d75491fc49e46e5a155e3f5ed5f18f0ebe48620542b0d37` under `/opt/mesa-anv-test`. Each runner reports `enabled=0 valid=1` and `selected=original`. The reclaim pool is observed by diagnostics but is not added to the budget. Recorded initial final budgets are 17,610,833,920; 22,814,916,608; 18,606,981,120; and 18,493,734,912 bytes, respectively. Intel PTL Vulkan0 was selected.

Model digest, prompt, output cap 128, context 32,768 and keep-alive 30 minutes match A. Effective context stays 32,768, default CPU threads stay at two, and the custom image is the reviewed build. The original server is stopped. The explicit stop sequence confirms the model list empty and runner exited before every subsequent request. No pool shrinking or container restart occurs within B.

## Comparison with A

Both original ANV and the disabled custom ANV choose partial offload on every load with substantial reuse-pool memory present. B starts with approximately 39.0 GiB in MemAvailable plus GPUReclaim, compared with A's 38.8 GiB. Its per-load sum stays roughly 39.0–39.3 GiB. Different pool/MemAvailable splits explain why exact layer counts need not match A; the smaller pool/higher MemAvailable run again gets more GPU layers.

The disabled rebuild has not independently restored full offload. This is the expected qualitative control result and permits the enabled-switch comparison. It does not prove bit-for-bit budget equivalence or a performance improvement: live counters and generated token counts differ, and rebuilding is itself a variable controlled by using the identical custom image in B/C.

## Memory pressure and host evidence

The collector saved 413 samples. Global pswpout increases by 53,239 pages (about 208.0 MiB with 4 KiB pages), and pswpin by 738 pages (about 2.88 MiB). A already left some swap occupied; these are new activity deltas, not total occupancy. Global activity cannot be wholly attributed to the test. The sampled minimum MemAvailable is about 9.33 GiB. Final container memory.swap.current is zero; cgroup OOM and oom_kill counters remain zero.

All command captures completed successfully. The kernel journal records Bluetooth input-device registration and no GPU reset/OOM event during the interval. Aleš's normal-responsiveness observation covers the desktop criterion for B; normal responsiveness was also confirmed for A. Swap activity remains a baseline condition to compare against C, not a claim of swap-free execution.

## Next handoff

Proceed to C with the exact same custom image ID and switch 1. Retain B's stopped container under another name, preserve its model mount and SELinux level, and change the experiment switch when creating the C container. Keep clients idle; no manual reclaim, rebuild, swap reset or cache drop. Full offload on all three reloads and successful inference are required before a preliminary pass.
