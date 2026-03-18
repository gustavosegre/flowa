from datetime import datetime, timezone
from flowa.database.db import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def create_pipeline_run(pipeline_name: str, run_dir: str) -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            "INSERT INTO pipeline_runs (pipeline_name, started_at, status, run_dir)"
            " VALUES (?, ?, 'RUNNING', ?)",
            (pipeline_name, _now(), run_dir),
        )
        return cur.lastrowid


def finish_pipeline_run(run_id: int, status: str):
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE pipeline_runs SET finished_at = ?, status = ? WHERE id = ?",
            (_now(), status, run_id),
        )


def get_run_by_id(run_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM pipeline_runs WHERE id = ?", (run_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_pipeline_history(pipeline_name: str = None, limit: int = 20) -> list:
    conn = get_connection()
    if pipeline_name:
        rows = conn.execute(
            "SELECT * FROM pipeline_runs"
            " WHERE pipeline_name = ? ORDER BY started_at DESC LIMIT ?",
            (pipeline_name, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_step_run(pipeline_run_id: int, step_name: str, log_file: str) -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            "INSERT INTO step_runs (pipeline_run_id, step_name, status, started_at, log_file)"
            " VALUES (?, ?, 'RUNNING', ?, ?)",
            (pipeline_run_id, step_name, _now(), log_file),
        )
        return cur.lastrowid

def finish_step_run(step_run_id: int, status: str):
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE step_runs SET finished_at = ?, status = ? WHERE id = ?",
            (_now(), status, step_run_id),
        )

def record_step_skipped(pipeline_run_id: int, step_name: str):
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO step_runs (pipeline_run_id, step_name, status, started_at, finished_at)"
            " VALUES (?, ?, 'SKIPPED', ?, ?)",
            (pipeline_run_id, step_name, _now(), _now()),
        )

def get_step_runs(pipeline_run_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM step_runs WHERE pipeline_run_id = ? ORDER BY started_at",
        (pipeline_run_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
