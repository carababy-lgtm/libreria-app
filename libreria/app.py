#!/usr/bin/env python3
"""
GESTIONE LIBRERIA DI CASA  –  Web App (Flask)
Accesso protetto da password · Backup GitHub · Lookup online con traduzione
"""

import os, base64, threading
from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, send_file, flash)
from werkzeug.utils import secure_filename

from config   import PASSWORD, STANZE, RIPIANI, DB_PATH
from database import (init_db, db_all, db_search, db_get,
                      db_insert, db_update, db_delete, db_stats, gia_presente)
from lookup   import lookup_espanso, lookup_singolo
from backup   import esegui_backup, ripristina_da_github, stato_backup, avvia_backup_automatico

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "libreria-secret-2024")


# ══════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════
def logged_in():
    return session.get("auth") is True


@app.route("/login", methods=["GET", "POST"])
def login():
    errore = ""
    if request.method == "POST":
        if request.form.get("password") == PASSWORD:
            session["auth"] = True
            return redirect(url_for("catalogo"))
        errore = "Password errata."
    return render_template("login.html", errore=errore)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ══════════════════════════════════════════════════════════
#  CATALOGO (pagina principale)
# ══════════════════════════════════════════════════════════
@app.route("/")
def index():
    return redirect(url_for("catalogo"))


@app.route("/catalogo")
def catalogo():
    if not logged_in():
        return redirect(url_for("login"))
    q      = request.args.get("q", "").strip()
    stanza = request.args.get("stanza", "")
    rows   = db_search(q, stanza) if q else db_all()
    if stanza and stanza != "(tutte)" and not q:
        rows = [r for r in rows if r.get("stanza") == stanza]
    stats, dist_stanze = db_stats()
    return render_template("catalogo.html",
                           libri=rows, q=q, stanza=stanza,
                           stanze=STANZE, stats=stats,
                           dist_stanze=dist_stanze,
                           backup_stato=stato_backup())


# ══════════════════════════════════════════════════════════
#  DETTAGLIO LIBRO
# ══════════════════════════════════════════════════════════
@app.route("/libro/<int:book_id>")
def dettaglio(book_id):
    if not logged_in():
        return redirect(url_for("login"))
    libro = db_get(book_id)
    if not libro:
        flash("Libro non trovato.", "warning")
        return redirect(url_for("catalogo"))
    return render_template("dettaglio.html", libro=libro)


# ══════════════════════════════════════════════════════════
#  AGGIUNGI / MODIFICA LIBRO
# ══════════════════════════════════════════════════════════
@app.route("/nuovo", methods=["GET", "POST"])
def nuovo():
    if not logged_in():
        return redirect(url_for("login"))
    if request.method == "POST":
        titolo = request.form.get("titolo", "").strip()
        if not titolo:
            flash("Il titolo è obbligatorio.", "danger")
            return render_template("form_libro.html",
                                   libro={}, stanze=STANZE, ripiani=RIPIANI,
                                   titolo_pag="Nuovo libro")
        data = _form_to_dict(request.form)
        db_insert(data)
        flash(f"«{titolo}» aggiunto.", "success")
        return redirect(url_for("catalogo"))
    return render_template("form_libro.html",
                           libro={}, stanze=STANZE, ripiani=RIPIANI,
                           titolo_pag="Nuovo libro")


@app.route("/modifica/<int:book_id>", methods=["GET", "POST"])
def modifica(book_id):
    if not logged_in():
        return redirect(url_for("login"))
    libro = db_get(book_id)
    if not libro:
        flash("Libro non trovato.", "warning")
        return redirect(url_for("catalogo"))
    if request.method == "POST":
        titolo = request.form.get("titolo", "").strip()
        if not titolo:
            flash("Il titolo è obbligatorio.", "danger")
            return render_template("form_libro.html",
                                   libro=libro, stanze=STANZE, ripiani=RIPIANI,
                                   titolo_pag=f"Modifica [{book_id}]")
        db_update(book_id, _form_to_dict(request.form))
        flash("Modifiche salvate.", "success")
        return redirect(url_for("dettaglio", book_id=book_id))
    return render_template("form_libro.html",
                           libro=libro, stanze=STANZE, ripiani=RIPIANI,
                           titolo_pag=f"Modifica [{book_id}]")


@app.route("/elimina/<int:book_id>", methods=["POST"])
def elimina(book_id):
    if not logged_in():
        return redirect(url_for("login"))
    libro = db_get(book_id)
    db_delete(book_id)
    flash(f"«{libro.get('titolo','')}» eliminato.", "info")
    return redirect(url_for("catalogo"))


def _form_to_dict(form):
    return {
        "titolo":      form.get("titolo", "").strip(),
        "autore":      form.get("autore", "").strip(),
        "argomento":   form.get("argomento", "").strip(),
        "anno":        form.get("anno", "").strip(),
        "editore":     form.get("editore", "").strip(),
        "isbn":        form.get("isbn", "").strip(),
        "descrizione": form.get("descrizione", "").strip(),
        "stanza":      form.get("stanza", "").strip(),
        "ripiano":     form.get("ripiano", "").strip(),
        "note":        form.get("note", "").strip(),
    }


# ══════════════════════════════════════════════════════════
#  LOOKUP ONLINE (AJAX)
# ══════════════════════════════════════════════════════════
@app.route("/api/lookup")
def api_lookup():
    if not logged_in():
        return jsonify({"error": "Non autorizzato"}), 401
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Query vuota"}), 400
    result, source = lookup_singolo(q)
    if result:
        return jsonify({"ok": True, "data": result, "source": source})
    return jsonify({"ok": False, "source": ""})


# ══════════════════════════════════════════════════════════
#  IMPORTAZIONE DA FOTO
# ══════════════════════════════════════════════════════════
@app.route("/importa", methods=["GET", "POST"])
def importa():
    if not logged_in():
        return redirect(url_for("login"))
    if request.method == "GET":
        return render_template("importa.html", stanze=STANZE, ripiani=RIPIANI)

    # POST: ricezione lista libri da importare
    righe   = request.form.get("righe", "").strip().splitlines()
    stanza  = request.form.get("stanza", "").strip()
    ripiano = request.form.get("ripiano", "").strip()

    risultati = []
    for riga in righe:
        riga = riga.strip()
        if not riga:
            continue
        # formato atteso: "Autore | Titolo" oppure solo "Titolo"
        if "|" in riga:
            autore, titolo = [p.strip() for p in riga.split("|", 1)]
        else:
            autore, titolo = "", riga

        if not titolo:
            continue

        if gia_presente(titolo):
            risultati.append({"titolo": titolo, "autore": autore,
                               "stato": "già presente", "classe": "warning"})
            continue

        extra, source = lookup_espanso(autore, titolo)
        data = {
            "titolo":      titolo,
            "autore":      autore,
            "argomento":   extra.get("argomento", "") if extra else "",
            "descrizione": extra.get("descrizione", "") if extra else "",
            "anno":        extra.get("anno", "") if extra else "",
            "editore":     extra.get("editore", "") if extra else "",
            "isbn":        extra.get("isbn", "") if extra else "",
            "stanza":      stanza,
            "ripiano":     ripiano,
            "note":        "posizione da confermare" if not stanza else "",
        }
        db_insert(data)
        stato  = f"importato ({source})" if extra else "importato (senza dati online)"
        classe = "success" if extra else "warning"
        risultati.append({"titolo": titolo, "autore": autore,
                           "stato": stato, "classe": classe})

    return render_template("importa.html", stanze=STANZE, ripiani=RIPIANI,
                           risultati=risultati)


# ══════════════════════════════════════════════════════════
#  BACKUP
# ══════════════════════════════════════════════════════════
@app.route("/backup/esegui", methods=["POST"])
def backup_esegui():
    if not logged_in():
        return redirect(url_for("login"))
    ok, msg = esegui_backup()
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("catalogo"))


@app.route("/backup/scarica")
def backup_scarica():
    if not logged_in():
        return redirect(url_for("login"))
    return send_file(DB_PATH, as_attachment=True, download_name="libri.db")


@app.route("/backup/ripristina", methods=["POST"])
def backup_ripristina():
    if not logged_in():
        return redirect(url_for("login"))
    # ripristino da file caricato
    f = request.files.get("db_file")
    if f and f.filename.endswith(".db"):
        f.save(DB_PATH)
        flash("DB ripristinato dal file caricato.", "success")
    else:
        ok, msg = ripristina_da_github()
        flash(msg, "success" if ok else "danger")
    return redirect(url_for("catalogo"))


# ══════════════════════════════════════════════════════════
#  AVVIO
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    init_db()
    avvia_backup_automatico()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
