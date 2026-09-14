import base64, json, urllib.request, urllib.error, datetime, threading, time
from config import (DB_PATH, GITHUB_TOKEN, GITHUB_USER,
                    GITHUB_REPO, GITHUB_BRANCH, BACKUP_INTERVAL_HOURS)

BACKUP_FILENAME = "libri.db"
_last_backup    = None   # timestamp ultimo backup


def _api(method, path, payload=None):
    url  = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/{path}"
    data = json.dumps(payload).encode() if payload else None
    req  = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization",  f"token {GITHUB_TOKEN}")
    req.add_header("Accept",         "application/vnd.github.v3+json")
    req.add_header("Content-Type",   "application/json")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _get_sha():
    """Recupera lo SHA del file esistente (necessario per update)."""
    try:
        data = _api("GET", f"contents/{BACKUP_FILENAME}?ref={GITHUB_BRANCH}")
        return data.get("sha", "")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return ""   # file non esiste ancora
        raise


def esegui_backup():
    """Carica libri.db su GitHub. Restituisce (True, messaggio) o (False, errore)."""
    global _last_backup
    if not GITHUB_TOKEN:
        return False, "GITHUB_TOKEN non configurato."
    try:
        with open(DB_PATH, "rb") as f:
            contenuto = base64.b64encode(f.read()).decode()
        sha     = _get_sha()
        payload = {
            "message": f"Backup automatico {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
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
    """Scarica libri.db da GitHub e sovrascrive il DB locale."""
    if not GITHUB_TOKEN:
        return False, "GITHUB_TOKEN non configurato."
    try:
        data     = _api("GET", f"contents/{BACKUP_FILENAME}?ref={GITHUB_BRANCH}")
        contenuto = base64.b64decode(data["content"])
        with open(DB_PATH, "wb") as f:
            f.write(contenuto)
        return True, "DB ripristinato da GitHub."
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


# ── BACKUP AUTOMATICO (thread in background) ───────────────
def _loop_backup():
    intervallo = BACKUP_INTERVAL_HOURS * 3600
    time.sleep(60)   # attendi 1 min all'avvio prima del primo tentativo
    while True:
        esegui_backup()
        time.sleep(intervallo)


def avvia_backup_automatico():
    t = threading.Thread(target=_loop_backup, daemon=True)
    t.start()
