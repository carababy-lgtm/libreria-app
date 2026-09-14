import base64, json, sqlite3, urllib.request, urllib.error
import datetime, threading, time, os, tempfile
from config import (DB_PATH, GITHUB_TOKEN, GITHUB_USER,
                    GITHUB_REPO, GITHUB_BRANCH, BACKUP_INTERVAL_HOURS)

BACKUP_FILENAME = "libri.db"
_last_backup    = None


def _api(method, path, payload=None):
    url  = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/{path}"
    data = json.dumps(payload).encode() if payload else None
    req  = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"token {GITHUB_TOKEN}")
    req.add_header("Accept",        "application/vnd.github.v3+json")
    req.add_header("Content-Type",  "application/json")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _get_sha():
    try:
        data = _api("GET", f"contents/{BACKUP_FILENAME}?ref={GITHUB_BRANCH}")
        return data.get("sha", "")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return ""
        raise


def esegui_backup():
    global _last_backup
    if not GITHUB_TOKEN:
        return False, "GITHUB_TOKEN non configurato."
    try:
        # Crea una copia pulita del DB prima di leggerlo
        tmp = tempfile.mktemp(suffix=".db")
        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(tmp)
        src.backup(dst)
        src.close()
        dst.close()

        with open(tmp, "rb") as f:
            contenuto = base64.b64encode(f.read()).decode()
        os.unlink(tmp)

        sha     = _get_sha()
        payload = {
            "message": f"Backup {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            "content": contenuto,
            "branch":  GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha
        _api("PUT", f"contents/{BACKUP_FILENAME}", payload)
        _last_backup = datetime.datetime.utcnow()
        return True, f"Backup completato: {_last_backup.strftime('%d/%m/%Y %H:%M')} UTC"
    except Exception as e:
        return False, f"Errore backup: {e}"


def ripristina_da_github():
    """Scarica libri.db da GitHub, verifica che sia un DB valido, poi sovrascrive."""
    if not GITHUB_TOKEN:
        return False, "GITHUB_TOKEN non configurato."
    try:
        data      = _api("GET", f"contents/{BACKUP_FILENAME}?ref={GITHUB_BRANCH}")
        # GitHub restituisce il contenuto con newline — va rimosso prima del decode
        contenuto_b64 = data["content"].replace("\n", "")
        contenuto = base64.b64decode(contenuto_b64)

        # Verifica che sia un file SQLite valido (inizia con "SQLite format 3")
        if not contenuto.startswith(b"SQLite format 3"):
            return False, "Il file su GitHub non è un DB SQLite valido."

        # Scrivi in un file temporaneo prima di sovrascrivere
        tmp = tempfile.mktemp(suffix=".db")
        with open(tmp, "wb") as f:
            f.write(contenuto)

        # Verifica che il DB temporaneo sia leggibile
        try:
            conn = sqlite3.connect(tmp)
            conn.execute("SELECT COUNT(*) FROM libri")
            conn.close()
        except Exception:
            os.unlink(tmp)
            return False, "Il backup su GitHub è corrotto o incompleto."

        # Tutto ok — sovrascrive il DB live
        os.replace(tmp, DB_PATH)
        return True, "DB ripristinato correttamente da GitHub."

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, "Nessun backup trovato su GitHub."
        return False, f"Errore HTTP {e.code}"
    except Exception as e:
        return False, f"Errore ripristino: {e}"


def stato_backup():
    if _last_backup:
        return _last_backup.strftime("%d/%m/%Y %H:%M") + " UTC"
    return "Mai eseguito in questa sessione"


def _loop_backup():
    intervallo = BACKUP_INTERVAL_HOURS * 3600
    time.sleep(60)
    while True:
        esegui_backup()
        time.sleep(intervallo)


def avvia_backup_automatico():
    t = threading.Thread(target=_loop_backup, daemon=True)
    t.start()
