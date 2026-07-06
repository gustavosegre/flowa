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

def finish_step_run(step_run_id: int, status: str, resource_usage: dict | None = None):
    conn = get_connection()
    with conn:
        if resource_usage:
            conn.execute(
                "UPDATE step_runs SET finished_at = ?, status = ?,"
                " cpu_percent_avg = ?, cpu_percent_max = ?, mem_mb_avg = ?, mem_mb_max = ?"
                " WHERE id = ?",
                (
                    _now(), status,
                    resource_usage.get("cpu_percent_avg"),
                    resource_usage.get("cpu_percent_max"),
                    resource_usage.get("mem_mb_avg"),
                    resource_usage.get("mem_mb_max"),
                    step_run_id,
                ),
            )
        else:
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

def get_stats() -> dict:
    conn = get_connection()

    totals = conn.execute("""
        SELECT
            COUNT(*)                                                         AS total,
            COALESCE(SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END), 0)  AS success,
            COALESCE(SUM(CASE WHEN status='FAILED'  THEN 1 ELSE 0 END), 0)  AS failed,
            COALESCE(SUM(CASE WHEN status='RUNNING' THEN 1 ELSE 0 END), 0)  AS running,
            AVG(CASE WHEN finished_at IS NOT NULL
                THEN (julianday(finished_at) - julianday(started_at)) * 86400
                END)                                                         AS avg_duration_seconds
        FROM pipeline_runs
    """).fetchone()

    daily = conn.execute("""
        SELECT
            date(started_at)                                                 AS day,
            COALESCE(SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END), 0)  AS success,
            COALESCE(SUM(CASE WHEN status='FAILED'  THEN 1 ELSE 0 END), 0)  AS failed
        FROM pipeline_runs
        WHERE date(started_at) >= date('now', '-6 days')
        GROUP BY date(started_at)
        ORDER BY day
    """).fetchall()

    pipelines = conn.execute("""
        SELECT
            pr.pipeline_name,
            COUNT(*)                                                         AS total,
            COALESCE(SUM(CASE WHEN pr.status='SUCCESS' THEN 1 ELSE 0 END), 0) AS success,
            COALESCE(SUM(CASE WHEN pr.status='FAILED'  THEN 1 ELSE 0 END), 0) AS failed,
            AVG(CASE WHEN pr.finished_at IS NOT NULL
                THEN (julianday(pr.finished_at) - julianday(pr.started_at)) * 86400
                END)                                                         AS avg_duration_seconds,
            (SELECT status FROM pipeline_runs
             WHERE pipeline_name = pr.pipeline_name
             ORDER BY started_at DESC LIMIT 1)                               AS last_status
        FROM pipeline_runs pr
        GROUP BY pr.pipeline_name
        ORDER BY total DESC
        LIMIT 20
    """).fetchall()

    conn.close()
    return {
        "totals":    dict(totals),
        "daily":     [dict(r) for r in daily],
        "pipelines": [dict(r) for r in pipelines],
    }


def get_step_runs(pipeline_run_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM step_runs WHERE pipeline_run_id = ? ORDER BY started_at",
        (pipeline_run_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_step_resource_usage(limit: int = 30) -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            sr.id, sr.step_name, sr.status, sr.started_at, sr.finished_at,
            sr.cpu_percent_avg, sr.cpu_percent_max, sr.mem_mb_avg, sr.mem_mb_max,
            pr.id AS pipeline_run_id, pr.pipeline_name
        FROM step_runs sr
        JOIN pipeline_runs pr ON pr.id = sr.pipeline_run_id
        WHERE sr.finished_at IS NOT NULL AND sr.cpu_percent_max IS NOT NULL
        ORDER BY sr.finished_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
