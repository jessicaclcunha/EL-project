import os
import sqlite3
from datetime import datetime

_HERE   = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('VISITORS_DB', os.path.join(_HERE, '..', 'db', 'visitors.db'))
DB_PATH = os.path.normpath(DB_PATH)


def _db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            name          TEXT NOT NULL,
            grammar_hash  TEXT NOT NULL,
            code          TEXT NOT NULL,
            updated_at    TEXT NOT NULL,
            PRIMARY KEY (name, grammar_hash)
        )
    """)
    con.commit()
    return con


def visitor_save(name: str, code: str, grammar_hash: str) -> None:
    con = _db()
    con.execute("""
        INSERT INTO visitors (name, grammar_hash, code, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name, grammar_hash) DO UPDATE SET
            code       = excluded.code,
            updated_at = excluded.updated_at
    """, (name, grammar_hash, code, datetime.now().isoformat()))
    con.commit()
    con.close()


def visitor_list(grammar_hash: str) -> list[str]:
    con  = _db()
    rows = con.execute(
        "SELECT name FROM visitors WHERE grammar_hash = ? ORDER BY updated_at DESC",
        (grammar_hash,)
    ).fetchall()
    con.close()
    names = [r['name'] for r in rows]
    print(f"[DB] list hash={grammar_hash[:16]}… → {names} | db={DB_PATH}")
    return names


def visitor_load(name: str, grammar_hash: str) -> str | None:
    con = _db()
    row = con.execute(
        "SELECT code FROM visitors WHERE name = ? AND grammar_hash = ?",
        (name, grammar_hash)
    ).fetchone()
    con.close()
    return row['code'] if row else None


def visitor_delete(name: str, grammar_hash: str) -> None:
    con = _db()
    cur = con.execute(
        "DELETE FROM visitors WHERE name = ? AND grammar_hash = ?",
        (name, grammar_hash)
    )
    con.commit()
    print(f"[DB] delete '{name}' hash={grammar_hash[:16]}… → {cur.rowcount} row(s) removed | db={DB_PATH}")
    con.close()