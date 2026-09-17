#!/usr/bin/env python3
"""Verify the backup tooling behaves as intended.

Companion to verify-backup.py, which checks a backup's artefacts. This one
checks the scripts themselves plus the secret-exposure guard, and delegates
artefact integrity to verify-backup.py so there is a single source of truth.

Usage:
    python scripts/verify-tooling.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = Path.home()
BACKEND = HERE.parent
FRONTEND = BACKEND / "guanchewear-landing"
BACKUPS = HOME / "guanchewear-backups"
SITE_DB = (
    HOME / ".wordpress-playground" / "sites"
    / "a4c628688111e18980e698350bf61da13f694daaa732c687c7f0b82b59eb140f"
    / "wp-content" / "database" / ".ht.sqlite"
)

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   <- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(module_name: str):
    # Hyphens are only invalid in the module name, not in the file name.
    spec = importlib.util.spec_from_file_location(module_name.replace("-", "_"), HERE / f"{module_name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def latest_backup() -> Path | None:
    folders = sorted(p for p in BACKUPS.glob("*") if p.is_dir())
    return folders[-1] if folders else None


def git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    # git is a native binary: it wants C:/..., not the MSYS /c/... form.
    return subprocess.run(["git", "-C", cwd.as_posix(), *args], capture_output=True, text=True, timeout=120)


def verify_secret_guard() -> None:
    print("1. .env must be ignored in both repos (it was committable)")
    for label, repo in (("backend", BACKEND), ("frontend", FRONTEND)):
        ignored = git(["check-ignore", ".env"], repo)
        check(f"{label}: .env is ignored", ignored.returncode == 0, "not ignored")
        check(f"{label}: .env is not tracked", git(["ls-files", "--error-unmatch", ".env"], repo).returncode != 0, "already tracked")
        # A control: the guard must not be ignoring everything.
        check(f"{label}: tracked sources are still visible to git", git(["check-ignore", "package.json"], repo).returncode != 0, "package.json ignored?")


def verify_archive_contents(backup: Path) -> None:
    print("2. archive contents")
    with zipfile.ZipFile(backup / "01-frontend-src.zip") as archive:
        names = archive.namelist()
    check("frontend zip keeps .vercel/project.json", any(n.endswith("/.vercel/project.json") for n in names))
    check("frontend zip excludes node_modules", not any("node_modules" in n for n in names))
    check("frontend zip excludes nested .git", not any("/.git/" in n for n in names))


def verify_dump(backup: Path) -> None:
    print("3. SQL dump is genuinely restorable")
    dump = backup / "08-wordpress-db-dump.sql"
    if not dump.is_file():
        check("SQL dump exists", False, "missing")
        return
    text = dump.read_text(encoding="utf-8")
    try:
        con = sqlite3.connect(":memory:")
        con.executescript(text)
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        rows = sum(con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables if t.startswith("wp_"))
        con.close()
        restored = True
    except sqlite3.Error as error:
        tables, rows, restored = set(), 0, False
        print(f"     restore failed: {error}")

    check("dump restores into a fresh database", restored, "sqlite refused the script")
    check("dump contains WordPress tables", any(t.startswith("wp_") for t in tables), f"{len(tables)} tables")
    check("restored database holds real rows", rows > 0, f"{rows} rows")

    if SITE_DB.is_file():
        # The dump copies the database first; a missing close() left a locked
        # temp file behind on Windows and the second call blew up.
        with tempfile.TemporaryDirectory(prefix="hermes-tooling-dump-") as tmp:
            first, second = Path(tmp) / "a.sql", Path(tmp) / "b.sql"
            dump_sqlite = load("backup-all").dump_sqlite
            dump_sqlite(SITE_DB, first)
            dump_sqlite(SITE_DB, second)
            check("dumping twice leaves no locked handle", first.stat().st_size > 0 and first.read_bytes() == second.read_bytes())
    else:
        check("playground database available", False, str(SITE_DB))


def verify_encryption(backup: Path) -> None:
    print("4. encryption round-trip and wrong-key detection")
    archive = backup.with_name(backup.name + ".tar.gz.enc")
    keyfile = backup.with_name(backup.name + ".PASSPHRASE.txt")
    sums = backup.with_name(backup.name + ".tar.gz.sha256")
    for path in (archive, keyfile, sums):
        check(f"{path.name} exists", path.is_file())
    if not all(p.is_file() for p in (archive, keyfile, sums)):
        return

    recorded = sums.read_text(encoding="utf-8").split()
    check("plaintext checksum file is well formed", len(recorded) == 2 and bool(re.fullmatch(r"[0-9a-f]{64}", recorded[0])))
    lines = keyfile.read_text(encoding="utf-8").splitlines()
    passphrase = lines[0].strip() if lines else ""
    # `openssl -pass file:` reads the FIRST line, so that line must be the key.
    # A human-readable header here made the documented restore command read
    # "Passphrase for ..." as the key: it could never work, and this verifier
    # did not notice because it decrypted through the environment instead.
    check("key file is the passphrase alone", len(lines) == 1, f"{len(lines)} lines")
    check("passphrase has real entropy", len(passphrase) >= 30, f"length {len(passphrase)}")

    def decrypt(key_source: str, dest: Path) -> None:
        subprocess.run(
            ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "600000",
             "-pass", key_source, "-in", archive.as_posix(), "-out", dest.as_posix()],
            capture_output=True, text=True, timeout=900,
        )

    with tempfile.TemporaryDirectory(prefix="hermes-tooling-dec-") as tmp:
        good = Path(tmp) / "good.tar.gz"
        # Exercise the documented command, not a private re-implementation.
        decrypt(f"file:{keyfile.as_posix()}", good)
        check("documented decrypt command restores the plaintext", sha256(good) == recorded[0],
              f"expected {recorded[0][:12]} got {sha256(good)[:12]}")
        bad = Path(tmp) / "bad.tar.gz"
        decrypt("pass:wrong-passphrase", bad)
        # AES-CBC is unauthenticated: the checksum is the only gate.
        check("wrong passphrase is detected by the checksum", sha256(bad) != recorded[0], "wrong key matched")

    # The documented recovery path is the script, so run it end to end.
    restore = Path(__file__).with_name("restore-backup.py")
    result = subprocess.run([sys.executable, str(restore), archive.as_posix(), "--list"],
                            capture_output=True, text=True, timeout=900)
    check("restore-backup.py reads the backup", result.returncode == 0 and "RESTORE_OK" in result.stdout,
          (result.stdout.strip() or result.stderr.strip())[-140:])


def verify_upload_guard() -> None:
    print("5. upload guard: the passphrase must never leave the machine")
    module = load("backup-and-upload")
    clouds = {name for name, _ in module.CANDIDATE_CLOUDS}
    check("Google Drive is auto-detected once its client exists", "Google Drive" in clouds, str(sorted(clouds)))
    check("OneDrive and iCloud are candidates", {"OneDrive", "iCloud Drive"} <= clouds)
    # Drive for desktop mounts a virtual volume, not a profile folder.
    check("parses a mounted Google Drive volume",
          module.parse_google_drive_volumes("G:\n") == [Path("G:/")],
          str(module.parse_google_drive_volumes("G:\n")))
    check("empty volume output yields nothing", module.parse_google_drive_volumes("") == [])
    check("malformed volume output is ignored", module.parse_google_drive_volumes("AB:\nnot-a-disk\n") == [],
          str(module.parse_google_drive_volumes("AB:\nnot-a-disk\n")))
    # The account folder is localised: Spanish Windows shows "Mi unidad".
    with tempfile.TemporaryDirectory(prefix="hermes-tooling-drive-") as tmp:
        volume = Path(tmp)
        check("a volume with no account folder resolves to None", module.resolve_drive_root(volume) is None)
        check("a missing volume resolves to None", module.resolve_drive_root(volume / "does-not-exist") is None)
        (volume / "Mi unidad").mkdir()
        check("resolves the localised 'Mi unidad' root", module.resolve_drive_root(volume) == volume / "Mi unidad")
        (volume / "My Drive").mkdir()
        check("prefers the English 'My Drive' name", module.resolve_drive_root(volume) == volume / "My Drive")
        (volume / "$RECYCLE.BIN").mkdir()
        check("ignores the recycle bin when nothing else matches",
              module.resolve_drive_root(volume) in {volume / "My Drive", volume / "Mi unidad"})

    with tempfile.TemporaryDirectory(prefix="hermes-tooling-ship-") as tmp:
        source = Path(tmp) / "src"
        source.mkdir()
        archive = source / "x.tar.gz.enc"
        archive.write_bytes(b"encrypted-blob")
        sums = source / "x.tar.gz.sha256"
        sums.write_text("0" * 64 + "  x.tar.gz\n", encoding="utf-8")
        key = source / "x.PASSPHRASE.txt"
        key.write_text("super-secret-passphrase\n", encoding="utf-8")

        cloud = Path(tmp) / "cloud"
        cloud.mkdir()
        # Pass the passphrase on purpose: the guard must reject it.
        shipped = module.ship([archive, sums, key], [("Test", cloud)])
        landed = {p.name for p in (cloud / module.FOLDER_NAME).iterdir()}

        check("encrypted archive is shipped", "x.tar.gz.enc" in landed)
        check("plaintext checksum is shipped", "x.tar.gz.sha256" in landed)
        check("PASSPHRASE is NOT shipped", not any("PASSPHRASE" in n for n in landed), str(sorted(landed)))
        check("guard reports only what it shipped", len(shipped) == 2, str(shipped))
        check("shipped copy is byte-identical", (cloud / module.FOLDER_NAME / "x.tar.gz.enc").read_bytes() == b"encrypted-blob")
        check("explicit destinations replace auto-detection", module.targets([cloud]) == [(str(cloud), cloud)])


def verify_artifact_integrity(backup: Path) -> None:
    print("6. artefact integrity (delegated to verify-backup.py)")
    result = subprocess.run([sys.executable, str(HERE / "verify-backup.py"), str(backup)], capture_output=True, text=True, timeout=900)
    check("verify-backup.py reports the backup intact", result.returncode == 0 and "VERIFY_OK" in result.stdout, result.stdout.strip()[-140:])
    check("verify-backup.py covers the .sql artifact", "08-wordpress-db-dump.sql resolves" in result.stdout)
    check("verify-backup.py regex matches .sql", bool(load("verify-backup").ARTIFACT_REF.fullmatch("08-wordpress-db-dump.sql")))


def main() -> int:
    backup = latest_backup()
    if backup is None:
        print(f"VERIFY_FAILED  no backup found in {BACKUPS}", file=sys.stderr)
        return 1
    print(f"tooling under test, newest backup: {backup.name}\n")

    verify_secret_guard()
    verify_archive_contents(backup)
    verify_dump(backup)
    verify_encryption(backup)
    verify_upload_guard()
    verify_artifact_integrity(backup)

    print()
    if failures:
        print(f"VERIFY_FAILED  {len(failures)} check(s) failed")
        for name in failures:
            print(f"  - {name}")
        return 1
    print(f"VERIFY_OK  tooling verified against {backup.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())