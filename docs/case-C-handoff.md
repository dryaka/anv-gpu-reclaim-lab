# Case C — enable reclaim accounting


Retain the stopped B container for reference. Fetch its existing SELinux level before stopping/renaming it. These commands keep the reviewed image, model mount, local port, device mapping and runtime settings; only the accounting switch changes from 0 to 1.

```bash
git pull --ff-only
MODEL_DIR="$HOME/.ollama/models"
TEST_IMAGE=localhost/ollama-anv-test:b14f909fe917
SELINUX_LEVEL="$(podman inspect --format '{{.ProcessLabel}}' ollama-anv-test | cut -d: -f4-)"

test -d "$MODEL_DIR" && test -n "$SELINUX_LEVEL" &&
podman stop ollama-anv-test &&
podman rename ollama-anv-test ollama-anv-test-off &&
podman run -d --name ollama-anv-test \
  --device /dev/dri \
  --security-opt "label=level:$SELINUX_LEVEL" \
  -v "$MODEL_DIR:/root/.ollama/models" \
  -p 127.0.0.1:11435:11434 \
  -e OLLAMA_IGPU_ENABLE=1 -e ANV_SYS_MEM_LIMIT=90 \
  -e ANV_EXPERIMENTAL_GPU_RECLAIM=1 \
  -e ANV_EXPERIMENTAL_GPU_RECLAIM_DEBUG=1 \
  "$TEST_IMAGE" &&
python3 scripts/run-reload-case.py --case C
```

Keep `ollama` stopped. The collector checks both the image ID and switch state before generating. It waits for the new API to start, then makes the same initial request and three explicit stop/reloads. No small-model smoke or extra Vulkan probe is needed inside the measurement. Return the printed C bundle and responsiveness note. If creation fails, return the error; do not start the preserved B server alongside C. Rollback to the original server remains `podman stop ollama-anv-test` followed by `podman start ollama` after confirming the test runner exited.
