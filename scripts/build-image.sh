#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
if [[ -n "$(git status --porcelain)" ]]; then
    echo 'Worktree must be clean so the image corresponds to an exact reviewed commit.' >&2
    exit 1
fi
lab_commit="$(git rev-parse HEAD)"
image_tag="localhost/ollama-anv-test:${lab_commit:0:12}"
evidence_dir="$(pwd)/../anv-gpu-reclaim-evidence/$(date -u +%Y%m%dT%H%M%SZ)-build"
mkdir -m 700 -p "$evidence_dir"
printf '%s\n' "$lab_commit" > "$evidence_dir/lab-commit.txt"
printf '%s\n' "$image_tag" > "$evidence_dir/image-tag.txt"
echo "Build log: $evidence_dir/build.log"
podman build --arch amd64 --build-arg "LAB_COMMIT=$lab_commit" \
    --build-arg "BUILD_JOBS=${BUILD_JOBS:-4}" -f Containerfile -t "$image_tag" . \
    2>&1 | tee "$evidence_dir/build.log"
podman image inspect "$image_tag" > "$evidence_dir/image-inspect.json"
probe_id="$(podman create "$image_tag")"
trap 'podman rm "$probe_id" >/dev/null 2>&1 || true' EXIT
podman cp "$probe_id:/opt/mesa-anv-test/build-evidence" "$evidence_dir/"
podman cp "$probe_id:/opt/mesa-anv-test/share/vulkan/icd.d/intel_icd.json" "$evidence_dir/intel_icd.json"
podman rm "$probe_id" >/dev/null
trap - EXIT
tar -czf "$evidence_dir.tar.gz" -C "$(dirname "$evidence_dir")" "$(basename "$evidence_dir")"
echo "Image: $image_tag"
echo "Build evidence: $evidence_dir.tar.gz"
echo 'Return the build evidence before starting the experimental container.'
