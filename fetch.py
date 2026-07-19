#!/usr/bin/env python3
"""Fetch Infineon (incl. former Cypress) CMSIS SVD files from five public
GitHub repos and organize them into <Family>/<Device>.svd at the repo root.

Python 3 stdlib only. Incremental: every run starts with a cheap metadata
check only (git ls-remote <url> HEAD per source) and compares each SHA with
the one recorded in manifest.json. Sources that still match are not touched.
Only changed sources are re-cloned (logged as "download:") and re-extracted;
their <Family> files, LICENSES/ copy and manifest entries are replaced.
If nothing changed the script prints "up to date" and exits 0 without
modifying anything.

If manifest.json or the family tree is missing (or --full is given) the script
falls back to a full rebuild of everything. Existing clones in .work are
reused when they already point at the wanted SHA.

Usage:
    python fetch.py            # incremental fetch, validate, manifest
    python fetch.py --full     # force a full rebuild
    python fetch.py --clean    # delete .work at the end
"""

import datetime
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT / ".work"
SVD_BASE = ROOT
LIC_OUT = ROOT / "LICENSES"
MANIFEST = ROOT / "manifest.json"

# Repo entries that are never family output dirs. clean_family_dirs() must
# skip these so a full rebuild can never delete the repo itself now that the
# SVD base is ROOT.
PROTECTED = {
    ".git", ".github", ".gitignore", ".work",
    "LICENSES", "README.md", "manifest.json", "fetch.py",
}

SOURCES = [
    {
        "name": "mtb-pdl-cat1",
        "url": "https://github.com/Infineon/mtb-pdl-cat1",
        "globs": ["devices/COMPONENT_CAT1*/svd/*.svd"],
    },
    {
        "name": "mtb-pdl-cat2",
        "url": "https://github.com/Infineon/mtb-pdl-cat2",
        "globs": ["devices/svd/*.svd"],
    },
    {
        "name": "mtb-xmclib-cat3",
        "url": "https://github.com/Infineon/mtb-xmclib-cat3",
        "globs": ["**/*.svd"],
    },
    {
        "name": "mtb-dsl-pse8xxgp",
        "url": "https://github.com/Infineon/mtb-dsl-pse8xxgp",
        "globs": ["pdl/svd/*.svd"],
    },
    {
        "name": "tc375-pac",
        "url": "https://github.com/Infineon/tc375-pac",
        "globs": ["**/*.svd"],
    },
]

# Filename prefix -> family folder. First match wins, order matters.
FAMILY_RULES = [
    ("psoc6", "PSoC6"),
    ("tvii", "TRAVEO"),
    ("cyw", "CYW"),
    ("psc3", "PSC3"),
    ("xmc1", "XMC1000"),
    ("xmc4", "XMC4000"),
    ("xmc5", "XMC5000"),
    ("cat1c", "XMC7000"),
    ("pse84", "PSE84"),
    ("tc3", "AURIX"),
    ("pag", "PAG2S"),
    ("pmg", "PMG1"),
    ("ccg", "CCG"),
    ("wlc", "CCG"),      # wireless charging parts ship in the CCG line
    ("psoc4", "PSoC4"),  # includes PSoC 4 HV (psoc4hv*)
]


def run(cmd, cwd=None):
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def capture(cmd, cwd=None):
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, check=True,
    ).stdout


def rmtree_force(path):
    shutil.rmtree(path, onerror=lambda f, p, e: (Path(p).chmod(0o777), f(p)))


def clean_family_dirs():
    """Full-rebuild cleanup: delete only family output dirs directly under ROOT,
    never the protected repo entries. Because SVD_BASE is now ROOT itself, this
    replaces the old rmtree(SVD_OUT), which would otherwise wipe the whole repo
    including .git."""
    for child in ROOT.iterdir():
        if child.is_dir() and child.name not in PROTECTED:
            rmtree_force(child)


def remote_head(url):
    """Cheap metadata check: HEAD SHA of a remote repo, no artifact download."""
    out = capture(["git", "ls-remote", url, "HEAD"])
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.strip() == "HEAD":
            return sha.strip()
    raise RuntimeError(f"no HEAD in ls-remote output for {url}")


def clone(src, want_sha=None):
    dest = WORK / src["name"]
    if (dest / ".git").exists():
        head = capture(["git", "rev-parse", "HEAD"], cwd=dest).strip()
        if want_sha is None or head == want_sha:
            print(f"reuse existing clone {dest}")
            return dest, head
        rmtree_force(dest)
    print(f"download: git clone {src['url']}")
    run([
        "git", "clone", "--filter=blob:none", "--depth", "1",
        src["url"], str(dest),
    ])
    sha = capture(["git", "rev-parse", "HEAD"], cwd=dest).strip()
    return dest, sha


def family_for(stem):
    low = stem.lower()
    for prefix, fam in FAMILY_RULES:
        if low.startswith(prefix):
            return fam
    return None


def svd_device_name(path):
    """Return //device/name text, or None if the file is not a valid SVD."""
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        print(f"  XML PARSE FAIL {path}: {exc}")
        return None
    root = tree.getroot()
    tag = root.tag.split("}")[-1]
    if tag != "device":
        print(f"  BAD ROOT <{root.tag}> in {path}")
        return None
    name_el = root.find("name")
    if name_el is None:
        for child in root:
            if child.tag.split("}")[-1] == "name":
                name_el = child
                break
    return name_el.text.strip() if name_el is not None and name_el.text else path.stem


def copy_licenses(src_dir, name):
    copied = []
    for cand in sorted(src_dir.glob("LICENSE*")) + sorted(src_dir.glob("LICENCE*")):
        if cand.is_file():
            suffix = cand.suffix if cand.suffix else ".txt"
            dest = LIC_OUT / f"{name}-{cand.name}" if len(
                list(src_dir.glob("LICENSE*"))) > 1 else LIC_OUT / f"{name}-LICENSE{suffix}"
            shutil.copy2(cand, dest)
            copied.append(dest.name)
    return copied


def process_source(src, want_sha=None):
    """Clone one source and copy its SVD files into <Family>/ at the repo root.

    Returns (source_entry, file_entries, issue_strings)."""
    repo_dir, sha = clone(src, want_sha)
    matched = []
    for pattern in src["globs"]:
        matched.extend(repo_dir.glob(pattern))
    matched = sorted(set(matched))
    print(f"{src['name']} @ {sha[:12]}: {len(matched)} svd files")
    lic_files = copy_licenses(repo_dir, src["name"])
    issues = []
    file_entries = []
    for f in matched:
        dev = svd_device_name(f)
        if dev is None:
            issues.append(
                f"{src['name']}: {f.relative_to(repo_dir).as_posix()} failed validation, skipped")
            continue
        fam = family_for(f.stem)
        if fam is None:
            issues.append(f"unmapped family, placed in Unsorted: {src['name']}: {f.name}")
            fam = "Unsorted"
        fam_dir = SVD_BASE / fam
        fam_dir.mkdir(parents=True, exist_ok=True)
        dest = fam_dir / f.name
        if dest.exists():
            issues.append(f"duplicate filename {f.name} ({src['name']}), kept first copy")
            continue
        shutil.copy2(f, dest)
        file_entries.append({
            "path": f"{fam}/{f.name}",
            "device": dev,
            "family": fam,
            "source": src["name"],
            "provenance": "pristine",
        })
    entry = {
        "name": src["name"],
        "url": src["url"],
        "version": sha,
        "license": ", ".join(lic_files) if lic_files else "see README",
        "files": len(file_entries),
    }
    return entry, file_entries, issues


def main():
    clean = "--clean" in sys.argv
    full = "--full" in sys.argv

    old = None
    if not full:
        try:
            old = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print("manifest.json missing or unreadable, doing a full rebuild")
        if old is not None:
            recorded = old.get("files", [])
            if recorded and not any((ROOT / f["path"]).exists() for f in recorded):
                print("family dirs missing, doing a full rebuild")
                old = None
    full = old is None

    old_sources = {s["name"]: s for s in (old or {}).get("sources", [])}
    old_files = (old or {}).get("files", [])
    old_issues = (old or {}).get("issues", [])

    # Cheap metadata check only: compare each remote HEAD with the recorded SHA.
    if full:
        stale = [(src, None) for src in SOURCES]
    else:
        stale = []
        for src in SOURCES:
            head = remote_head(src["url"])
            rec = old_sources.get(src["name"], {}).get("version")
            state = "up to date" if head == rec else "changed"
            print(f"check {src['name']}: remote {head[:12]} recorded {(rec or 'none')[:12]} -> {state}")
            if head != rec:
                stale.append((src, head))
        if not stale:
            print("up to date")
            return

    stale_names = {src["name"] for src, _ in stale}

    WORK.mkdir(exist_ok=True)
    LIC_OUT.mkdir(exist_ok=True)
    if full:
        clean_family_dirs()
    else:
        # Drop the files previously extracted from the sources being rebuilt.
        for entry in old_files:
            if entry["source"] in stale_names:
                p = ROOT / entry["path"]
                if p.exists():
                    p.unlink()

    new_sources = {}
    new_files = {}
    new_issues = {}
    for src, want_sha in stale:
        entry, files, issues = process_source(src, want_sha)
        new_sources[src["name"]] = entry
        new_files[src["name"]] = files
        new_issues[src["name"]] = issues

    # Merge: rebuilt sources get fresh manifest data, untouched sources keep
    # their recorded entries, files and issues.
    manifest_sources = []
    manifest_files = []
    manifest_issues = []
    for src in SOURCES:
        name = src["name"]
        if name in stale_names:
            manifest_sources.append(new_sources[name])
            manifest_files.extend(new_files[name])
            manifest_issues.extend(new_issues[name])
        else:
            manifest_sources.append(old_sources[name])
            manifest_files.extend(f for f in old_files if f["source"] == name)
            manifest_issues.extend(i for i in old_issues if name in i)
    manifest_files.sort(key=lambda x: x["path"])

    # Prune family dirs left empty after a rebuild.
    for d in sorted(SVD_BASE.iterdir()):
        if d.is_dir() and d.name not in PROTECTED and not any(d.iterdir()):
            d.rmdir()

    total_bytes = sum((ROOT / f["path"]).stat().st_size for f in manifest_files)
    manifest = {
        "vendor": "Infineon",
        "generated": datetime.date.today().isoformat(),
        "sources": manifest_sources,
        "files": manifest_files,
        "stats": {
            "total_files": len(manifest_files),
            "total_bytes": total_bytes,
        },
        "issues": manifest_issues,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"\nrebuilt sources: {', '.join(sorted(stale_names))}")
    print(f"total: {len(manifest_files)} files, {total_bytes/1e6:.1f} MB")
    if manifest_issues:
        print("ISSUES:")
        for i in manifest_issues:
            print("  ", i)

    if clean and WORK.exists():
        rmtree_force(WORK)
        print("removed .work")


if __name__ == "__main__":
    main()
