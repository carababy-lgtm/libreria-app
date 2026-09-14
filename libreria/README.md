# 📚 Libreria di Casa – Web App

App web per gestire la libreria di casa, accessibile da qualsiasi dispositivo.

## File inclusi

| File | Descrizione |
|---|---|
| `app.py` | Server Flask principale |
| `config.py` | Password e configurazione |
| `database.py` | Gestione SQLite |
| `lookup.py` | Ricerca online + traduzione |
| `backup.py` | Backup automatico su GitHub |
| `requirements.txt` | Dipendenze Python |
| `Procfile` | Avvio su Render |

---

## Funzionalità

- **Catalogo** con ricerca su tutti i campi + filtro per stanza
- **Inserimento manuale** con lookup automatico online (Google Books / Open Library)
- **Importazione da foto**: scrivi i titoli visti in foto, il sistema trova i dati online
- **Descrizioni tradotte** in italiano automaticamente
- **Backup manuale** (download DB) e **automatico** ogni 24 ore su GitHub privato
- **Ripristino** DB da file locale o da GitHub
- Accesso protetto da **password**

---

## Deploy su Render (gratuito)

### 1. Carica il codice su GitHub

Crea un secondo repository **pubblico** chiamato `libreria-app`:

1. Vai su https://github.com/new
2. Nome: `libreria-app`, spunta **Public**, clicca "Create repository"
3. Dal tuo PC, installa Git se non ce l'hai: https://git-scm.com
4. Apri il terminale nella cartella del progetto e lancia:

```bash
git init
git add .
git commit -m "Prima versione"
git branch -M main
git remote add origin https://github.com/carababy-lgtm/libreria-app.git
git push -u origin main
```

### 2. Crea il servizio su Render

1. Vai su https://render.com → "Sign up" con il tuo account GitHub
2. Dashboard → **New** → **Web Service**
3. Connetti il repository `libreria-app`
4. Impostazioni:
   - **Name**: `libreria-casa`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `bash render_start.sh`
5. Clicca **Advanced** → **Add Environment Variable** e aggiungi:

| Chiave | Valore |
|---|---|
| `APP_PASSWORD` | la tua password (es. `Pass12345`) |
| `GITHUB_TOKEN` | il token `ghp_...` che hai creato |
| `GITHUB_USER` | `carababy-lgtm` |
| `GITHUB_REPO` | `libreria-db-backup` |
| `SECRET_KEY` | una stringa casuale (es. `xk92mPqL7nR3`) |

6. Clicca **Create Web Service**
7. Dopo 2-3 minuti l'app è online all'indirizzo `https://libreria-casa.onrender.com`

---

## Come cambiare la password

### Su Render (metodo consigliato):
1. Dashboard Render → il tuo servizio → **Environment**
2. Modifica il valore di `APP_PASSWORD`
3. Clicca **Save Changes** → il servizio si riavvia automaticamente

### In locale (se usi l'app sul tuo PC):
Apri `config.py` e modifica la riga:
```python
PASSWORD = os.environ.get("APP_PASSWORD", "Pass12345")
```
Cambia `"Pass12345"` con la nuova password.

---

## Importazione libri da foto

1. Fai la foto alla libreria
2. Vai su **Importa** nell'app
3. Scrivi i libri che vedi, uno per riga:
   - Formato completo: `Autore | Titolo`
   - Solo titolo: `Titolo`
4. Seleziona la stanza e il ripiano
5. Clicca **Importa**

Il sistema cerca automaticamente su Google Books e Open Library,
traduce le descrizioni in italiano e salta i libri già presenti.

---

## Backup

- **Backup manuale**: pulsante "☁ Backup ora" nella barra del catalogo
- **Backup automatico**: ogni 24 ore, il DB viene caricato su GitHub privato (`libreria-db-backup`)
- **Scarica DB**: pulsante "⬇ Scarica DB" per salvare una copia sul PC
- **Ripristino**: carica un file `.db` dal PC oppure usa "⬆ Ripristina" per recuperare da GitHub

---

## Uso locale (senza Render)

```bash
pip install flask deep-translator langdetect
python app.py
```
Apri http://localhost:5000 nel browser.
