import os
import sqlite3
from flask import g

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "grievances.db")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS grievances (
        id TEXT PRIMARY KEY,
        name TEXT,
        contact TEXT,
        department_key TEXT,
        department_label TEXT,
        description TEXT,
        draft_text TEXT,
        drafted_by TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()