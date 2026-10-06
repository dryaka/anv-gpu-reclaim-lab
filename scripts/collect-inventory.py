#!/usr/bin/env python3
"""Read-only host/container inventory; no loads, stops, probes or sudo."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


ENV_KEYS = (
    "OLLAMA_IGPU_ENABLE", "ANV_SYS_MEM_LIMIT", "VK_DRIVER_FILES",
    "VK_ICD_FILENAMES", "GGML_VK_VISIBLE_DEVICES", "OLLAMA_VULKAN",
    "OLLAMA_LLM_LIBRARY", "OLLAMA_CONTEXT_LENGTH", "OLLAMA_KEEP_ALIVE",
    "OLLAMA_FLASH_ATTENTION", "OLLAMA_KV_CACHE_TYPE", "OLLAMA_NUM_PARALLEL",
    "OLLAMA_MAX_LOADED_MODELS", "OLLAMA_GPU_OVERHEAD", "OLLAMA_HOST",
    "OLLAMA_MODELS", "OLLAMA_LOAD_TIMEOUT", "LLAMA_ARG_FIT",
    "LLAMA_ARG_FIT_TARGET", "ANV_EXPERIMENTAL_GPU_RECLAIM",
)


def redact_url(value):
    """Do not expose credentials if a whitelisted URL contains userinfo."""
    try:
        parsed = urlsplit(value)
        if parsed.scheme and parsed.netloc and "@" in parsed.netloc:
            return urlunsplit(parsed._replace(netloc="<redacted>@" + parsed.netloc.rsplit("@", 1)[1]))
    except ValueError:
        return "<invalid URL>"
    return value


def selected_environment(entries):
    selected = {}
    for entry in entries or []:
        key, separator, value = entry.partition("=")
        if separator and key in ENV_KEYS:
            selected[key] = redact_url(value)
    return {key: selected.get(key) for key in ENV_KEYS}


def summarize_inspect(data):
    """Never serialize the original inspect object or arbitrary env/labels."""
    config = data.get("Config") or {}
    host = data.get("HostConfig") or {}
    state = data.get("State") or {}
    host_keys = (
        "Memory", "MemorySwap", "MemoryReservation", "NanoCpus", "CpuQuota",
        "CpuPeriod", "CpusetCpus", "CpusetMems", "Devices", "DeviceRequests",
        "GroupAdd", "SecurityOpt", "UsernsMode", "CgroupnsMode", "Privileged",
        "ReadonlyRootfs", "NetworkMode", "PortBindings",
    )
    return {
        "image_name": data.get("ImageName"), "image_id": data.get("Image"),
        "state": {key: state.get(key) for key in ("Status", "Running", "Pid", "OOMKilled")},
        "user": config.get("User"), "environment": selected_environment(config.get("Env")),
        "host_config": {key: host.get(key) for key in host_keys},
        "mounts": [{key: mount.get(key) for key in
                    ("Type", "Source", "Destination", "Options", "RW", "Propagation")}
                   for mount in data.get("Mounts", [])],
        "process_label": data.get("ProcessLabel"), "mount_label": data.get("MountLabel"),
    }


def run(argv, timeout=30):
    started = datetime.now(timezone.utc).isoformat()
    try:
        result = subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)
        return {"started_utc": started, "returncode": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        # Do not serialize a TimeoutExpired object with arbitrary command output.
        return {"started_utc": started, "returncode": None, "error": type(exc).__name__}


def read_text(path):
    try:
        return Path(path).read_text()
    except OSError as exc:
        return {"error": type(exc).__name__}


CONTAINER_PROBE = r'''
printf '\n== OS ==\n'
cat /etc/os-release
printf '\n== Ollama version ==\n'
ollama --version 2>&1
printf '\n== Source packages and versions ==\n'
if command -v dpkg-query >/dev/null 2>&1; then
    dpkg-query -W -f='${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\n' 'mesa*' 'libvulkan*' 'libdrm*' 2>&1
    printf '\n== Mesa package file verification (empty output means no reported differences) ==\n'
    dpkg -V mesa-vulkan-drivers 2>&1
fi
printf '\n== ICD manifests ==\n'
for f in /usr/share/vulkan/icd.d/*intel*.json /etc/vulkan/icd.d/*intel*.json; do
    [ -f "$f" ] || continue
    printf '\n%s\n' "$f"
    cat "$f"
done
printf '\n== Packaged Intel libraries ==\n'
for f in /usr/lib/x86_64-linux-gnu/libvulkan_intel.so /usr/lib/x86_64-linux-gnu/libvulkan_intel_hasvk.so; do
    [ -f "$f" ] || continue
    sha256sum "$f"
    if command -v readelf >/dev/null 2>&1; then readelf -n "$f" | sed -n '/Build ID/p'; fi
    ldd "$f" 2>&1
done
printf '\n== Existing processes with loaded Intel Vulkan libraries ==\n'
found=0
for maps in /proc/[0-9]*/maps; do
    [ -r "$maps" ] || continue
    if grep -qE 'libvulkan_intel[^ /]*\.so' "$maps"; then
        found=1
        pid=${maps#/proc/}; pid=${pid%/maps}
        printf '\nPID=%s comm=' "$pid"
        cat "/proc/$pid/comm"
        grep -E 'libvulkan[^ /]*\.so|libggml-vulkan[^ /]*\.so' "$maps"
        awk '/libvulkan_intel[^ /]*\.so/ {print $NF}' "$maps" | sort -u |
        while IFS= read -r library; do
            [ -f "$library" ] && sha256sum "$library"
        done
    fi
done
[ "$found" = 1 ] || printf 'No readable process maps showed ANV; driver selection is UNCONFIRMED. Do not load a model solely for this inventory.\n'
printf '\n== Cgroup membership and namespace ==\n'
cat /proc/1/cgroup /proc/self/cgroup
readlink /proc/1/ns/cgroup /proc/self/ns/cgroup
printf '\n== Visible cgroup v2 counters (may need host path follow-up) ==\n'
for key in memory.max memory.high memory.current memory.swap.max memory.swap.current memory.events memory.events.local memory.stat cpu.max cpuset.cpus.effective; do
    f=/sys/fs/cgroup/$key
    if [ -r "$f" ]; then printf '\n%s\n' "$f"; cat "$f"; fi
done
printf '\n== Container memory counters ==\n'
sed -n -E '/^(MemTotal|MemAvailable|MemFree|GPUActive|GPUReclaim|SwapTotal|SwapFree|KReclaimable|SReclaimable):/p' /proc/meminfo
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", default="ollama")
    parser.add_argument("--output", type=Path, help="New output directory; default is outside the repository")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", args.container):
        parser.error("container must be a simple name or ID")
    repository = Path(__file__).resolve().parent.parent
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or repository.parent / "anv-gpu-reclaim-evidence" / stamp
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {
        "schema_version": 1, "started_utc": datetime.now(timezone.utc).isoformat(),
        "container": args.container, "collector_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "repository_commit": run(["git", "-C", str(repository), "rev-parse", "HEAD"]),
        "repository_status": run(["git", "-C", str(repository), "status", "--porcelain"]),
        "kernel": run(["uname", "-r"]), "host_os": read_text("/etc/os-release"),
        "gpu_driver": run(["readlink", "-f", "/sys/class/drm/renderD128/device/driver"]),
        "gpu_device": {key: read_text("/sys/class/drm/renderD128/device/" + key)
                       for key in ("vendor", "device", "revision")},
        "host_meminfo": read_text("/proc/meminfo"),
        "host_vmstat": read_text("/proc/vmstat"),
        "podman_version": run(["podman", "version", "--format", "json"]),
    }
    kernel = report["kernel"].get("stdout", "").strip()
    if kernel:
        report["kernel_package"] = run(["rpm", "-q", "--qf",
            "%{NAME}\t%{VERSION}-%{RELEASE}.%{ARCH}\t%{SOURCERPM}\n", "kernel-core-" + kernel])
        report["kernel_config_gpu"] = run(["sh", "-c",
            'for f in /boot/config-"$(uname -r)"; do [ -r "$f" ] && sed -n -E "/^CONFIG_(DRM_XE|DRM_TTM|CGROUPS|MEMCG|NUMA)=/p" "$f"; done'])
        report["xe_module"] = run(["modinfo", "-F", "filename", "xe"])
        report["ttm_pool_limit"] = read_text("/sys/module/ttm/parameters/page_pool_size")
    inspected = run(["podman", "inspect", "--type", "container", args.container])
    if inspected.get("returncode") == 0:
        try:
            original = json.loads(inspected["stdout"])[0]
            report["container_inspect"] = summarize_inspect(original)
            image = original.get("Image")
            if image:
                image_result = run(["podman", "image", "inspect", image])
                if image_result.get("returncode") == 0:
                    image_original = json.loads(image_result["stdout"])[0]
                    report["image"] = {key: image_original.get(key) for key in
                                       ("Id", "Digest", "RepoDigests", "RepoTags", "Architecture", "Os", "Created")}
                else:
                    report["image"] = {"returncode": image_result.get("returncode"), "error": "image inspection failed"}
            if (original.get("State") or {}).get("Running"):
                report["container_probe"] = run(["podman", "exec", args.container, "sh", "-c", CONTAINER_PROBE], timeout=60)
                report["container_top"] = run(["podman", "top", args.container, "hpid", "pid", "comm"])
                pid = (original.get("State") or {}).get("Pid")
                if isinstance(pid, int) and pid > 0:
                    membership = read_text(f"/proc/{pid}/cgroup")
                    report["container_host_cgroup_membership"] = membership
                    if isinstance(membership, str):
                        for line in membership.splitlines():
                            if line.startswith("0::"):
                                relative = Path(line[3:].lstrip("/"))
                                if ".." not in relative.parts:
                                    base = Path("/sys/fs/cgroup") / relative
                                    report["container_host_cgroup"] = {key: read_text(base / key) for key in
                                        ("memory.max", "memory.high", "memory.current", "memory.swap.max", "memory.events", "cpu.max", "cpuset.cpus.effective")}
                                    # An ancestor may impose a lower limit even when the leaf says max.
                                    root = Path("/sys/fs/cgroup")
                                    report["ancestor_memory_limits"] = []
                                    for ancestor in base.parents:
                                        if ancestor == root or root in ancestor.parents:
                                            report["ancestor_memory_limits"].append({"path": str(ancestor),
                                                "memory.max": read_text(ancestor / "memory.max"),
                                                "memory.high": read_text(ancestor / "memory.high"),
                                                "memory.swap.max": read_text(ancestor / "memory.swap.max")})
            else:
                report["container_probe"] = {"skipped": "container is stopped; it was not started"}
        except (ValueError, IndexError, TypeError) as exc:
            report["inspect_error"] = type(exc).__name__
    else:
        # Avoid dumping unfiltered inspect stdout or stderr in any failure path.
        report["inspect_error"] = {"returncode": inspected.get("returncode"), "error": inspected.get("error", "container inspection failed")}
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report_file = output / "inventory.json"
    report_file.write_text(json.dumps(report, indent=2) + "\n")
    os.chmod(report_file, 0o600)
    print(f"Saved {report_file.resolve()}")
    print("Review before sharing: host paths, mount paths and device/process details are included.")
    print("No model was loaded/stopped; no container or memory settings were changed.")


if __name__ == "__main__":
    main()
