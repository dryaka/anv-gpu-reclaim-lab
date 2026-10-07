# Build and later runtime handoff

## Build now — Aleš

Finish the loaded-baseline collection and stop its model manually before compiling. Keep the original container available. From the clean experiment branch:

```bash
git fetch origin
git switch experiment/anv-gpu-reclaim
git pull --ff-only
bash scripts/build-image.sh
```

The default build concurrency is four. The source is approximately 44 MB and compiler dependencies include LLVM 20; allow download time, disk space and time for compilation. `BUILD_JOBS=4` can be supplied explicitly. Do not collect comparison measurements while compiling; let the notebook settle after the build.

The script pins the verified amd64 Ollama image, verifies/extracts the Mesa source, runs production-parser tests, applies the patch and builds ANV. It retains the new driver under `/opt/mesa-anv-test`, leaving the packaged driver in place. The final stage verifies runtime dependency resolution without needing GPU access. It records the repository commit, image identity, source/patch hashes, build packages, Meson options, ICD manifest, driver hash and runtime dependencies.

Return the printed build `.tar.gz` bundle here. If building fails, return its `build.log` instead. The assistant has not compiled the complete driver locally: no container build engine is available in that execution environment. Do not start B/C until the returned build evidence has been checked.

## Runtime design — after build review

These are the intended commands for step 7, not part of the build. Use the exact image tag printed by the build script; B and C must use that same image. Retain the original model mount and its SELinux label instead of relabeling it with `:Z` or disabling label enforcement.

```bash
# Set these to the existing model directory and the exact built image tag.
MODEL_DIR="$HOME/.ollama/models"
TEST_IMAGE=localhost/ollama-anv-test:b14f909fe917
SELINUX_LEVEL="$(podman inspect --format '{{.ProcessLabel}}' ollama | cut -d: -f4-)"
test -d "$MODEL_DIR"
test -n "$SELINUX_LEVEL"

podman stop ollama
podman run -d --name ollama-anv-test \
  --device /dev/dri \
  --security-opt "label=level:$SELINUX_LEVEL" \
  -v "$MODEL_DIR:/root/.ollama/models" \
  -p 127.0.0.1:11435:11434 \
  -e OLLAMA_IGPU_ENABLE=1 -e ANV_SYS_MEM_LIMIT=90 \
  -e ANV_EXPERIMENTAL_GPU_RECLAIM=0 \
  -e ANV_EXPERIMENTAL_GPU_RECLAIM_DEBUG=1 \
  "$TEST_IMAGE"
podman exec ollama-anv-test vulkaninfo --summary
```

The current container already exposes card0/renderD128. The proposed device mapping must still be verified for the new container. Stop on a permission/label failure and return it; do not widen host permissions or use privileged mode. The new server is local-only at port 11435; the original container retains its configuration for rollback.

The custom image selects its absolute ICD manifest through `VK_DRIVER_FILES`. `vulkaninfo` and loaded runner maps together with logs will establish selection; setting the variable alone is insufficient. Probe outside timed loads. A small smoke request can use the already installed `lfm2.5-thinking:1.2b`, then collect the inventory while its runner is loaded and stop it manually. Run `python3 scripts/smoke-test.py` after starting the container above. The collector verifies the reviewed image ID and switch-off configuration, checks device access and Vulkan enumeration, makes a small request at context 4,096 and a 32-token output cap, captures loaded process maps and hashes, then manually stops the smoke model. It saves a private `.tar.gz` bundle beside the repository even on a test failure; return that bundle here. No model is downloaded. This smoke workload is separate from the 32,768-context comparison workload. Leave the test container running after collection for review. Comparison commands follow after smoke verification.

Case A uses the existing image. B/C use the custom image with switch 0/1 respectively. Recreating the test container to change the environment happens between cases, never between measured stop/reload cycles. No CPU-thread override is introduced. Context, prompt, output cap, keep-alive and other workload settings will be identical across A–C. Each case retains one initial load plus three measured manual stop/reload cycles; no manual reclaim between a measured stop and reload.

## Rollback

```bash
podman stop ollama-anv-test
podman top ollama-anv-test hpid pid comm
podman start ollama
OLLAMA_HOST=http://127.0.0.1:11434 ollama ps
```

Confirm no experimental runner remains before restoring the original server. A stopped-container `podman top` may report it is not running; that is expected. Retain the test image and evidence. The host pool may remain populated; restore the original known stop–shrink–reload workaround if necessary, separately from experiment results. No cleanup command removes models.
