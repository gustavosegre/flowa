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

# Columns added after the initial release; applied via ALTER TABLE since
# sqlite has no "ADD COLUMN IF NOT EXISTS".
_STEP_RUNS_MIGRATIONS = [
    ("cpu_percent_avg", "REAL"),
    ("cpu_percent_max", "REAL"),
    ("mem_mb_avg", "REAL"),
    ("mem_mb_max", "REAL"),
]

def get_connection() -> sqlite3.Connection:
    db_path = os.getenv("FLOWA_DB_PATH", "flowa-core/data/flowa.db")
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass  # WAL not supported on some filesystems (e.g. WSL2 via Windows process)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def _migrate_step_runs(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(step_runs)")}
    for column, col_type in _STEP_RUNS_MIGRATIONS:
        if column not in existing:
            conn.execute(f"ALTER TABLE step_runs ADD COLUMN {column} {col_type}")

def init_db():
    conn = get_connection()
    with conn:
        conn.executescript(_DDL)
        _migrate_step_runs(conn)
    conn.close()
