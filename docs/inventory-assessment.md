# Inventory assessment

Date: 6 October 2026. Raw inventory remains private; this document contains selected experiment facts only.

## Confirmed

| Item | Observation |
| --- | --- |
| Host | Fedora 44 KDE; kernel `7.2.8-200.fc44.x86_64`; source RPM `kernel-7.2.8-200.fc44.src.rpm` |
| GPU kernel driver | Xe, PCI vendor/device `8086:b0a0` |
| Podman / Ollama | Podman 5.8.7; Ollama 0.34.4 |
| Runtime stack | Ubuntu 24.04.5; Mesa 25.2.8-0ubuntu0.24.04.2; libdrm 2.4.125-1ubuntu0.1~24.04.2 |
| Packaged ANV | `/usr/lib/x86_64-linux-gnu/libvulkan_intel.so`; SHA-256 recorded in the environment manifest; `dpkg -V` reported no differences |
| Relevant settings | `OLLAMA_IGPU_ENABLE=1`; `ANV_SYS_MEM_LIMIT=90`; no explicit ICD-selection variables |
| Memory ceilings | Container and readable cgroup ancestors report `memory.max=max` and `memory.high=max`; container swap ceiling is `max` |
| OOM evidence | No recorded `oom` or `oom_kill` events in the container cgroup at collection time |
| Model options | Operator used defaults for memory tests. The separate 12-thread CPU-test choice is not applied to this comparison. Saved model parameters remain to be inspected. |

Both reported repository digests are now resolved against Docker's registry. `sha256:8262851b2846b87c649eddf3e76beb270c52f4d1bc94559f47efde16b0841551` is an OCI image index. Its linux/amd64 manifest is `sha256:4be1eaabf0dd0152bfbb780347e2888b5fe86ec25d0faa3eb4b1a956173736fb`, whose configuration digest matches the uploaded local image ID `sha256:7fe01b0ef22e342fcbcb61e89d39de511609f078c30754a3a0bee7bb0f20a5c2`. The amd64 manifest is the selected immutable build base, recorded separately from the configuration ID.

The 13 GiB charged to the otherwise idle container is predominantly file cache (`memory.stat` reports about 13.7 billion bytes of file pages and only about 14 million bytes of anonymous pages). It should not be interpreted as a resident model or a memory limit.

## Snapshot, not a comparison run

Host counters show approximately 38.9 GiB `MemAvailable`, 1.21 GiB `GPUActive`, 0.84 GiB `GPUReclaim` and no used swap. Only the Ollama server process is present. This inventory does not establish the populated large reuse-pool condition needed for A–C. `GPUActive` can include desktop GPU use; it is not evidence that an Ollama model was loaded.

## Remaining runtime checks

No running process maps showed ANV, as expected with no model loaded. Packaged library identity is established; actual runner library identity is still unconfirmed.

The configuration collector reported `Devices=[]`, no device requests and only the model bind mount. This does not establish access to `/dev/dri` inside the container. Check the actual device nodes and process identity before reproducing device access in the test container. Do not widen permissions or disable SELinux merely to make the check pass.

Run these read-only commands in the current state and return their output:

```bash
podman exec ollama sh -c 'id; ls -ld /dev/dri; ls -l /dev/dri'
podman exec ollama ollama show hf.co/bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF:Q6_K --parameters
```

Neither command loads a model. If the device directory is absent, report the output; do not recreate the working container yet. Model parameters are needed because using request defaults does not tell us whether the saved model already specifies context, batch or other options. The agreed comparison context remains 32,768 and will be made explicit consistently for A–C.

Loaded-library maps will be collected during a suitable existing or small-model baseline run after device access is resolved. No large-model load is required solely to answer these two checks.
