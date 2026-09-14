import json, time, urllib.request, urllib.parse

try:
    from deep_translator import GoogleTranslator
    from langdetect import detect
    _translate_ok = True
except Exception:
    _translate_ok = False


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "LibreriaApp/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())


def _prime_parole(testo, n=4):
    return " ".join(testo.split()[:n])


def _traduci_se_necessario(testo):
    """Traduce in italiano se il testo è in altra lingua."""
    if not testo or len(testo) < 20 or not _translate_ok:
        return testo
    try:
        lingua = detect(testo)
        if lingua == "it":
            return testo
        tradotto = GoogleTranslator(source="auto", target="it").translate(testo)
        return tradotto or testo
    except Exception:
        return testo


# ── GOOGLE BOOKS ───────────────────────────────────────────
def _google(query):
    try:
        enc  = urllib.parse.quote(query)
        data = _fetch(f"https://www.googleapis.com/books/v1/volumes?q={enc}&maxResults=1")
        if not data.get("items"):
            return None
        info = data["items"][0]["volumeInfo"]
        desc = info.get("description", "")
        if len(desc) > 600:
            desc = desc[:597] + "…"
        desc = _traduci_se_necessario(desc)
        isbn = next((x["identifier"]
                     for x in info.get("industryIdentifiers", [])
                     if x["type"] in ("ISBN_13", "ISBN_10")), "")
        autori = info.get("authors", [])
        return {
            "titolo":      info.get("title", ""),
            "autore":      ", ".join(autori),
            "argomento":   ", ".join(info.get("categories", [])),
            "descrizione": desc,
            "anno":        str(info.get("publishedDate", ""))[:4],
            "editore":     info.get("publisher", ""),
            "isbn":        isbn,
        }
    except Exception:
        return None


# ── OPEN LIBRARY ───────────────────────────────────────────
def _openlibrary_desc(ol_key):
    try:
        data = _fetch(f"https://openlibrary.org{ol_key}.json")
        desc = data.get("description", "")
        if isinstance(desc, dict):
            desc = desc.get("value", "")
        desc = str(desc).strip()
        if len(desc) > 600:
            desc = desc[:597] + "…"
        return _traduci_se_necessario(desc)
    except Exception:
        return ""


def _openlibrary(query):
    try:
        enc  = urllib.parse.quote(query)
        data = _fetch(
            f"https://openlibrary.org/search.json?q={enc}&limit=1"
            f"&fields=title,author_name,first_publish_year,publisher,subject,isbn,key"
        )
        docs = data.get("docs", [])
        if not docs:
            return None
        d     = docs[0]
        isbns = d.get("isbn") or []
        isbn  = next((x for x in isbns if len(x) == 13), isbns[0] if isbns else "")
        desc  = ""
        if d.get("key"):
            desc = _openlibrary_desc(d["key"])
        return {
            "titolo":      d.get("title", ""),
            "autore":      ", ".join(d.get("author_name", [])),
            "argomento":   ", ".join((d.get("subject") or [])[:4]),
            "descrizione": desc,
            "anno":        str(d.get("first_publish_year", "")),
            "editore":     (d.get("publisher") or [""])[0],
            "isbn":        isbn,
        }
    except Exception:
        return None


# ── LOOKUP ESPANSO (5 tentativi) ───────────────────────────
def lookup_espanso(autore, titolo):
    breve = _prime_parole(titolo, 4)
    tentativi = [
        (_google,      f"{autore} {titolo}".strip(), "Google"),
        (_google,      titolo,                        "Google"),
        (_google,      breve,                         "Google"),
        (_openlibrary, f"{autore} {titolo}".strip(), "Open Library"),
        (_openlibrary, titolo,                        "Open Library"),
    ]

    risultato = None
    label_ok  = ""

    for fn, query, label in tentativi:
        if not query.strip():
            continue
        r = fn(query)
        if r:
            risultato = r
            label_ok  = label
            break
        time.sleep(0.15)

    if risultato is None:
        return None, ""

    # Se descrizione vuota prova fonte alternativa
    if not risultato.get("descrizione"):
        query_desc = f"{autore} {titolo}".strip()
        fn2 = _openlibrary if "Google" in label_ok else _google
        r2  = fn2(query_desc)
        if r2 and r2.get("descrizione"):
            risultato["descrizione"] = r2["descrizione"]

    return risultato, label_ok


# ── LOOKUP SINGOLO (form manuale) ──────────────────────────
def lookup_singolo(query):
    """Ricerca per un singolo libro — restituisce tutti i campi inclusi titolo e autore."""
    r = _google(query)
    if r:
        return r, "Google Books"
    r = _openlibrary(query)
    if r:
        return r, "Open Library"
    return None, ""
