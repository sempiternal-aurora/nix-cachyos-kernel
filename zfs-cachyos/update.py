import json
import re
import requests
import subprocess
import tempfile
from pathlib import Path


def get_zfs_commit(variant: str = "latest") -> str:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as dir:
        subprocess.run(
            ["nix", "build", ".#cachyos-kernel-input-path", "-o", f"{dir}/result"],
            check=True,
        )

        pkgbuild_path = f"linux-cachyos-{variant}" if variant != "latest" else "linux-cachyos"

        with open(f"{dir}/result/{pkgbuild_path}/PKGBUILD") as f:
            pkgbuild = f.read()

        commit = re.search(r"zfs.git#commit=([0-9a-f]{40})", pkgbuild)
        if not commit:
            raise ValueError(f"Cannot find ZFS commit ID for {variant=}")
        return commit[1]


def get_zfs_version(commit: str) -> str:
    url = f"https://raw.githubusercontent.com/CachyOS/zfs/{commit}/META"
    print(f"{url=}")
    metadata = requests.get(url).text
    version = re.search(r"^Version:\s+([0-9\.]+)$", metadata, re.MULTILINE)
    return version[1]


def nix_sha256_to_sri(hash: str) -> str:
    cmd = ["nix", "hash", "to-sri", "--type", "sha256", hash]

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise RuntimeError(f"nix hash command failed with return code: {result.returncode}")

    output = result.stdout.strip()
    if not output:
        raise RuntimeError("nix hash output is empty")

    return output


def run_nix_prefetch_url(url: str) -> str:
    cmd = ["nix-prefetch-url", url]

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise RuntimeError(f"nix-prefetch-url command failed with return code: {result.returncode}")

    output = result.stdout.strip()
    if not output:
        raise RuntimeError("nix-prefetch-url output is empty")

    return output


if __name__ == "__main__":
    versions = {}
    for variant in ["latest", "lts", "rc", "hardened"]:
        print(f"{variant=}")
        commit = get_zfs_commit(variant)
        print(f"{commit=}")
        version = get_zfs_version(commit)
        print(f"{version=}")

        url = f"https://github.com/CachyOS/zfs/archive/{commit}.tar.gz"
        print(f"{url=}")
        hash = run_nix_prefetch_url(url)
        hash = nix_sha256_to_sri(hash)
        print(f"{hash=}")
        versions[variant] = {
            "commit": commit,
            "version": version,
            "url": url,
            "hash": hash,
        }

    current = Path.cwd()
    while not (current / "flake.lock").exists():
        if current == current.parent:
            raise RuntimeError("Could not find flake.lock in any parent directory, exiting")
        current = current.parent

    output_file = current / "zfs-cachyos" / "version.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(versions, f, indent=2)
