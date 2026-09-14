import os

# ── PASSWORD ACCESSO APP ───────────────────────────────────
# Per cambiarla: modifica PASSWORD qui sotto, salva, riavvia l'app su Render
PASSWORD = os.environ.get("APP_PASSWORD", "Pass12345")

# ── GITHUB BACKUP ──────────────────────────────────────────
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER   = os.environ.get("GITHUB_USER", "carababy-lgtm")
GITHUB_REPO   = os.environ.get("GITHUB_REPO", "libreria-db-backup")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")

# ── DATABASE ───────────────────────────────────────────────
import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "libri.db"))

# ── VOCABOLARI ─────────────────────────────────────────────
STANZE  = ["", "STUDIO", "INGRESSO", "BOX", "SOGGIORNO", "CAMERA", "ALTRO"]
RIPIANI = [""] + [f"{r}{n}" for r in "ABCDE" for n in "1234"]

# ── BACKUP AUTOMATICO (ore) ────────────────────────────────
BACKUP_INTERVAL_HOURS = 24
