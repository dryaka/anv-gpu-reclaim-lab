# Experiment status

Updated: 7 October 2026, after the owner's wrap-up decision.

The hardware sequence is complete. [Final result and limitations](experiment-results.md): placement succeeded with enabled accounting on this stack; host acceptance is qualified by observed global swap activity. All operator notes report normal desktop responsiveness. Rollback to the original image/driver and successful inference is verified; the original server is running with the model unloaded.

| Plan steps | State |
| --- | --- |
| 1–2 — inventory/source binding | Complete |
| 3–6 — patch, build and review | Complete; full ANV build and driver hashes verified |
| 7–8 — switch-off smoke/review | Complete |
| 9–10 — A/B/C comparison and analysis | Complete; controls remain partial, enabled image fully offloads |
| 11 — bounded memory workload and rollback | Complete; D/E evidence reviewed |
| 12 — report and repository consolidation | Complete; reports and consolidated documentation approved for publication |
| 13 — owner decision | Recorded: clean upstream preparation, approximately one month of local use, then submission decision |

## Wrap-up and follow-up

The controlled experiment is closed. Aleš decided against further swap-out investigation. Allocation pressure causing both GPU-pool reclaim and anonymous-page swap-out is a working hypothesis, not an established cause. The measurements and swap qualification remain in the [final report](experiment-results.md#owner-decision--7-october-2026).

The follow-up is to prepare a clean upstream change on a separate branch, use a specific identifiable Ollama container build on this system for approximately one month, then decide whether to submit the patch upstream. Count the period from the start of regular use. Keep the running image fixed; validate any accounting changes before replacing it. These are follow-up activities, not outstanding acceptance steps for the completed experiment.

The patch remains default off. PR #1 is merged; the original-driver rollback was verified during E. No host driver replacement or upstream submission has been performed. Raw evidence remains outside Git. The experiment's 23 local tests and exact final-head CI passed; PR #1 records that validation. This wrap-up changes documentation only.
