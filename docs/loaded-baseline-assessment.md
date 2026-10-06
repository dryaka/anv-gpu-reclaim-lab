# Loaded baseline assessment

The 6 October loaded-baseline bundle completes source binding for step 2. Raw logs and machine inventory remain outside Git.

| Check | Evidence |
| --- | --- |
| Actual runner | `llama-server` mapped `/usr/lib/x86_64-linux-gnu/libvulkan_intel.so`; its hash matches the packaged library recorded in the manifest. |
| GPU used | Runner selected Vulkan0, Intel Graphics PTL, and reported 66/66 layers offloaded. Multiple other ICD libraries were also mapped during loader enumeration; their mappings alone do not mean those drivers were used for inference. |
| Context | Runner logs and `/api/ps` both confirm 32,768. |
| Request | Completed; 65 prompt tokens, 45 generated tokens; load duration approximately 18.75 seconds. |
| CPU/batch defaults | Two inference threads; batch and microbatch 512. These observations are not replaced with the separate 12-thread CPU test setting. |
| Memory pressure | 120 samples; swap-in/out deltas zero; no container OOM or OOM-kill events. |
| Generation speed | About 0.48 tokens/s from API durations; runner rounded it to 0.47. Slow generation is recorded as a baseline observation, not fixed or explained by this accounting experiment. |

Host `GPUActive` rose from about 1.26 GiB to 26.75 GiB, while `MemAvailable` fell from about 38.49 GiB to 13.05 GiB. The small initial reuse pool fell from about 0.84 GiB to 0.23 GiB. There is no post-stop sample in this bundle, so it does not establish the populated-pool reload behavior and is not counted as case A.

The full-offload identity check used the original driver with ample initial available memory. The accounting hypothesis still needs A/B/C comparisons under a populated pool. Operator desktop responsiveness and kernel reset/error evidence were not included in this bundle; the absence of recorded cgroup OOMs does not establish all host acceptance criteria.
