# ANV GPU reclaim lab

Test whether an opt-in Intel ANV availability estimate using `MemAvailable + GPUReclaim` prevents Ollama from choosing partial GPU offload when a model reloads with a populated TTM reuse pool.

**Status:** repository initialized; matching Ubuntu source inspected; remaining runtime inventory needed. No experimental driver has been built or hardware-tested. See [current status and next handoff](docs/status.md).

## Start here

```bash
git switch experiment/anv-gpu-reclaim
python3 scripts/collect-inventory.py --container ollama
```

The collector is read-only and writes evidence outside Git. Return its output privately after reviewing local paths. It does not load/stop models, restart containers, reclaim memory or install packages.

## Contents

- [Agreed project plan](docs/anv-gpu-reclaim-test-project-plan.md): responsibilities, manual reload matrix, acceptance and rollback.
- [Environment manifest](versions/environment.json): supplied observations separated from unknown and intended values.
- [Pinned Mesa source](versions/mesa-source.json) and [source assessment](docs/source-assessment.md): Ubuntu distribution patches, checked hashes and identified accounting path.
- `scripts/fetch-mesa-source.py`: reproduce source extraction in an environment containing `dpkg-source`, into a new directory outside Git. Retains Ubuntu patches; applies no experimental change.
- `tests/`: inventory privacy/behavior and manifest checks. Run `python3 -m unittest discover -s tests -v`.

The source/build/image/model trees and raw evidence are excluded from this public repository. Only reviewed summaries should be added. B and C will use the same custom image with the new switch off/on; the normal container remains available for rollback. Host driver replacement and upstream submission are outside this initial experiment.
