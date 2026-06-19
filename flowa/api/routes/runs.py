import os
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from flowa.api.schemas import (
    PipelineRunSchema,
    PipelineRunDetail,
    StepRunSchema,
    StepLogsResponse,
    StopResponse,
)
from flowa.database.db import init_db
from flowa.database.repository import get_pipeline_history, get_step_runs, get_run_by_id

router = APIRouter(prefix="/runs", tags=["runs"])


def _run_or_404(run_id: int) -> dict:
    run = get_run_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


@router.get("", response_model=List[PipelineRunSchema])
def list_runs(
    pipeline: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    init_db()
    return get_pipeline_history(pipeline_name=pipeline, limit=limit)


@router.get("/{run_id}", response_model=PipelineRunDetail)
def get_run(run_id: int):
    init_db()
    run = _run_or_404(run_id)
    steps = [StepRunSchema(**s) for s in get_step_runs(run_id)]
    return PipelineRunDetail(**run, steps=steps)


@router.post("/{run_id}/stop", response_model=StopResponse)
def stop_run(run_id: int):
    from flowa.executor.runner import request_stop
    _run_or_404(run_id)
    stopped = request_stop(run_id)
    if not stopped:
        raise HTTPException(status_code=409, detail=f"Run {run_id} is not currently active")
    return StopResponse(stopped=True, run_id=run_id)


@router.get("/{run_id}/steps/{step_name}/logs", response_model=StepLogsResponse)
def get_step_logs(run_id: int, step_name: str):
    init_db()
    _run_or_404(run_id)

    steps = get_step_runs(run_id)
    step = next((s for s in steps if s["step_name"] == step_name), None)

    if not step:
        raise HTTPException(
            status_code=404,
            detail=f"Step '{step_name}' not found in run {run_id}",
        )

    log_file = step.get("log_file")
    if not log_file or not os.path.exists(log_file):
        raise HTTPException(status_code=404, detail="Log file not available")

    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    return StepLogsResponse(
        run_id=run_id,
        step_name=step_name,
        log_file=log_file,
        content=content,
    )
