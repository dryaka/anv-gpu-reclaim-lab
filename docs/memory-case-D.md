# Case D — bounded background-memory workload

Use the existing enabled test container and the same reviewed custom image. Keep the original `ollama` container stopped and all other model clients idle. No container recreation or image rebuild is needed.

```bash
git pull --ff-only
python3 scripts/run-memory-case.py
```

The collector verifies the enabled switch, image/model identity and unloaded starting state. It requires at least 12 GiB of current MemAvailable before allocating a fixed 4 GiB private anonymous mapping. It touches every page once and then holds the mapping without a CPU stress loop or locked memory. A separate process holds it so its resident footprint, swap usage and CPU-time counters can be recorded independently of the model. Its size cannot grow during the test.

D establishes an initial loaded model with the holder running, explicitly stops it, confirms the runner exited, and sends the same fixed request for one measured reload. The holder remains present throughout both requests and the intervening stop/reload. The workload matches A–C: ThinkingCap Q6_K, context 32,768, output cap 128, keep-alive 30 minutes, and default CPU thread selection. No manual reclaim occurs inside the sequence.

The collector records memory counters before allocation, after holder readiness, during the model sequence and after holder release. Allocation can itself reclaim pool pages; that is part of the measured reduced-headroom state. Holder readiness requires at least 95% of the requested resident footprint. Per-second samples retain its VmRSS/VmSwap and process stat counters so analysis can check actual residency and low CPU activity during the holding phase.

Observe the desktop. Ctrl+C stops the attempted model and releases the holder while retaining evidence. Normal completion also stops the model and frees the holder. If the parent exits unexpectedly, the holder checks parent identity and exits; no unbounded or persistent stress job is installed. If cleanup reports a runner still present, stop the experimental container manually and report it.

Attach the printed `*-case-D.tar.gz` bundle and desktop responsiveness note. A completed collector means the fixed sequence finished; full offload and host acceptance are assessed from the returned evidence. Keep existing swap state, caches and pool conditions rather than resetting them. Do not merge the experiment yet; rollback verification and the final outcome review follow D.
