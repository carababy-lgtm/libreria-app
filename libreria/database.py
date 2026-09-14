import sqlite3
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # sicuro con accessi multipli
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS libri (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                autore    TEXT DEFAULT '',
                titolo    TEXT NOT NULL,
                argomento TEXT DEFAULT '',
                descrizione TEXT DEFAULT '',
                anno      TEXT DEFAULT '',
                editore   TEXT DEFAULT '',
                isbn      TEXT DEFAULT '',
                stanza    TEXT DEFAULT '',
                ripiano   TEXT DEFAULT '',
                note      TEXT DEFAULT '',
                data_ins  TEXT DEFAULT (date('now'))
            )""")
        conn.commit()


# ── CRUD ───────────────────────────────────────────────────
def db_all():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM libri ORDER BY autore COLLATE NOCASE, titolo COLLATE NOCASE"
        ).fetchall()
    return [dict(r) for r in rows]


def db_search(q, stanza=""):
    like = f"%{q}%"
    sql = """
        SELECT * FROM libri
        WHERE (autore LIKE ? OR titolo LIKE ? OR argomento LIKE ?
               OR descrizione LIKE ? OR anno LIKE ? OR editore LIKE ?
               OR isbn LIKE ? OR stanza LIKE ? OR ripiano LIKE ? OR note LIKE ?)
    """
    params = [like] * 10
    if stanza and stanza != "(tutte)":
        sql += " AND stanza = ?"
        params.append(stanza)
    sql += " ORDER BY autore COLLATE NOCASE, titolo COLLATE NOCASE"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def db_get(book_id):
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM libri WHERE id=?", (book_id,)).fetchone()
    return dict(r) if r else {}


def db_insert(d):
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO libri
                (autore,titolo,argomento,descrizione,anno,editore,isbn,stanza,ripiano,note)
            VALUES
                (:autore,:titolo,:argomento,:descrizione,:anno,:editore,:isbn,:stanza,:ripiano,:note)
        """, d)
        conn.commit()
        return cur.lastrowid


def db_update(book_id, d):
    with get_conn() as conn:
        conn.execute("""
            UPDATE libri SET
                autore=:autore, titolo=:titolo, argomento=:argomento,
                descrizione=:descrizione, anno=:anno, editore=:editore,
                isbn=:isbn, stanza=:stanza, ripiano=:ripiano, note=:note
            WHERE id=:id
        """, {**d, "id": book_id})
        conn.commit()


def db_delete(book_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM libri WHERE id=?", (book_id,))
        conn.commit()


def db_stats():
    with get_conn() as conn:
        r = conn.execute("""
            SELECT
                COUNT(*) tot,
                COUNT(DISTINCT NULLIF(TRIM(autore),''))    autori,
                COUNT(DISTINCT NULLIF(TRIM(argomento),'')) argomenti,
                SUM(CASE WHEN TRIM(stanza)!='' THEN 1 ELSE 0 END) posizionati
            FROM libri
        """).fetchone()
        stanze = conn.execute("""
            SELECT stanza, COUNT(*) n FROM libri
            WHERE TRIM(stanza)!='' GROUP BY stanza ORDER BY stanza
        """).fetchall()
    return dict(r) if r else {}, [dict(s) for s in stanze]


def gia_presente(titolo):
    with get_conn() as conn:
        r = conn.execute(
            "SELECT id FROM libri WHERE titolo LIKE ?",
            (f"%{titolo[:25]}%",)
        ).fetchone()
    return r is not None
