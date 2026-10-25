#!/usr/bin/env python3
"""Builds CATALOG.md and catalog.json from the entries in catalog/.

Each entry only names a GitHub repo. Everything shown (name, description,
author, version, permissions, download links) is read from that repo's
latest release, and from the adapter.toml or plugin.toml inside its zips,
so what the catalog says an add-on can do is what Folio will show before
installing it. Both adapters and WebAssembly plugins can be listed.

Usage:
    python3 scripts/catalog.py            # write CATALOG.md and catalog.json
    python3 scripts/catalog.py --check    # verify every entry's zips install, write nothing

Set GITHUB_TOKEN (or GH_TOKEN) to avoid GitHub's rate limit for anonymous use.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLATFORMS = {
    "macos-arm64": "macOS (Apple Silicon)",
    "windows-x64": "Windows",
    "linux-x64": "Linux",
}
PERMISSIONS = {
    "document.read": "read your document",
    "document.edit": "edit your document",
    "network": "go online",
}
ZIP = re.compile(r"^(?P<id>.+?)-(?P<version>\d[\w.]*?)(?:-(?P<platform>" + "|".join(PLATFORMS) + r"))?\.zip$")


class Problem(Exception):
    pass


def fetch(url: str, accept: str = "application/vnd.github+json") -> bytes:
    headers = {"Accept": accept, "User-Agent": "folio-adapters-catalog"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise Problem(f"{url}: HTTP {e.code}") from e


def read_manifest(data: bytes, zip_name: str, platform: str | None) -> dict:
    """The adapter.toml inside a release zip, checked the way Folio installs it."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise Problem(f"{zip_name} isn't a valid zip") from e
    names = [n for n in z.namelist() if not n.startswith("__MACOSX/")]
    manifests = [n for n in names if re.fullmatch(r"(?:[^/]+/)?(?:adapter|component|plugin)\.toml", n)]
    if len(manifests) != 1:
        raise Problem(f"{zip_name} should hold one adapter.toml or plugin.toml, at the top or one folder down")
    folder, _, file = manifests[0].rpartition("/")
    try:
        manifest = tomllib.loads(z.read(manifests[0]).decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        raise Problem(f"{zip_name}: {file} has a problem: {e}") from e
    if file == "plugin.toml":
        return read_plugin(manifest, zip_name, folder, names)
    manifest["kind"] = "adapter"
    for key in ["name", "run"]:
        if not manifest.get(key):
            raise Problem(f"{zip_name}: adapter.toml needs `{key}`")
    unknown = [p for p in manifest.get("permissions", []) if p not in PERMISSIONS]
    if unknown:
        raise Problem(f"{zip_name}: unknown permissions {unknown}")
    program = manifest["run"][0]
    if platform and "/" in program:
        path = f"{folder}/{program.removeprefix('./')}" if folder else program.removeprefix("./")
        if platform.startswith("windows") and not path.endswith(".exe"):
            path += ".exe"
        if path not in names:
            raise Problem(f"{zip_name} doesn't contain its program {path}")
    return manifest


def read_plugin(manifest: dict, zip_name: str, folder: str, names: list[str]) -> dict:
    """Checks a WebAssembly plugin's manifest and turns its capabilities
    into the same plain-words list adapters get."""
    if not manifest.get("name"):
        raise Problem(f"{zip_name}: plugin.toml needs `name`")
    wasm = manifest.get("wasm", "plugin.wasm")
    if (f"{folder}/{wasm}" if folder else wasm) not in names:
        raise Problem(f"{zip_name} doesn't contain its component {wasm}")
    caps = manifest.get("capabilities", {})
    can = []
    for access in caps.get("document", []):
        can.append({"read": "read your document", "edit": "edit your document"}.get(access, access))
    for grant in caps.get("filesystem", []):
        verb = "read and change" if grant.get("access") == "read-write" else "read"
        can.append(f"{verb} files in {grant.get('path')}")
    network = caps.get("network", "none")
    if network == "any":
        can.append("go online")
    elif isinstance(network, list) and network:
        can.append("connect to " + ", ".join(network))
    manifest["kind"] = "plugin"
    manifest["can"] = can
    return manifest


def load_entry(path: Path, check: bool) -> dict:
    entry = tomllib.loads(path.read_text())
    repo = entry.get("repo", "")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        raise Problem(f"{path.name}: `repo` should look like \"owner/name\"")
    info = json.loads(fetch(f"https://api.github.com/repos/{repo}"))
    release = json.loads(fetch(f"https://api.github.com/repos/{repo}/releases/latest"))

    zips = [(m, a) for a in release.get("assets", []) if (m := ZIP.match(a["name"]))]
    ids = {m["id"] for m, _ in zips}
    wanted = entry.get("adapter") or (ids.pop() if len(ids) == 1 else path.stem)
    zips = [(m, a) for m, a in zips if m["id"] == wanted]
    if not zips:
        raise Problem(
            f"{path.name}: the latest release of {repo} ({release.get('tag_name')}) has no "
            f"{wanted}-<version>[-<platform>].zip"
        )

    downloads = {}
    manifest = None
    # Checking reads every zip; listing only needs one.
    for m, asset in zips if check else zips[:1]:
        found = read_manifest(fetch(asset["browser_download_url"], "application/octet-stream"), asset["name"], m["platform"])
        if manifest and found["name"] != manifest["name"]:
            raise Problem(f"{asset['name']} names a different adapter ({found['name']})")
        manifest = found
    for m, asset in zips:
        downloads[m["platform"] or "all"] = asset["browser_download_url"]

    return {
        "id": wanted,
        "name": manifest["name"],
        "version": manifest.get("version", zips[0][0]["version"]),
        "author": manifest.get("author", ""),
        "license": manifest.get("license", ""),
        "description": manifest.get("description", "") or info.get("description") or "",
        "kind": manifest["kind"],
        "permissions": manifest.get("permissions", []),
        # Plain words for what it may do (plugins enforce this in a sandbox).
        "can": manifest.get("can") or [PERMISSIONS[p] for p in manifest.get("permissions", [])],
        "category": entry.get("category", "Other"),
        "tags": entry.get("tags", []),
        "repo": repo,
        "homepage": manifest.get("homepage") or info.get("homepage") or f"https://github.com/{repo}",
        "stars": info.get("stargazers_count", 0),
        "updated": release.get("published_at", "")[:10],
        "downloads": downloads,
    }


def render(adapters: list[dict]) -> str:
    categories = sorted({a["category"] for a in adapters}, key=lambda c: (c == "Other", c))
    out = [
        "# Folio adapter catalog",
        "",
        "Add-ons for [Folio](https://github.com/solacecasino/folio). Pick one, download the zip for your",
        "computer, then drop it on the Folio window, or choose **Folio → Adapters… → Add Adapter…**.",
        "Folio shows what an adapter can do and asks you before it first runs.",
        "",
        f"**{len(adapters)} adapters** · " + " · ".join(f"[{c}](#{c.lower().replace(' ', '-')})" for c in categories)
        + " · Search this page with Ctrl+F (Cmd+F on a Mac).",
        "",
        "**Made one?** [List it here](catalog/README.md): it's a two-line file. Start from the "
        "[template](https://github.com/solacecasino/folio-adapter-template) to get downloads for every platform.",
        "",
    ]
    for category in categories:
        out += [f"## {category}", ""]
        for a in sorted((a for a in adapters if a["category"] == category), key=lambda a: (-a["stars"], a["name"].lower())):
            if "all" in a["downloads"]:
                links = f"[**Download** (every platform)]({a['downloads']['all']})"
            else:
                links = "**Download:** " + " · ".join(
                    f"[{label}]({a['downloads'][p]})" for p, label in PLATFORMS.items() if p in a["downloads"]
                )
                missing = [label for p, label in PLATFORMS.items() if p not in a["downloads"]]
                if missing:
                    links += f" (not yet for {', '.join(missing)})"
            can = ", ".join(a["can"]) or "nothing beyond its own window and menus"
            if a["kind"] == "plugin":
                can += " (enforced: plugins run in a sandbox; not in Folio Lite)"
            meta = [f"v{a['version']}"]
            if a["author"]:
                meta.append(f"by {a['author']}")
            if a["license"]:
                meta.append(a["license"])
            meta.append(f"[source and help]({a['homepage']})")
            if a["stars"]:
                meta.append(f"★ {a['stars']}")
            if a["updated"]:
                meta.append(f"updated {a['updated']}")
            badge = " · *plugin*" if a["kind"] == "plugin" else ""
            out += [
                f"### {a['name']}{badge}",
                "",
                a["description"],
                "",
                links,
                "",
                f"Can {can}. " + " · ".join(meta),
                "",
            ]
    out += [
        "---",
        "",
        "Built from [catalog/](catalog) by `scripts/catalog.py` every day and whenever an entry changes,",
        "so it always shows each adapter's latest release. Don't edit this file by hand.",
        "",
    ]
    return "\n".join(out)


def main():
    check = "--check" in sys.argv
    adapters, problems = [], []
    for path in sorted((ROOT / "catalog").glob("*.toml")):
        try:
            adapters.append(load_entry(path, check))
            print(f"ok    {path.name}", flush=True)
        except Problem as e:
            problems.append(str(e))
            print(f"FAIL  {e}", flush=True)

    if check:
        sys.exit(1 if problems else 0)
    # A broken entry (say, a deleted release) drops out instead of breaking the page.
    (ROOT / "CATALOG.md").write_text(render(adapters))
    (ROOT / "catalog.json").write_text(json.dumps({"adapters": adapters}, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote CATALOG.md and catalog.json ({len(adapters)} adapters)")


if __name__ == "__main__":
    main()
