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

## Device and parameter checks completed

No running process maps showed ANV, as expected with no model loaded. Packaged library identity is established; actual runner library identity is still unconfirmed.

The configuration collector reported `Devices=[]`, no device requests and only the model bind mount. The subsequent check confirms `/dev/dri/card0` and `/dev/dri/renderD128` are present inside the running container. Its process identity is root with groups 0 and 65534. `card0` is mode 0660 with an ACL; `renderD128` is mode 0666. These are observations of the existing state, not instructions to change host permissions. The exact device mapping/creation command is still not recovered from the inspect summary.

The completed read-only checks were:

```bash
podman exec ollama sh -c 'id; ls -ld /dev/dri; ls -l /dev/dri'
podman exec ollama ollama show hf.co/bottlecapai/ThinkingCap-Qwen3.8-27B-GGUF:Q6_K --parameters
```

Both container and host CLI parameter queries returned no output, so no saved parameter overrides are shown. The model reports qwen35, 27.3B parameters, Q6_K quantization and a 262,144 maximum context, plus a CLIP projector with 460.73M parameters. The maximum context is not proof of active runtime context. The agreed comparison context remains 32,768 and will be made explicit consistently for A–C.

Device presence and saved-parameter checks are now complete. The next intentional baseline request will collect actual loaded-library maps and effective context; see `docs/status.md`. No permissions or container settings were changed by these checks.
