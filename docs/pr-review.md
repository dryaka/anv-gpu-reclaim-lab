# Final PR summary

Title: Add and validate opt-in ANV reclaim-pool accounting

## Description

Ollama's automatic fitting can choose partial GPU placement when unused TTM pool pages are excluded from ANV's MemAvailable estimate. This adds a default-off ANV experiment that includes GPUReclaim within the separately queried raw Xe region bound while retaining heap limits, reserve and rounding. It is restricted to Linux Xe integrated GPUs and falls back conservatively on invalid input; shared Mesa memory helpers are unchanged.

Hardware validation on Intel PTL reproduces partial placement in the original and disabled-rebuild controls. The identical custom image with accounting enabled retains 66/66 layers through all three reloads. A verified 4 GiB low-CPU resident holder also completes full-offload inference/reload, and the original image/driver workflow is restored afterward. Context, model manifest and request settings remain fixed. The result supports the accounting hypothesis on this stack, with qualified host acceptance: global swap activity remains present and is higher in the enabled main case. Full offload is not shown to improve throughput or establish production suitability.

Includes pinned source/base-image inputs, the switchable patch, build recipe, evidence collectors, focused helper/lifecycle tests, case assessments, reproduction/rollback instructions and final report. Raw evidence stays outside Git. The experimental switch remains off by default; merging preserves the experiment and does not deploy it.

Validation: complete ANV build succeeded on the operator's host; runtime library hashes/process maps and all measured requests/unloads were verified. Twenty-three local tests plus Python/shell/JSON/whitespace checks pass. CI passed on the collector head; the exact final-head result is recorded in PR checks. No recorded cgroup OOM/GPU reset; operator reported normal desktop responsiveness throughout. See `docs/experiment-results.md` for measurements and limits.

## Review state

Publication of the assessments, final report and consolidated documentation is approved. The PR title/description use the final scope above. Verify exact-head CI before the ready-for-review transition and leave merge to the owner. The experimental switch remains default off; retaining, extending or pursuing upstream work is a separate owner decision.
