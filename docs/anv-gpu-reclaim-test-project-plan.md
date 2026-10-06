# ANV GPU Reclaim Accounting Test Project Plan

Date: 6 October 2026

Project: LLM lab

Owner and test operator: Aleš Dryák

Implementation and analysis: ChatGPT assistant

Status: Test approach agreed; environment inventory is the next action

## Objective

Determine whether including unused GPU reuse-pool memory in ANV’s system-memory availability estimate allows Ollama to reload the selected model with full GPU offload after a manual model stop, without manually shrinking the TTM pool.

The experiment will use a separate Podman image containing a switchable ANV patch. Acceptance requires successful model loading and inference, consistent placement across reloads, and acceptable host behavior. A larger reported memory budget alone is insufficient.

## Background and working hypothesis

The existing report, `vulkan-igpu-memory-management-findings.md`, records partial GPU offload after model unloading leaves a large TTM reuse pool. Targeted shrinking raises `MemAvailable`, and subsequent loads achieve full offload.

Source inspection identified a path in which ANV caps system-memory availability using Linux `MemAvailable`, applies its own reserve, and reports a Vulkan budget. The llama.cpp runner fits the model before real allocation, so later reuse or reclaim does not improve the chosen placement. The proposed experiment changes the host-availability input to `MemAvailable + GPUReclaim`.

This is a hypothesis to validate against the installed binaries. Mesa 25.2.0 and current source were inspected, but the tested container’s exact Mesa build and host kernel still need identification. The previous Ollama investigation used version 0.34.4 and its pinned llama.cpp dependency.

## Environment and scope

| Item | Starting point |
| --- | --- |
| Host | Fedora KDE notebook, Intel Panther Lake integrated GPU, 48 GB nominal RAM |
| Runtime | Rootless Podman; existing container named `ollama` |
| Baseline model | `hf.co/bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF:Q6_K` |
| Context | 32,768 tokens; verify effective context in each run |
| Known settings | `OLLAMA_IGPU_ENABLE=1`, `ANV_SYS_MEM_LIMIT=90`; confirm current values |
| Model storage | Existing host model directory; confirm its actual mount mapping |
| Experimental container | Proposed name `ollama-anv-test`, API bound to `127.0.0.1:11435` |
| Changed component | Mesa’s ANV Intel Vulkan driver in the test image |
| Host components | Existing Linux kernel, Xe driver and TTM pool |

Mesa is the userspace graphics project. ANV is its Intel Vulkan driver. Xe and TTM run in the host kernel. The test driver will be installed inside the experimental image under a separate prefix and selected explicitly through its Vulkan driver manifest.

The first experiment covers this notebook, one model and the current runtime stack. Kernel modifications, general Mesa-wide behavior changes, upstream submission and permanent replacement of the working image are follow-up decisions.

## Responsibilities

**Aleš** runs commands on the Fedora notebook, controls local containers and workloads, builds the image with Podman, observes responsiveness and returns the evidence. He decides whether the result is suitable for regular use.

**Assistant** supplies the inventory and execution instructions, identifies the matching source, implements and reviews the patch, prepares the Containerfile and test scripts, diagnoses build failures, analyzes the returned evidence and writes the outcome report. Hardware behavior is validated by Aleš’s runs; the assistant does not currently have direct access to the notebook.

## Work sequence and handoffs

| Step | Owner | Work | Completion evidence and next handoff |
| --- | --- | --- | --- |
| 1 | Aleš | Collect host, container, package and runtime inventory. Provide the current launch command or configuration with credentials removed. | Inventory output to assistant. |
| 2 | Assistant | Identify the ANV library actually loaded by the runner; resolve its source revision and distribution patches. Check the exact kernel’s reclaim accounting and container memory limits. | Version manifest and a confirmed source path for the change. Request only any missing targeted diagnostics. |
| 3 | Assistant | Implement the opt-in ANV change, diagnostics and focused parser/arithmetic tests. Review that existing limits remain effective. | Patch, implementation notes and local test results. |
| 4 | Assistant | Prepare a reproducible multi-stage Containerfile, runtime commands, evidence collector and rollback instructions. | Build and test bundle ready for Aleš. |
| 5 | Aleš | Build the test image locally; return the build log and image identity. | Successful image build, or a build failure for assistant diagnosis. |
| 6 | Assistant | Resolve any build issues and check the completed build’s version and dependency evidence. | Image ready for GPU validation. |
| 7 | Aleš | Stop the normal Ollama container, start the test container with the switch off, and run driver-selection and small-model smoke checks. | ANV library/manifest confirmation, startup logs and successful inference. |
| 8 | Assistant | Check that the intended driver was loaded and the disabled switch preserves baseline behavior. | Proceed to the comparison, or fix the driver/build mismatch. |
| 9 | Aleš | Run cases A, B and C from the test matrix, one at a time, and return the evidence bundles. | Recorded pool conditions, placement, requests and host measurements. |
| 10 | Assistant | Compare the results and identify whether the accounting change explains the difference. | Preliminary pass, fail or inconclusive result. |
| 11 | Aleš | If the core test passes, run the bounded background-workload case and verify rollback. | Additional evidence and confirmation that the normal container works again. |
| 12 | Assistant | Produce the final report, limitations and recommendation; update this plan’s status. | Reproducible result and retained patch/build/run evidence. |
| 13 | Aleš | Decide whether to retain the experimental image, extend the test or pursue an upstream proposal. | Recorded next decision. |

Steps 3 and 4 depend on the inventory and source match. Image compilation can be slow; complete it before collecting memory measurements and let the host settle afterward. No date-based schedule is imposed.

## Patch requirements

- Use an ANV-specific experimental switch, disabled by default. Proposed name: `ANV_EXPERIMENTAL_GPU_RECLAIM=1`. This is a new patch feature, not an existing Mesa option.
- Limit activation to the Linux integrated-GPU system-memory budget relevant to this experiment.
- Read `MemAvailable` and `GPUReclaim` together from one `/proc/meminfo` read. These are still sampled counters, not an atomic memory reservation.
- Missing `GPUReclaim` means zero added allowance. Unusable input must fall back conservatively; use checked arithmetic and correct kB-to-byte conversion.
- Add reclaimable memory to the host-availability input before applying independent limits. Preserve or recompute the original Xe region bound rather than adding memory to an already-clamped final budget.
- Retain heap capacity, the configured system-memory heap limit, ANV’s reserve and budget rounding. Do not include `GPUActive` in the extra allowance.
- Keep the existing shared `os_get_available_system_memory()` behavior for other callers. The exact implementation point depends on the installed source.
- Add opt-in diagnostics for switch state, input counters, relevant limits and final budget. Avoid continuous verbose logging during normal inference.
- Cover missing/malformed fields, overflow and retained limits with focused tests. Confirm switch-off equivalence through the hardware comparison.

Before implementation, verify that the installed kernel does not already include the same pool pages in `MemAvailable`. If it does, revisit the design instead of adding the counter twice.

## Build and runtime design

Pin the existing Ollama image by an immutable image reference and record its image ID. Match the Mesa source and build environment to the runtime libraries. A different Mesa version is a separate experimental variable and must be identified explicitly if an exact match is unavailable.

Build the ANV target and required dependencies in a compatible container stage. Install under `/opt/mesa-anv-test` in the runtime image. Include `vulkaninfo`, verify the generated ICD manifest and its library path, and confirm the runner’s loaded library through runtime evidence. Merely setting `VK_DRIVER_FILES` is not proof of driver selection.

Reuse the existing model directory without pulling, modifying or deleting models during the comparison. Preserve the working device permissions and relevant launch settings, including SELinux handling. Do not widen device permissions as a default workaround. Keep the normal container available for rollback, but stopped during measurements.

Use one custom image for cases B and C; change only the experimental switch. Recreate or restart the test server as required to apply the environment, ensuring the old runner has exited.

## Test matrix

| Case | Driver and switch | Required initial state | Runs and purpose |
| --- | --- | --- | --- |
| A | Existing image | Populated reclaim pool, no model loaded | Three manual stop/reload cycles; record placement and reproduce the known partial-offload behavior. |
| B | Custom ANV, switch off | Comparable populated pool and host workload | The same three manual stop/reload cycles; compare with A to exclude a rebuild or dependency change as the explanation. |
| C | Same custom ANV, switch on | Comparable populated pool and host workload | The same three manual stop/reload cycles; require full offload and successful fixed inference requests. |
| D | Same as C | Defined memory-consuming background workload with low CPU activity | One additional manual stop/reload cycle after the core test passes; assess host behavior and budget headroom. |
| E | Existing image restored | Test runner stopped | Confirm the original API and model workflow operate again. |

Use the same sequence in A, B and C: establish an initial loaded model, then repeat three times: finish the fixed inference request, issue `ollama stop` against the server under test, confirm that the model is unloaded and its runner has exited, capture the memory counters, and send the next fixed request to trigger a fresh load. Record placement and request success after each reload. This means one initial load followed by three measured reloads per case. Do not restart the container between cycles. Keep the keep-alive configuration constant, but do not wait for it to expire. CLI exit alone does not establish unloading.

Keep the model blob, context, threads, batch settings, KV-cache type, flash attention, parallel requests, fit-target overrides, prompt and output limit identical across A–C. Record the effective values rather than relying only on intended configuration.

Prepare a populated pool through the normal load/unload sequence. If full loading is needed to seed it, the existing shrink script may be used before that seed load; record this preparation, then unload and confirm the pool is populated before measurement. Do not shrink between a measured unload and its reload. Avoid rebooting or dropping caches between comparison cases.

Record each case’s starting `MemAvailable`, `GPUReclaim`, `GPUActive` and swap state. Exact equality is not required, but the assistant must check that the conditions meaningfully exercise the problem. If A or B cannot reproduce it, classify the result as inconclusive rather than crediting C with a fix. An additional B run is warranted only if changed host conditions leave a concrete ambiguity.

For D, the assistant will provide a bounded host-side workload that allocates and touches a defined amount of anonymous memory, then holds it with low CPU activity while the model is stopped and reloaded. Aleš starts it before the measured cycle and stops it afterward. Select and record the allocation size after reviewing A–C headroom; do not use an unbounded allocator, lock the memory, or add a CPU stress loop. Verify its actual resident footprint and swap activity rather than relying only on the requested allocation size.

Allocating the background memory may itself reclaim part of the GPU pool. Record counters before and after starting it and keep it running throughout D. Case D tests behavior under reduced memory headroom; it does not replace A–C as evidence that the patch handles a populated reuse pool. CPU-only or combined CPU-and-memory stress is outside this first test matrix.

## Evidence to collect

The assistant will provide a collector that produces timestamped logs and a compact per-run summary. Aleš will run it on the host and return its output.

| Evidence | Reason |
| --- | --- |
| Kernel, source revision, package versions, image reference and patch checksum | Establish exactly what was tested. |
| Selected manifest, loaded ANV library and switch state | Prove the intended driver and calculation were active. |
| Model identity, request options and effective context | Keep the workload constant. |
| Host memory counters, swap usage and swap-in/out activity, sampled about once per second | Observe pool transitions and memory pressure; existing swap occupancy alone is not evidence of a regression. |
| Container memory limits and OOM counters, where available | Identify constraints hidden by host-wide counters. |
| Vulkan budget and runner fit/offload logs | Connect the changed estimate to placement. |
| `ollama ps` or API status after loading, plus layer counts from logs | Confirm full versus partial GPU placement. |
| Load duration, prompt/evaluation counts and durations, request success | Check usable inference and loading latency. |
| Kernel errors/device resets and operator responsiveness notes | Detect unacceptable host effects. |

Store both stdout and stderr from container logs. Keep initialization, explicit model-stop, confirmed unload and reload events in the same timeline. Driver-identification probes should run outside timed loads, since they can affect state or timing.

## Acceptance and stopping criteria

The core experiment passes when A and B demonstrate the problematic behavior under comparable conditions, and C completes all three reloads with the intended full offload, fixed context and successful inference, without manual reclaim between unload and reload. Diagnostics must connect the difference to the added pool allowance.

There must be no OOM kill, GPU reset, failed allocation or test-attributable sustained swap churn. Report load-time changes and any responsiveness degradation explicitly; a faster or slower load is an outcome to assess, not proof of correctness. D must remain responsive and complete its request, although full offload is conditional on sufficient capacity under that added workload. E must confirm rollback.

Aleš stops the current test if the desktop becomes persistently unresponsive, a GPU reset/OOM occurs, or sustained swapping makes the machine impractical to use. Capture available logs, stop the test runner, and send the evidence for analysis. Do not respond to a failed run by progressively removing reserves or forcing more layers.

## Rollback

Aleš stops the test container and confirms that its runner has exited, then starts the original `ollama` container and checks its usual API and model behavior. No host driver replacement is part of this plan.

The shared host TTM pool can remain populated after stopping the test. If the original image then reloads with partial offload, use the existing documented stop–shrink–reload workaround to restore its known operating state. Record that action separately from experimental results. Retain the test image and logs until analysis is complete; cleanup must not remove the model directory.

## Deliverables and next action

The assistant will deliver the version manifest, patch, Containerfile, build/run/rollback instructions, collection and test scripts, and final result report. Aleš will supply the environment inventory, local build output and hardware test evidence.

**Next action — Aleš:** run the inventory commands below and provide the output together with the current container launch command or configuration, omitting credentials. These commands collect information; they do not change the running service.

```bash
uname -r
readlink -f /sys/class/drm/renderD128/device/driver
podman inspect --format '{{.ImageName}} {{.Image}}' ollama

podman exec ollama sh -c '
cat /etc/os-release
if command -v dpkg-query >/dev/null; then
    dpkg-query -W "mesa*" "libvulkan*"
elif command -v rpm >/dev/null; then
    rpm -qa | sort | grep -E "mesa|vulkan"
fi
printenv VK_DRIVER_FILES VK_ICD_FILENAMES
'
```

Unset selection variables may produce no output and a nonzero final status; that is not an inventory failure. If the container is stopped, report that state rather than changing it solely to run this block. The assistant will then supply the remaining targeted checks for the loaded driver, memory limits and exact configuration.

## References

- Existing experimental report: `vulkan-igpu-memory-management-findings.md` in LLM lab.
- [Ollama 0.34.4 runner launch and automatic layer selection](https://github.com/ollama/ollama/blob/v0.34.4/llm/llama_server.go).
- [Mesa 25.2.0 ANV memory-budget calculation](https://gitlab.freedesktop.org/mesa/mesa/-/blob/mesa-25.2.0/src/intel/vulkan/anv_physical_device.c).
- [Mesa 25.2.0 Intel memory availability adjustment](https://gitlab.freedesktop.org/mesa/mesa/-/blob/mesa-25.2.0/src/intel/dev/intel_device_info.c).
- [Linux memory-counter documentation](https://docs.kernel.org/filesystems/proc.html).
- [Mesa build instructions](https://docs.mesa3d.org/meson.html).
- [Vulkan loader driver-selection documentation](https://vulkan.lunarg.com/doc/view/latest/linux/LoaderDriverInterface.html).

These references support the starting investigation. Step 2 will pin the implementation evidence to the versions actually installed on the notebook and in the container.
