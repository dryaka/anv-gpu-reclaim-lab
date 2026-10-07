# ANV GPU reclaim lab

Test whether an opt-in Intel ANV availability estimate using `MemAvailable + GPUReclaim` prevents Ollama from choosing partial GPU offload when a model reloads with a populated TTM reuse pool.

**Status:** hardware experiments and rollback are complete. The accounting change restored full placement on this tested stack; swap behavior qualifies host acceptance. See the [final result](docs/experiment-results.md) and [current status](docs/status.md).

## Start here

Read the final result and limitations before rerunning or enabling the patch. The experimental driver remains opt-in; repository merge does not deploy it. The original server was restored after rollback verification.

## Contents

- [Agreed project plan](docs/anv-gpu-reclaim-test-project-plan.md): responsibilities, manual reload matrix, acceptance and rollback.
- [Environment manifest](versions/environment.json): supplied observations separated from unknown and intended values.
- [Inventory assessment](docs/inventory-assessment.md) and [Fedora source evidence](versions/fedora-kernel-source.json): assessed runtime limits and exact kernel accounting check.
- [Loaded baseline](docs/loaded-baseline-assessment.md), [implementation](docs/implementation.md) and [build/runtime handoff](docs/build-and-runtime.md): source binding, switch semantics and reproducible build instructions.
- [Pinned Mesa source](versions/mesa-source.json) and [source assessment](docs/source-assessment.md): Ubuntu distribution patches, checked hashes and identified accounting path.
- `scripts/fetch-mesa-source.py`: reproduce source extraction in an environment containing `dpkg-source`, into a new directory outside Git. Retains Ubuntu patches; applies no experimental change.
- `scripts/check-loaded-baseline.py`: intentionally load the existing test model once with context 32,768, capture loaded-driver evidence and leave manual stop to the operator. See the status document before running.
- `scripts/build-image.sh` and `Containerfile`: build the experimental ANV image from the clean commit and collect build evidence without starting it.
- `tests/`: 23 checks for production helpers, collection, reload sequencing, holder lifecycle and rollback. Run `python3 -m unittest discover -s tests -v`.

- [Case assessments A–E and final result](docs/experiment-results.md#supporting-records) retain measured outcomes and limitations.
- [Comparison runs](docs/comparison-runs.md), [bounded workload D](docs/memory-case-D.md) and [rollback E](docs/rollback-case-E.md) describe reproducing the hardware sequence.

The source/build/image/model trees and raw evidence are excluded from this public repository. Only reviewed summaries should be added. B and C used the same custom image with the switch off/on; the normal container remains available for rollback. Host driver replacement and upstream submission are outside this initial experiment.
