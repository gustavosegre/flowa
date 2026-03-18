import sqlite3
import os

_DDL = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_name TEXT    NOT NULL,
    started_at    TEXT    NOT NULL,
    finished_at   TEXT,
    status        TEXT    NOT NULL DEFAULT 'RUNNING',
    run_dir       TEXT
);

CREATE TABLE IF NOT EXISTS step_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_run_id  INTEGER NOT NULL REFERENCES pipeline_runs(id),
    step_name        TEXT    NOT NULL,
    status           TEXT    NOT NULL DEFAULT 'RUNNING',
    started_at       TEXT,
    finished_at      TEXT,
    log_file         TEXT
);
"""

def get_connection() -> sqlite3.Connection:
    db_path = os.getenv("FLOWA_DB_PATH", "flowa.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_connection()
    with conn:
        conn.executescript(_DDL)
    conn.close()
