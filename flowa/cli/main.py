import typer
from typing import Optional
from datetime import datetime

from flowa.core.parser import load_pipeline
from flowa.executor.runner import Executor
from flowa.scheduler.scheduler import start_scheduler
from flowa.utils.logger import setup_logging
from flowa.database.db import init_db
from flowa.database.repository import get_pipeline_history, get_step_runs

app = typer.Typer()

STATUS_ICON = {
    "SUCCESS":        "✓",
    "FAILED":         "✗",
    "FAILED (ignored)": "~",
    "SKIPPED":        "-",
    "RUNNING":        "…",
}


def _duration(started_at: str, finished_at: str) -> str:
    if not finished_at:
        return "running"
    try:
        fmt = "%Y-%m-%dT%H:%M:%S.%f%z"
        a = datetime.fromisoformat(started_at)
        b = datetime.fromisoformat(finished_at)
        secs = int((b - a).total_seconds())
        if secs < 60:
            return f"{secs}s"
        return f"{secs // 60}m{secs % 60:02d}s"
    except Exception:
        return ""


@app.callback()
def main():
    setup_logging()


@app.command()
def start():
    start_scheduler()


@app.command()
def run(pipeline_file: str):
    pipeline = load_pipeline(pipeline_file)
    executor = Executor()
    executor.run_pipeline(pipeline)


@app.command()
def history(
    pipeline_name: Optional[str] = typer.Argument(None, help="Filter by pipeline name"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max rows to show"),
):
    init_db()
    runs = get_pipeline_history(pipeline_name, limit)

    if not runs:
        msg = f"No runs found"
        if pipeline_name:
            msg += f" for pipeline '{pipeline_name}'"
        typer.echo(msg)
        raise typer.Exit()

    header = f"{'ID':>5}  {'PIPELINE':<25}  {'STATUS':<16}  {'STARTED':^19}  {'DURATION':>8}  {'RUN DIR'}"
    typer.echo(header)
    typer.echo("-" * len(header))

    for r in runs:
        icon = STATUS_ICON.get(r["status"], "?")
        started = r["started_at"][:19].replace("T", " ")
        dur = _duration(r["started_at"], r["finished_at"])
        typer.echo(
            f"{r['id']:>5}  {r['pipeline_name']:<25}  {icon} {r['status']:<14}  {started}  {dur:>8}  {r['run_dir'] or ''}"
        )


@app.command()
def logs(run_id: int = typer.Argument(..., help="Pipeline run ID (from 'flowa history')")):
    init_db()
    steps = get_step_runs(run_id)

    if not steps:
        typer.echo(f"No steps found for run_id={run_id}")
        raise typer.Exit()

    typer.echo(f"\nSteps for run #{run_id}:\n")
    header = f"  {'STEP':<25}  {'STATUS':<16}  {'STARTED':^19}  {'DURATION':>8}  {'LOG'}"
    typer.echo(header)
    typer.echo("  " + "-" * (len(header) - 2))

    for s in steps:
        icon = STATUS_ICON.get(s["status"], "?")
        started = (s["started_at"] or "")[:19].replace("T", " ")
        dur = _duration(s["started_at"] or "", s["finished_at"] or "")
        log = s["log_file"] or ""
        typer.echo(
            f"  {s['step_name']:<25}  {icon} {s['status']:<14}  {started}  {dur:>8}  {log}"
        )


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on file changes"),
):
    import uvicorn
    uvicorn.run("flowa.api.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
