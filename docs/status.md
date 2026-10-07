# Experiment status

Updated: 7 October 2026, after final publication approval.

The hardware sequence is complete. [Final result and limitations](experiment-results.md): placement succeeded with enabled accounting on this stack; host acceptance is qualified by observed global swap activity. All operator notes report normal desktop responsiveness. Rollback to the original image/driver and successful inference is verified; the original server is running with the model unloaded.

| Plan steps | State |
| --- | --- |
| 1–2 — inventory/source binding | Complete |
| 3–6 — patch, build and review | Complete; full ANV build and driver hashes verified |
| 7–8 — switch-off smoke/review | Complete |
| 9–10 — A/B/C comparison and analysis | Complete; controls remain partial, enabled image fully offloads |
| 11 — bounded memory workload and rollback | Complete; D/E evidence reviewed |
| 12 — report and repository consolidation | Complete; reports and consolidated documentation approved for publication |
| 13 — owner decision | Pending review: retain lab result, extend testing or pursue upstream work |

The patch remains default off. No permanent deployment, host driver replacement, upstream submission or PR merge has been performed. All assessment summaries, consolidated outcome and documentation updates have publication approval. PR #1 is the review vehicle. Raw evidence remains outside Git.

There are 23 passing local tests and successful CI on the collector commit. Final-head CI and review status are recorded on PR #1. Merge remains the owner's decision.
