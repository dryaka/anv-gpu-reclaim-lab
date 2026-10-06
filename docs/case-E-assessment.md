# Case E — original server restored

Evidence bundle `20261006T215114Z-case-E.tar.gz`, collected 6 October 2026, 21:51:14–21:53:28 UTC. Aleš reports normal desktop responsiveness. The single fixed request completed, then the explicit model stop confirmed an empty model list and exit of the runner. The original server remains running with its model unloaded.

Original image identity matches the recorded baseline. Loaded process maps confirm the original packaged ANV library `/usr/lib/x86_64-linux-gnu/libvulkan_intel.so` with SHA-256 `9ecefd82942c76e227075e01a6dc78318cbb210e7fd86d2bde145501539422e4`, rather than the experimental driver. The enabled test container was stopped. Model digest, context 32,768, fixed request and default two CPU threads were retained.

At request start, MemAvailable was about 16.49 GiB and GPUReclaim 22.87 GiB. The original driver selected 36/66 layers on GPU. This is the expected baseline limitation with a populated pool, not a rollback failure. Inference returned 60 generated tokens with normal stop, load duration 20.28 seconds and evaluation rate about 0.571 tokens/s. E did not include a manual pool shrink.

The collector retained 136 memory samples. Global pswpout increased by 121,753 pages (about 475.6 MiB with 4 KiB pages); pswpin increased by 17,565 pages (about 68.61 MiB). Minimum sampled MemAvailable was about 11.74 GiB. Cgroup OOM/oom_kill counters stayed zero and final container swap usage was zero. All evidence commands completed successfully. The kernel journal returned no entries for this interval; no GPU reset/OOM event was recorded.

Rollback is verified: the original image/driver and normal API/model workflow were restored without replacing host drivers, removing models or modifying the original container configuration. The documented stop–shrink–reload workaround remains available as a separate later action to regain original full GPU offload when needed. Experimental images, stopped containers and private evidence should be retained until final review.
