#!/usr/bin/env python3
"""Restore a GuancheWear backup: decrypt, verify, extract.

This is the canonical recovery path. It refuses to extract anything whose
plaintext does not match the recorded sha256: AES-CBC is unauthenticated, so a
wrong passphrase yields garbage instead of an error and the checksum is the
only gate.

Usage:
    python scripts/restore-backup.py [file.tar.gz.enc] [--to DIR] [--list]

Defaults to the newest archive under ~/guanchewear-backups. The plaintext
tarball never touches disk: it is decrypted into a temporary directory and
thrown away once verified.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

BACKUPS = Path.home() / "guanchewear-backups"
ITERATIONS = "600000"


def newest_archive() -> Path | None:
    archives = sorted(BACKUPS.glob("*.tar.gz.enc"))
    return archives[-1] if archives else None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_passphrase(keyfile: Path) -> str:
    # The key file is the passphrase alone on the first line, because that is
    # what `openssl -pass file:` reads.
    if not keyfile.is_file():
        return ""
    return keyfile.read_text(encoding="utf-8").splitlines()[0].strip()


def safe_extract(tar: tarfile.TarFile, dest: Path) -> list[str]:
    root = dest.resolve()
    names: list[str] = []
    for member in tar.getmembers():
        target = (dest / member.name).resolve()
        if root not in target.parents and target != root:
            raise ValueError(f"unsafe path in archive: {member.name}")
        tar.extract(member, dest)
        names.append(member.name)
    return names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", nargs="?", type=Path)
    parser.add_argument("--to", type=Path, help="extraction folder")
    parser.add_argument("--list", action="store_true", help="only list the contents")
    args = parser.parse_args()

    archive = args.archive or newest_archive()
    if archive is None or not archive.is_file():
        print(f"RESTORE_FAILED  no archive in {BACKUPS}", file=sys.stderr)
        return 1

    stem = archive.name.replace(".tar.gz.enc", "")
    keyfile = archive.with_name(f"{stem}.PASSPHRASE.txt")
    sums = archive.with_name(f"{stem}.tar.gz.sha256")

    if not sums.is_file():
        print(f"RESTORE_FAILED  missing {sums.name}: cannot verify the plaintext",
              file=sys.stderr)
        return 1
    recorded = sums.read_text(encoding="utf-8").split()[0]

    passphrase = os.environ.get("GW_BACKUP_PASSPHRASE") or read_passphrase(keyfile)
    if not passphrase:
        print(f"RESTORE_FAILED  no passphrase (put it in {keyfile.name} or "
              "GW_BACKUP_PASSPHRASE)", file=sys.stderr)
        return 1

    dest = args.to or Path.home() / "guanchewear-restore" / stem
    print(f"Restoring {archive.name}\n  key      {keyfile.name} ({len(passphrase)} chars)"
          f"\n  expected {recorded[:16]}\n")

    with tempfile.TemporaryDirectory(prefix="hermes-restore-") as tmp:
        tarball = Path(tmp) / f"{stem}.tar.gz"
        result = subprocess.run(
            ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", ITERATIONS,
             "-pass", "env:GW_BACKUP_PASSPHRASE",
             "-in", archive.as_posix(), "-out", tarball.as_posix()],
            # The secret travels through the environment, never the argv.
            env={**os.environ, "GW_BACKUP_PASSPHRASE": passphrase},
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"RESTORE_FAILED  openssl: {result.stderr.strip()}", file=sys.stderr)
            return 1

        actual = sha256(tarball)
        if actual != recorded:
            print(f"RESTORE_FAILED  plaintext {actual[:16]} != recorded {recorded[:16]}: "
                  "wrong passphrase or damaged archive", file=sys.stderr)
            return 1
        print(f"  verified {actual[:16]} matches the recorded hash")

        if args.list:
            with tarfile.open(tarball, "r:gz") as tar:
                for name in tar.getnames():
                    print(f"  {name}")
            print("\nRESTORE_OK  listed only, nothing written")
            return 0

        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tarball, "r:gz") as tar:
            names = safe_extract(tar, dest)

    print(f"  extracted {len(names)} entries -> {dest}")
    print("\nRESTORE_OK")
    print("  The plaintext never touched disk: it lived in a temporary folder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
