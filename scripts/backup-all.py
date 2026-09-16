#!/usr/bin/env python3
"""Full backup for the GuancheWear project.

Backs up, into one timestamped folder:

  01 frontend working tree   (React/Vite app, excluding regenerable caches)
  02 frontend git history    (bundle: every ref, no remote config)
  03 backend working tree    (API + docs + .env)
  04 backend git history     (bundle)
  05 wordpress theme         (child theme + dist mounted into WordPress)
  06 wordpress site          (WP core, plugins and the SQLite database)
  07 deploy package          (the ZIP handed over for upload)

Deliberate exclusions:
  * node_modules, .vercel, __pycache__ - regenerable from package-lock.json
  * .git directories - their config embeds an access token in the remote URL.
    History is preserved as a git bundle instead, which carries refs and
    objects but no config.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime
from pathlib import Path

HOME = Path.home()
STAMP = datetime.now().strftime("%Y-%m-%d_%H%M%S")

BACKUP_ROOT = HOME / "guanchewear-backups" / STAMP

FRONTEND = HOME / "guanchewear-webhook" / "guanchewear-landing"
BACKEND = HOME / "guanchewear-webhook"
THEME = HOME / "guanchewear-wp-migration" / "guanchewear-landing"
SITE = HOME / ".wordpress-playground" / "sites" / "a4c628688111e18980e698350bf61da13f694daaa732c687c7f0b82b59eb140f"
DEPLOY_PACKAGE = HOME / "guanchewear-wp-migration" / "guanchewear-landing.zip"

# desktop-attachments holds cached chat attachments (many duplicate tar exports),
# not project content. .hermes/plans IS project content and stays. .vercel is
# kept: project.json is what lets the project be re-linked for deployment.
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".cache", ".turbo", "desktop-attachments"}
SKIP_FILES = {".DS_Store", "Thumbs.db"}
SKIP_SUFFIX = (".log",)

REPOS = {
    "02-frontend-git.bundle": FRONTEND,
    "04-backend-git.bundle": BACKEND,
}


def should_skip(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return True
    if path.name in SKIP_FILES or path.name.endswith(SKIP_SUFFIX):
        return True
    return False


def collect(root: Path, exclude_roots: tuple[Path, ...] = ()) -> list[Path]:
    files: list[Path] = []
    for item in sorted(root.rglob("*")):
        if not item.is_file() or should_skip(item):
            continue
        if any(item.is_relative_to(ex) and item != ex for ex in exclude_roots):
            continue
        files.append(item)
    return files


def zip_paths(target: Path, root: Path, files: list[Path], base: str) -> int:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for item in files:
            archive.write(item, Path(base) / item.relative_to(root))
    return len(files)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, timeout=120,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def human(size: int) -> str:
    return f"{size / 1048576:.1f} MB" if size >= 1048576 else f"{size / 1024:.0f} KB"


def dump_sqlite(db: Path, out: Path) -> int:
    """Write the WordPress database as portable SQL text.

    The live site may hold the database open, so dump from a copy instead of
    risking a lock on the original.
    """
    with tempfile.TemporaryDirectory(prefix="hermes-backup-db-") as tmp:
        copy = Path(tmp) / db.name
        shutil.copy2(db, copy)
        for sidecar in (".wal", ".shm"):
            extra = db.with_name(db.name + sidecar)
            if extra.is_file():
                shutil.copy2(extra, copy.with_name(copy.name + sidecar))
        # sqlite3.Connection.__exit__ only commits, it does NOT close, and an
        # open handle makes the temp cleanup fail on Windows.
        with closing(sqlite3.connect(f"file:{copy}?mode=ro", uri=True)) as con:
            statements = list(con.iterdump())
        out.write_text("\n".join(statements) + "\n", encoding="utf-8", newline="\n")
    return len(statements)


def main() -> int:
    BACKUP_ROOT.mkdir(parents=True, exist_ok=False)
    artifacts: list[dict[str, object]] = []

    def record(name: str, files: int, note: str) -> None:
        path = BACKUP_ROOT / name
        artifacts.append({
            "name": name,
            "bytes": path.stat().st_size,
            "files": files,
            "sha256": sha256(path),
            "note": note,
        })
        print(f"  {name:34} {human(path.stat().st_size):>10}  {files:>6} files")

    print(f"Backup -> {BACKUP_ROOT}\n")

    # 01 frontend working tree
    files = collect(FRONTEND)
    count = zip_paths(BACKUP_ROOT / "01-frontend-src.zip", FRONTEND, files, "guanchewear-landing")
    record("01-frontend-src.zip", count, "React/Vite app: src, public (41 garments), dist, scripts, configs")

    # 02 backend working tree (nested frontend excluded, it has its own archive)
    files = collect(BACKEND, exclude_roots=(FRONTEND,))
    count = zip_paths(BACKUP_ROOT / "03-backend-src.zip", BACKEND, files, "guanchewear-webhook")
    record("03-backend-src.zip", count, "API, references, docs, .env (CONTAINS SECRETS)")

    # 03/04 wordpress theme + site
    files = collect(THEME)
    count = zip_paths(BACKUP_ROOT / "05-wordpress-theme.zip", THEME, files, "guanchewear-landing-theme")
    record("05-wordpress-theme.zip", count, "WP child theme: PHP templates + dist with stacked assets")

    files = collect(SITE)
    count = zip_paths(BACKUP_ROOT / "06-wordpress-site.zip", SITE, files, "wordpress-site")
    record("06-wordpress-site.zip", count, "WP core, WooCommerce, Kadence, uploads, SQLite database")

    # Portable database dump: the .sqlite above is a binary blob, this stays
    # readable and restores without the original engine via sqlite3 or MySQL.
    db = SITE / "wp-content" / "database" / ".ht.sqlite"
    if db.is_file():
        dump = BACKUP_ROOT / "08-wordpress-db-dump.sql"
        statements = dump_sqlite(db, dump)
        record("08-wordpress-db-dump.sql", statements, "WordPress database as portable SQL statements")

    # 04 deploy package
    if DEPLOY_PACKAGE.exists():
        shutil.copy2(DEPLOY_PACKAGE, BACKUP_ROOT / "07-deploy-package.zip")
        record("07-deploy-package.zip", 0, "Ready-to-upload theme ZIP")

    # git bundles
    print()
    repos: list[dict[str, str]] = []
    for name, repo in REPOS.items():
        if not (repo / ".git").exists():
            print(f"  {name:34} skipped (no git repo)")
            continue
        out = BACKUP_ROOT / name
        result = subprocess.run(
            ["git", "-C", str(repo), "bundle", "create", str(out), "--all"],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            print(f"  {name:34} FAILED: {result.stderr.strip()[:120]}")
            continue
        record(name, 0, "full git history, all refs (no remote/credentials)")
        repos.append({
            "repo": str(repo),
            "branch": git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
            "head": git(repo, "rev-parse", "HEAD"),
            "tracked_changes": len([l for l in git(repo, "status", "--porcelain").splitlines() if l[:2].strip() and not l.startswith("??")]),
            "untracked": len([l for l in git(repo, "status", "--porcelain").splitlines() if l.startswith("??")]),
        })

    # checksums + manifest
    sums = BACKUP_ROOT / "SHA256SUMS.txt"
    sums.write_text(
        "".join(f"{a['sha256']}  {a['name']}\n" for a in artifacts),
        encoding="utf-8",
        newline="\n",  # LF: sha256sum -c chokes on the CRLF Windows would add
    )

    total = sum(int(a["bytes"]) for a in artifacts)
    manifest = BACKUP_ROOT / "MANIFEST.md"
    manifest.write_text(build_manifest(artifacts, repos, total), encoding="utf-8", newline="\n")

    (BACKUP_ROOT / "manifest.json").write_text(
        json.dumps({"created": STAMP, "artifacts": artifacts, "repos": repos}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"\nBACKUP_OK dir={BACKUP_ROOT}")
    print(f"  artifacts={len(artifacts)} total={human(total)}")
    return 0


def build_manifest(
    artifacts: list[dict[str, object]],
    repos: list[dict[str, str]],
    total: int,
    stamp: str = STAMP,
) -> str:
    lines = [
        "# Backup GuancheWear",
        "",
        f"- **Creado:** {stamp}",
        f"- **Artefactos:** {len(artifacts)} · **Total:** {human(total)}",
        "",
        "## Contenido",
        "",
        "| Archivo | Tamaño | Archivos | Qué es |",
        "|---|---|---|---|",
    ]
    for a in artifacts:
        lines.append(f"| `{a['name']}` | {human(int(a['bytes']))} | {a['files']} | {a['note']} |")

    lines += ["", "## Estado de los repositorios", "", "| Repo | Rama | Commit | Cambios sin commitear | Sin seguimiento |", "|---|---|---|---|---|"]
    for r in repos:
        lines.append(f"| `{r['repo']}` | `{r['branch']}` | `{r['head'][:10]}` | {r['tracked_changes']} | {r['untracked']} |")

    lines += [
        "",
        "## Cómo restaurar",
        "",
        "### Frontend (React/Vite)",
        "```bash",
        "git clone 02-frontend-git.bundle guanchewear-landing",
        "cd guanchewear-landing && git checkout master",
        "unzip -o ../01-frontend-src.zip -d ..   # recupera cambios sin commitear",
        "npm ci && npm run build",
        "```",
        "",
        "### Backend",
        "```bash",
        "git clone 04-backend-git.bundle guanchewear-webhook",
        "cd guanchewear-webhook && git checkout feat/redesign-premium",
        "unzip -o ../03-backend-src.zip -d ..   # recupera .env y archivos sueltos",
        "npm install",
        "```",
        "",
        "### WordPress",
        "```bash",
        "# El paquete listo para subir es 07-deploy-package.zip",
        "# El tema con sus fuentes está en 05-wordpress-theme.zip",
        "# El sitio completo (con base de datos SQLite) en 06-wordpress-site.zip",
        "```",
        "",
        "> El sitio de WordPress usa SQLite: la base de datos es",
        "> `wp-content/database/.ht.sqlite` y viaja dentro de `06-wordpress-site.zip`.",
        "> Para volver a levantarlo localmente, descomprime `06` y arranca Playground",
        "> apuntando a esa carpeta como `--path`.",
        "",
        "## Avisos",
        "",
        "- `03-backend-src.zip` **contiene `.env` con credenciales** (Stripe, OpenAI, SMTP).",
        "  No compartas este backup ni lo subas a ningún repositorio.",
        "- Las carpetas `.git` **no** se incluyen: su `config` lleva un token de acceso",
        "  embebido en la URL del remoto. El historial completo va en los `.bundle`,",
        "  que no arrastran credenciales.",
        "- `node_modules`, `.vercel` y `__pycache__` se excluyen: se regeneran con",
        "  `npm ci` a partir de `package-lock.json`.",
        "",
        "## Verificar integridad",
        "",
        "```bash",
        "sha256sum -c SHA256SUMS.txt",
        "",
        "# Los bundles necesitan un repositorio de contexto, asi que la prueba",
        "# real es clonar desde ellos (no requiere ningun repo previo):",
        "git clone 02-frontend-git.bundle /tmp/check-fe && git -C /tmp/check-fe log --oneline -1",
        "git clone 04-backend-git.bundle  /tmp/check-be && git -C /tmp/check-be  log --oneline -1",
        "rm -rf /tmp/check-fe /tmp/check-be",
        "```",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    # Regenerate MANIFEST.md for an existing backup without redoing the archives.
    if len(sys.argv) == 3 and sys.argv[1] == "--rewrite-manifest":
        target = Path(sys.argv[2])
        data = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        total = sum(int(a["bytes"]) for a in data["artifacts"])
        out = target / "MANIFEST.md"
        out.write_text(
            build_manifest(data["artifacts"], data["repos"], total, data.get("created", STAMP)),
            encoding="utf-8",
            newline="\n",
        )
        print(f"MANIFEST_REWRITTEN {out}")
        sys.exit(0)
    sys.exit(main())