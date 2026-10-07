#!/usr/bin/env python3
"""Fetch the pinned Ubuntu source, apply distribution patches and verify files."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, help="New source directory outside Git")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    lock = json.loads((root / "versions/mesa-source.json").read_text())
    if shutil.which("dpkg-source") is None:
        parser.error("dpkg-source is required; use an Ubuntu build environment (not a host package replacement)")
    destination = (args.destination or root.parent / "anv-mesa-source").resolve()
    destination.mkdir(parents=True, exist_ok=False)
    for entry in lock["files"]:
        path = destination / entry["name"]
        print("Fetching", entry["name"], flush=True)
        request = urllib.request.Request(lock["base_url"] + entry["name"], headers={"User-Agent": "anv-gpu-reclaim-lab/1"})
        with urllib.request.urlopen(request, timeout=60) as response, path.open("wb") as output:
            shutil.copyfileobj(response, output)
        if sha256(path) != entry["sha256"]:
            raise SystemExit("SHA-256 mismatch: " + entry["name"])
    dsc = next(entry["name"] for entry in lock["files"] if entry["name"].endswith(".dsc"))
    source = destination / ("mesa-" + lock["upstream_version"])
    # The descriptor and archives have been checked against the committed hashes.
    # This command does not imply GPG signature authentication.
    subprocess.run(["dpkg-source", "--no-check", "-x", dsc, str(source)], cwd=destination, check=True)
    for relative, expected in lock["inspected_patched_files_sha256"].items():
        if sha256(source / relative) != expected:
            raise SystemExit("Patched source mismatch: " + relative)
    series = [line.strip() for line in (source / "debian/patches/series").read_text().splitlines()
              if line.strip() and not line.lstrip().startswith("#")]
    if series != lock["applied_distribution_patches"]:
        raise SystemExit("Distribution patch series mismatch")
    print("Verified patched source:", source)
    print("No experimental patch has been applied. See docs/status.md for remaining prerequisites.")


if __name__ == "__main__":
    main()
