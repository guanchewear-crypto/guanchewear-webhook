#!/usr/bin/env python3
"""One command: back up GuancheWear, verify it, encrypt it, and ship it off-site.

    python scripts/backup-and-upload.py [--to DIR]... [--dry-run]

Pipeline (each step delegated, so there is one source of truth per concern):
    backup-all.py      build the backup folder
    verify-backup.py   refuse to continue unless the backup is intact
    encrypt-backup.py  pack + encrypt it for safe transport
    then copy the encrypted archive to every destination and re-verify the copy

The passphrase is NEVER copied off the machine: it belongs in a password
manager, not next to the archive it protects.

Destinations are auto-detected (OneDrive, Google Drive, iCloud Drive) so this
starts working with a given provider the moment its desktop client exists.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = Path.home()
BACKUPS = HOME / "guanchewear-backups"
FOLDER_NAME = "GuancheWear-Backups"
# Never leaves the machine: it must stay apart from the archive it protects.
PROTECTED = ("PASSPHRASE",)

# Checked in order; any that exists becomes an upload target automatically.
CANDIDATE_CLOUDS = (
    ("OneDrive", HOME / "OneDrive"),
    ("Google Drive", HOME / "Google Drive"),
    ("Google Drive", HOME / "My Drive"),
    ("iCloud Drive", HOME / "iCloudDrive"),
    ("Dropbox", HOME / "Dropbox"),
    ("MEGA", HOME / "MEGAsync"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def human(size: int) -> str:
    return f"{size / 1048576:.1f} MB"


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [sys.executable, str(HERE / script), *args],
        capture_output=True, text=True, timeout=1800,
    )
    tail = [line for line in result.stdout.splitlines() if line.strip()][-3:]
    for line in tail:
        print(f"     {line.strip()}")
    if result.returncode != 0:
        print(f"\nABORT  {script} failed (exit {result.returncode})", file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr.strip()[-600:], file=sys.stderr)
        raise SystemExit(1)
    return result


def newest_backup() -> Path:
    folders = sorted(p for p in BACKUPS.glob("*") if p.is_dir())
    if not folders:
        print("ABORT  no backup was produced", file=sys.stderr)
        raise SystemExit(1)
    return folders[-1]


def targets(explicit: list[Path]) -> list[tuple[str, Path]]:
    if explicit:
        return [(str(p), p) for p in explicit]
    found = [(name, path) for name, path in CANDIDATE_CLOUDS if path.is_dir()]
    found.extend(mounted_clouds())
    unique: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for name, path in found:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append((name, path))
    return unique


def parse_google_drive_volumes(output: str) -> list[Path]:
    """Turn `Get-CimInstance Win32_LogicalDisk` output into volume roots.

    Drive for desktop mounts a virtual volume labelled "Google Drive", so it
    never appears as a folder in the user profile and a folder scan misses it.
    """
    volumes: list[Path] = []
    for line in output.splitlines():
        device = line.strip().rstrip(":").upper()
        if len(device) == 1 and device.isalpha():
            volumes.append(Path(f"{device}:/"))
    return volumes


def resolve_drive_root(volume: Path) -> Path | None:
    """Find the account folder inside a Drive volume.

    The folder is "My Drive" in English but localised elsewhere - Spanish
    Windows shows "Mi unidad" - so never hardcode the English name.
    """
    if not volume.is_dir():
        return None
    for name in ("My Drive", "Mi unidad", "Mon Drive", "Meine Ablage", "Il mio Drive"):
        candidate = volume / name
        if candidate.is_dir():
            return candidate
    for entry in sorted(volume.iterdir()):
        if entry.is_dir() and not entry.name.startswith("$"):
            return entry
    return None


def mounted_clouds() -> list[tuple[str, Path]]:
    query = (
        "Get-CimInstance Win32_LogicalDisk | "
        "Where-Object { $_.VolumeName -eq 'Google Drive' } | "
        "Select-Object -ExpandProperty DeviceID"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", query],
            capture_output=True, text=True, timeout=90,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    destinations: list[tuple[str, Path]] = []
    for volume in parse_google_drive_volumes(result.stdout):
        root = resolve_drive_root(volume)
        if root is not None:
            destinations.append(("Google Drive", root))
    return destinations


def ship(sources: list[Path], destinations: list[tuple[str, Path]]) -> list[str]:
    """Copy sources into each destination, skipping protected files.

    Callers may pass the passphrase; the guard here is what keeps it local, so
    it is load bearing rather than an accident of which files get listed.
    """
    shipped: list[str] = []
    for name, path in destinations:
        folder = path / FOLDER_NAME
        folder.mkdir(parents=True, exist_ok=True)
        for source in sources:
            if any(token in source.name for token in PROTECTED):
                continue
            destination = folder / source.name
            shutil.copy2(source, destination)
            landed = destination.stat().st_size == source.stat().st_size and sha256(destination) == sha256(source)
            if not landed:
                raise RuntimeError(f"copy verification failed for {destination}")
            shipped.append(f"{name}:{source.name}")
    return shipped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", type=Path, action="append", default=[], help="extra destination folder (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="do everything except the copy")
    parser.add_argument("--reuse", action="store_true", help="upload the newest existing backup instead of building a new one")
    args = parser.parse_args()

    if args.reuse:
        backup = newest_backup()
        print(f"1. reusing the newest backup: {backup.name}")
    else:
        print("1. building the backup")
        run("backup-all.py")
        backup = newest_backup()
        print(f"     -> {backup.name}")

    print("2. verifying the backup (refusing to ship a broken one)")
    run("verify-backup.py", str(backup))

    archive = backup.with_name(backup.name + ".tar.gz.enc")
    keyfile = backup.with_name(backup.name + ".PASSPHRASE.txt")
    sums = backup.with_name(backup.name + ".tar.gz.sha256")
    if archive.is_file() and sums.is_file():
        # Re-encrypting would mint a fresh passphrase and orphan the current one.
        print("3. already encrypted, keeping the existing passphrase")
    else:
        print("3. encrypting for transport")
        run("encrypt-backup.py", str(backup))
    if not archive.is_file() or not sums.is_file():
        print("ABORT  encryption did not produce the expected files", file=sys.stderr)
        return 1
    digest = sha256(archive)
    print(f"     -> {archive.name}  {human(archive.stat().st_size)}  {digest[:16]}")

    print("4. uploading")
    destinations = targets(args.to)
    if not destinations:
        print("     no cloud folder found. Install Google Drive/OneDrive, or pass --to DIR.")
        print("     The backup and its encrypted archive stay available locally.")
        return 0
    if args.dry_run:
        for name, path in destinations:
            print(f"     DRY RUN  would copy to [{name}] {path / FOLDER_NAME}")
        return 0

    for name, path in destinations:
        print(f"     [{name}] -> {path / FOLDER_NAME}")
    try:
        # The passphrase is passed on purpose: the guard must reject it.
        for entry in ship([archive, sums, keyfile], destinations):
            print(f"     {entry}: OK")
    except RuntimeError as error:
        print(f"ABORT  {error}", file=sys.stderr)
        return 1

    print()
    print(f"UPLOAD_OK  {backup.name}  ->  {len(destinations)} destination(s)")
    print(f"  passphrase stays local: {keyfile}")
    print("  keep it in a password manager, then delete that file")
    print("  restore: decrypt, run 'sha256sum -c <file>.tar.gz.sha256', then extract")
    return 0


if __name__ == "__main__":
    sys.exit(main())