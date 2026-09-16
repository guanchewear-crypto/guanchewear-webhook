#!/usr/bin/env python3
"""Verify a GuancheWear backup produced by backup-all.py.

Usage:
    python scripts/verify-backup.py [backup_dir]

Defaults to the newest folder under ~/guanchewear-backups.

Checks, in order of strength:
  1. the expected files exist and text files use LF (CRLF breaks sha256sum -c)
  2. every checksum line is well formed, names a real file and matches
  3. the checksum set equals the artifacts recorded in manifest.json
  4. manifest.json sizes and hashes match the files on disk
  5. every artifact referenced by MANIFEST.md resolves
  6. each git bundle actually clones and lands on the recorded commit
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BACKUPS = Path.home() / "guanchewear-backups"
REQUIRED = ("MANIFEST.md", "SHA256SUMS.txt", "manifest.json")
HASH = re.compile(r"[0-9a-f]{64}")
ARTIFACT_REF = re.compile(r"\b0[0-9]-[a-z-]+\.(?:zip|bundle|sql)\b")

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    suffix = f"   <- {detail}" if detail and not ok else ""
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{suffix}")
    if not ok:
        failures.append(label)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_backup(argv: list[str]) -> Path | None:
    if len(argv) > 1:
        return Path(argv[1])
    folders = sorted(p for p in BACKUPS.glob("*") if p.is_dir())
    return folders[-1] if folders else None


def verify_text_files(backup: Path) -> None:
    print("1. structure and line endings")
    for name in REQUIRED:
        check(f"{name} exists", (backup / name).is_file())
    for name in ("MANIFEST.md", "SHA256SUMS.txt"):
        target = backup / name
        if target.is_file():
            raw = target.read_bytes()
            check(f"{name} uses LF only", b"\r" not in raw, f"{raw.count(bytes([13]))} CR bytes")


def verify_checksums(backup: Path, artifacts: list[dict]) -> None:
    print("2. checksum file")
    listed: dict[str, str] = {}
    for number, line in enumerate((backup / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines(), 1):
        digest, _, name = line.partition("  ")
        # A truncated line (hash, no name) still counts as a line: validate shape.
        check(f"line {number} is '<64-hex>  <filename>'", bool(HASH.fullmatch(digest)) and bool(name), f"got {line[:48]!r}")
        if not name:
            continue
        listed[name] = digest
        target = backup / name
        check(f"{name} is a file", target.is_file())
        if target.is_file():
            check(f"{name} hash matches", sha256(target) == digest)

    print("3. checksum set vs manifest.json")
    recorded = {str(a["name"]) for a in artifacts}
    check("checksums cover exactly the recorded artifacts", set(listed) == recorded, f"checksums={sorted(listed)} recorded={sorted(recorded)}")


def verify_manifest_json(backup: Path) -> list[dict]:
    print("4. manifest.json entries")
    data = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    for artifact in data["artifacts"]:
        target = backup / artifact["name"]
        if not target.is_file():
            check(f"{artifact['name']} present", False, "missing")
            continue
        check(f"{artifact['name']} size matches", target.stat().st_size == artifact["bytes"])
        check(f"{artifact['name']} sha256 matches", sha256(target) == artifact["sha256"])
    return data["artifacts"]


def verify_manifest_md(backup: Path) -> None:
    print("5. MANIFEST.md references")
    text = (backup / "MANIFEST.md").read_text(encoding="utf-8")
    refs = sorted(set(ARTIFACT_REF.findall(text)))
    check("manifest cites artifacts", bool(refs))
    for ref in refs:
        check(f"{ref} resolves", (backup / ref).exists())


def verify_bundles(backup: Path, artifacts: list[dict], repos: list[dict]) -> None:
    print("6. git bundles restore to the recorded commits")
    heads = {r["head"] for r in repos}
    with tempfile.TemporaryDirectory(prefix="hermes-verify-bundle-") as tmp:
        for artifact in artifacts:
            name = str(artifact["name"])
            if not name.endswith(".bundle"):
                continue
            dest = Path(tmp) / name.replace(".bundle", "")
            result = subprocess.run(
                ["git", "clone", "--quiet", str(backup / name), str(dest)],
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode != 0:
                check(f"{name} clones", False, result.stderr.strip()[:80])
                continue
            head = subprocess.run(
                ["git", "-C", str(dest), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=120,
            ).stdout.strip()
            check(f"{name} restores a known commit", head in heads, f"clone HEAD {head[:10]} not in {sorted(h[:10] for h in heads)}")


def main() -> int:
    backup = resolve_backup(sys.argv)
    if backup is None or not backup.is_dir():
        print(f"VERIFY_FAILED  no backup folder found in {BACKUPS}", file=sys.stderr)
        return 1
    print(f"backup under test: {backup}\n")

    verify_text_files(backup)
    if not (backup / "manifest.json").is_file():
        print("\nVERIFY_FAILED  manifest.json missing, cannot continue", file=sys.stderr)
        return 1

    data = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    verify_checksums(backup, data["artifacts"])
    verify_manifest_json(backup)
    verify_manifest_md(backup)
    verify_bundles(backup, data["artifacts"], data["repos"])

    print()
    if failures:
        print(f"VERIFY_FAILED  {len(failures)} check(s) failed")
        for name in failures:
            print(f"  - {name}")
        return 1
    print(f"VERIFY_OK  backup={backup.name} artifacts={len(data['artifacts'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())