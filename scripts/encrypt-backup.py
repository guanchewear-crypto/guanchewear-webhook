#!/usr/bin/env python3
"""Encrypt a GuancheWear backup into one portable, safe-to-upload file.

The backup contains .env (Stripe, OpenAI, SMTP) and a WordPress database, so
the plain folder must never leave the machine as-is. This packs it into a
tar.gz and encrypts it with AES-256-CBC (PBKDF2, 600k iterations) so the
result can be stored on GitHub, Drive, Dropbox or anywhere else.

Usage:
    python scripts/encrypt-backup.py [backup_dir] [--out FILE]

Defaults to the newest folder under ~/guanchewear-backups. The passphrase is
taken from GW_BACKUP_PASSPHRASE, otherwise a strong one is generated and
written next to the archive.

Decrypt:
    python scripts/restore-backup.py <file>.tar.gz.enc

    Or by hand (the key file holds the passphrase alone, first line):
    openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \\
      -pass file:<file>.PASSPHRASE.txt -in <file>.tar.gz.enc -out backup.tar.gz
    sha256sum -c <file>.tar.gz.sha256    # MUST pass: AES-CBC cannot detect a
                                         # wrong passphrase, it returns garbage
    tar -xzf backup.tar.gz
"""

from __future__ import annotations

import argparse
import hashlib
import os
import secrets
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

BACKUPS = Path.home() / "guanchewear-backups"
ITERATIONS = "600000"


def newest_backup() -> Path | None:
    folders = sorted(p for p in BACKUPS.glob("*") if p.is_dir())
    return folders[-1] if folders else None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def human(size: int) -> str:
    return f"{size / 1048576:.1f} MB" if size >= 1048576 else f"{size / 1024:.0f} KB"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("backup", nargs="?", type=Path)
    parser.add_argument("--out", type=Path, help="destination .enc file")
    args = parser.parse_args()

    backup = args.backup or newest_backup()
    if backup is None or not backup.is_dir():
        print(f"ENCRYPT_FAILED  no backup folder in {BACKUPS}", file=sys.stderr)
        return 1

    passphrase = os.environ.get("GW_BACKUP_PASSPHRASE") or secrets.token_urlsafe(24)
    generated = "GW_BACKUP_PASSPHRASE" not in os.environ

    dest = args.out or BACKUPS / f"{backup.name}.tar.gz.enc"
    if dest.exists():
        dest.unlink()

    print(f"Encrypting {backup.name} -> {dest.name}\n")

    with tempfile.TemporaryDirectory(prefix="hermes-encrypt-") as tmp:
        tarball = Path(tmp) / f"{backup.name}.tar.gz"
        with tarfile.open(tarball, "w:gz") as tar:
            tar.add(backup, arcname=backup.name)
        raw = tarball.stat().st_size
        # AES-CBC is unauthenticated: decrypting with the wrong passphrase yields
        # garbage rather than an error, so record the plaintext hash to check
        # against after decrypting.
        raw_sha = sha256(tarball)

        result = subprocess.run(
            ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", ITERATIONS, "-salt",
             "-pass", "env:GW_BACKUP_PASSPHRASE",
             "-in", str(tarball), "-out", str(dest)],
            # Pass the secret through the environment: arguments are visible in
            # the process list, the environment is not.
            env={**os.environ, "GW_BACKUP_PASSPHRASE": passphrase},
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"ENCRYPT_FAILED  openssl: {result.stderr.strip()}", file=sys.stderr)
            return 1

    # The key file holds the passphrase alone, on the first line: `openssl -pass
    # file:` reads that line and nothing else, so a human-readable header would
    # silently become the key and the documented restore command would never
    # work. The warning lives in the printed output instead.
    keyfile = dest.with_name(dest.name.replace(".tar.gz.enc", "") + ".PASSPHRASE.txt")
    keyfile.write_text(passphrase + "\n", encoding="utf-8", newline="\n")

    sums = dest.with_name(dest.name.replace(".tar.gz.enc", ".tar.gz.sha256"))
    sums.write_text(f"{raw_sha}  {backup.name}.tar.gz\n", encoding="utf-8", newline="\n")

    print(f"  tarball          {human(raw)}")
    print(f"  tarball sha256   {raw_sha}")
    print(f"  encrypted        {human(dest.stat().st_size)}")
    print(f"  sha256           {sha256(dest)}")
    print(f"  passphrase file  {keyfile}")
    print(f"  checksum file    {sums}")
    print(f"  passphrase {'generated' if generated else 'from environment'}"
          f" ({len(passphrase)} chars)")
    print()
    print("ENCRYPT_OK")
    print(f"  restore: python scripts/restore-backup.py {dest.name}")
    print(f"  manual : openssl enc -d -aes-256-cbc -pbkdf2 -iter {ITERATIONS} "
          f"-pass file:{keyfile.name} -in {dest.name} -out {backup.name}.tar.gz")
    print(f"  verify : sha256sum -c {sums.name}   # obligatorio antes de extraer")
    print("  AVISO: mueve la passphrase a tu gestor de claves y borra el archivo .txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())