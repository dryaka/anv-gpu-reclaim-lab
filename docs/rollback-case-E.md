# Case E — original server rollback verification

Restore the original container without changing its image, environment, model mount or device configuration. Keep both experimental containers stopped. The bounded memory holder must have been released by the D collector before proceeding.

```bash
git pull --ff-only
podman stop ollama-anv-test
podman start ollama
python3 scripts/run-reload-case.py --case E
```

E verifies the original image identity, model manifest, IGPU configuration and unloaded starting state. It makes one fixed ThinkingCap request at context 32,768 with default thread selection, collects loaded-driver evidence and original-server logs, then explicitly stops the model and confirms the runner exited. It retains sampled host/cgroup memory data and kernel logs. The original server remains running afterward for normal use; the model is unloaded.

Attach the printed `*-case-E.tar.gz` bundle and responsiveness note. No full A/B/C sequence is repeated. The original driver can again choose partial offload if the shared TTM pool is populated. That is the known baseline behavior and does not by itself mean rollback failed; successful inference and the original image/driver establish restoration of the original workflow. Do not silently reclaim between stopping the experimental container and the E request.

If the request fails, return the available evidence. Any later use of the known stop–shrink–reload workaround to regain original full offload is a separate recovery action; record it separately from E. No command removes models, host drivers or experimental evidence. Retain the enabled and disabled experimental containers/images until the final review. Do not merge the PR before the result and limitations are consolidated.
