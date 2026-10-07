# ANV GPU reclaim experiment — final result

Date: 6 October 2026. Operator: Aleš Dryák. Implementation and evidence analysis: ChatGPT assistant.

## Result and decision

The accounting hypothesis is supported on this tested stack. The original ANV driver and the rebuilt driver with the experimental switch off consistently chose partial GPU placement with populated TTM pools. Enabling the switch in the identical custom image restored 66/66 layers on the initial load and all three explicit reloads. The final reload again had a large pool and low MemAvailable, so the result is not explained solely by earlier unloads freeing the pool. Diagnostics connect the improvement to adding GPUReclaim within the existing raw-region, heap, reserve and rounding limits.

A verified 4 GiB resident, low-CPU background workload also completed its initial request and one reload with full offload. Rollback restored the original image and packaged driver, successful inference and the original partial-placement behavior. Aleš reported normal desktop responsiveness throughout A–E. No cgroup OOM or GPU reset was recorded.

This is a successful **placement experiment with qualified host acceptance**, not a production-ready general fix. All cases recorded some global swap activity, and C recorded more swap-out than A/B. The evidence does not establish the absence of test-attributable sustained swapping because global counters do not fully attribute activity. Normal responsiveness and no observed OOM/reset are positive observations, but do not erase that limitation.

### Owner decision — 7 October 2026

Aleš considers the controlled experiment complete and will not pursue further swap-out investigation. Memory pressure during full model allocation could drive both TTM-pool reclaim and anonymous-page swap-out, but this is an unproven explanation. Some activity also occurred during inference. The recorded measurements and qualified host acceptance above remain unchanged; the cause is unresolved and is not a blocker for the chosen opt-in local trial.

The next steps are to prepare a clean upstream change separately, retain a specific Ollama container build for approximately one month of use on this system, then decide whether to post the patch upstream. The observation period starts when regular use of that build begins; no upstream submission is authorized by this decision. Keep the daily-use image identifiable and fixed while preparing the upstream change. If preparation changes accounting behavior, validate that change before replacing the running build.

The experimental switch remains default off. Preserve the original image and workaround. Repository review/merge preserves the experiment; it does not deploy the driver or make it a general default. A broader workload/kernel/GPU matrix and permanent deployment remain separate decisions.

## Tested stack and workload

- Host: Fedora KDE, Intel Panther Lake integrated GPU, Xe driver, kernel `7.2.8-200.fc44.x86_64`, approximately 48 GB nominal RAM.
- Runtime: rootless Podman; Ollama 0.34.4 in Ubuntu 24.04.5; Mesa source `25.2.8-0ubuntu0.24.04.2`, including its distribution patch series.
- Original image configuration digest: `7fe01b0ef22e342fcbcb61e89d39de511609f078c30754a3a0bee7bb0f20a5c2`.
- Pinned amd64 base manifest: `sha256:4be1eaabf0dd0152bfbb780347e2888b5fe86ec25d0faa3eb4b1a956173736fb`.
- Custom image ID: `2687fe2ef85d0b19e60318e731e4af0309370cb8c81efd4233609eb72866bda6`, built from lab commit `b14f909fe917567629c5fc5a4176feb37e381d4f`; B/C/D used this image.
- Custom ANV SHA-256: `0efddde0239a00350d75491fc49e46e5a155e3f5ed5f18f0ebe48620542b0d37`.
- Original ANV SHA-256: `9ecefd82942c76e227075e01a6dc78318cbb210e7fd86d2bde145501539422e4`.
- Patch SHA-256: `d59b3f8d7608fec6a34cb3eca715b5c391e5c13c7bdc9e1321df8f90f114e157`.
- Model: `hf.co/bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF:Q6_K`, manifest digest `c44571a7ec4632c3d7494a7317a9c70949ce475d2acce2586046d585f244839f`.
- Every measured request: context 32,768; prompt `Reply with one short sentence: the GPU memory test is ready.`; stream false; keep-alive 30 minutes; output cap 128.
- No new thread, layer, batch, cache or fit override. Effective CPU threads remained two; the separate 12-thread CPU experiment was excluded.

A/B/C each contain an initial request and three explicit model-stop/reload cycles. D contains an initial request and one explicit reload with the memory holder present. E contains one original-server request. All 15 measured requests completed and every corresponding explicit model stop confirmed both an empty API model list and runner exit. No manual pool shrink or server restart occurred inside a measured case. Container changes occurred between cases to apply the intended driver/switch or rollback.

The early source-binding baseline and small-model smoke check were separate from these measurements. The source-binding baseline demonstrated full offload with ample headroom. The smoke verified custom-driver loading and switch-off behavior; its log collector failure was corrected without invalidating the completed inference.

## Case outcomes

| Case | Driver / switch | GPU layers: initial, then reloads | Request result | Operator observation |
| --- | --- | --- | --- | --- |
| A | Original packaged ANV | 37/66, 57/66, 38/66, 56/66 | All completed | Normal responsiveness |
| B | Custom ANV, off | 41/66, 54/66, 43/66, 43/66 | All completed | Normal responsiveness |
| C | Same custom ANV, on | 66/66, 66/66, 66/66, 66/66 | All completed | No desktop degradation |
| D | Same custom ANV, on; 4 GiB holder | 66/66, 66/66 | Both completed | Normal responsiveness |
| E | Original image restored | 36/66 | Completed; original driver confirmed | Normal responsiveness |

A/B provide the problematic-placement controls under comparable combined available/reclaim headroom. Their exact layer counts vary with the pool/MemAvailable split. B's unchanged selected input and partial placement show that rebuilding alone did not restore full offload. C uses the same custom binary and changes the accounting switch. Its first two reloads have smaller pools, but reload 3 starts with approximately 15.81 GiB MemAvailable and 23.26 GiB GPUReclaim and still selects 66/66 layers.

For that final C reload, diagnostics show an original input around 16.95 billion bytes, selected input around 41.93 billion bytes and rounded budget 37,734,055,936 bytes. The separately queried raw Xe region bound remains higher. C/D API records also report model size equal to size_vram, consistent with full layer offload.

D verifies reduced headroom and a real resident holder, not another equally large-pool reproduction. The allocation was exactly 4 GiB; measured VmRSS stayed approximately 4.02 GiB including process overhead, VmSwap remained zero, and holder CPU counters added only one tick during the recorded hold. The collector released it after the final stop, confirmed its process status disappeared and observed corresponding available-memory recovery.

E restores the original packaged ANV and successful fixed inference. Its partial placement is expected with the still-populated shared pool; no shrink was silently inserted to make rollback appear fully offloaded. The original server is left running, with the test model unloaded. Both experimental containers are retained stopped for reference.

## Host pressure and performance

Global swap deltas below use 4 KiB pages. They measure activity during each case, not total swap occupancy and not exclusively test-process activity.

| Case | Swap-out (MiB) | Swap-in (MiB) | Minimum sampled MemAvailable (GiB) | Recorded cgroup OOM / GPU reset |
| --- | ---: | ---: | ---: | --- |
| A | 225.6 | 7.46 | 9.45 | None |
| B | 208.0 | 2.88 | 9.33 | None |
| C | 850.1 | 9.59 | 11.56 | None |
| D | 314.2 | 14.79 | 8.49 | None |
| E | 475.6 | 68.61 | 11.74 | None |

C's swap-out is concentrated in its initial run and last reload; the middle reloads add little or none. Higher C swap-out is a material qualification, even though sampled available memory and desktop usability remain acceptable. Global attribution, allocator/kernel decisions, pre-existing swap state and unrelated host activity prevent a definitive cause from these measurements alone. No attempt was made to reset swap or drop caches between cases.

Kernel journal capture succeeded for every measured case. It returned perf sampling-rate adjustments or input-device registration in A–C and no entries in D/E; no GPU reset/OOM event was recorded. Cgroup OOM/oom_kill counters stayed zero. These are observed intervals, not a guarantee of future behavior.

C evaluation rate was approximately 0.46–0.51 tokens/s; D approximately 0.49–0.50 tokens/s. Partial A/B placement produced roughly 0.53–0.65 tokens/s in these short requests. The patch therefore establishes placement consistency, not a throughput benefit. Generated lengths vary and no deterministic performance protocol, thread tuning, thermal control or repeated benchmark design was used. Do not infer that full GPU placement is the fastest configuration for this model on this iGPU.

## Validation and limits

The full patched ANV driver compiled locally on Aleš's host, and loaded process maps plus library hashes confirmed the selected driver in every measured run. Runtime dependencies resolved. The repository has 23 passing local tests covering production parser/checked limits, exact opt-in helper behavior, inventory privacy/behavior, invalid UTF-8 log capture, sequencing/unload checks, bounded holder lifecycle and one-request rollback. Production helper tests compile with warnings as errors and undefined-behavior sanitization. Syntax, manifest parsing and whitespace checks pass. CI on collector commit `72941cda9ac3c6cd825b94b8e7c00c7a25393824` succeeded.

The experiment covers one notebook, one kernel/runtime stack, one model/quantization/context and a modest background-memory workload. TTM state changes naturally across cases; counters are sampled, not atomic reservations. All readable cgroup memory limits in the assessed setup were unconstrained; stricter cgroups were not tested. The patch remains Linux Xe iGPU-specific, changes no shared Mesa utility, preserves limits, and falls back to the original estimate on unusable input. It adds an extra raw-region query when the experimental/diagnostic path is active.

Source/base-image/Meson inputs are pinned, but all apt dependencies are not historically snapshot-locked. Build/source checksums do not substitute for source-package signature verification, which was not performed. Future rebuilds or versions need fresh driver/hash and behavior checks.

Raw bundles contain machine/process details and remain outside Git; this report retains reviewed measurement summaries. Retain artifacts and experimental images through the local observation period and the later upstream-submission decision.

## Supporting records

- [Original-image case A](case-A-assessment.md)
- [Disabled custom-driver case B](case-B-assessment.md)
- [Enabled custom-driver case C](case-C-assessment.md)
- [Bounded-memory case D](case-D-assessment.md)
- [Original-server rollback E](case-E-assessment.md)
- [Implementation](implementation.md), [source assessment](source-assessment.md), [build/runtime instructions](build-and-runtime.md)
