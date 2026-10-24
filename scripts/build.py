#!/usr/bin/env python3
"""Builds the adapters and packs one zip per adapter into dist/.

Each zip holds a single folder with adapter.toml, ready for
Folio → Adapters… → Add Adapter…. Compiled (Rust) adapters are built for
this computer and named for it, e.g. pdf-export-0.2.0-windows-x64.zip;
script adapters work everywhere and have no platform in the name.

Usage: python3 scripts/build.py [--compiled-only]
"""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
# Only what Folio needs to run an adapter: no sources or build output.
SKIP = {"target", "src", "tests", "Cargo.toml", "Cargo.lock", ".gitignore", "__pycache__", ".DS_Store"}


def platform_name():
    system = {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}[platform.system()]
    machine = platform.machine().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(machine, machine)
    return f"{system}-{arch}"


def zip_adapter(folder: Path, out: Path, binary: Path | None):
    """Zips the adapter folder. The compiled program, if any, is marked
    executable for macOS and Linux."""
    programs = {folder / folder.name, folder / f"{folder.name}.exe"}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(folder.rglob("*")):
            rel = path.relative_to(folder)
            if path.is_dir() or rel.parts[0] in SKIP or path.name in SKIP:
                continue
            if path in programs and path != binary:
                continue  # a leftover build for another platform
            info = zipfile.ZipInfo.from_file(path, f"{folder.name}/{rel.as_posix()}")
            info.compress_type = zipfile.ZIP_DEFLATED
            if path == binary:
                info.external_attr = 0o100755 << 16
            z.writestr(info, path.read_bytes())


def main():
    compiled_only = "--compiled-only" in sys.argv
    shutil.rmtree(DIST, ignore_errors=True)
    DIST.mkdir()
    for folder in sorted(p for p in ROOT.iterdir() if (p / "adapter.toml").is_file()):
        version = re.search(r'^version = "(.+)"', (folder / "adapter.toml").read_text(), re.M).group(1)
        binary = None
        if (folder / "Cargo.toml").is_file():
            subprocess.run(["cargo", "build", "--release"], cwd=folder, check=True)
            exe = ".exe" if platform.system() == "Windows" else ""
            binary = folder / f"{folder.name}{exe}"
            shutil.copy2(folder / "target/release" / binary.name, binary)
            name = f"{folder.name}-{version}-{platform_name()}.zip"
        elif compiled_only:
            continue
        else:
            name = f"{folder.name}-{version}.zip"
        zip_adapter(folder, DIST / name, binary)
        print(f"Built dist/{name}", flush=True)


if __name__ == "__main__":
    main()
