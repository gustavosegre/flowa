import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List

from flowa.api.schemas import PipelineInfo, TriggerResponse
from flowa.core.parser import load_pipeline
from flowa.executor.runner import Executor

router = APIRouter(prefix="/pipelines", tags=["pipelines"])

PIPELINES_DIR = lambda: os.getenv("FLOWA_PIPELINES_DIR", "flowa_pipelines")


def _list_yaml_files() -> List[str]:
    d = PIPELINES_DIR()
    if not os.path.isdir(d):
        return []
    return [f for f in os.listdir(d) if f.endswith(".yaml")]


@router.get("", response_model=List[PipelineInfo])
def list_pipelines():
    """Lista todos os pipelines disponíveis."""
    result = []
    for filename in _list_yaml_files():
        path = os.path.join(PIPELINES_DIR(), filename)
        try:
            pipeline = load_pipeline(path)
            result.append(PipelineInfo(
                name=pipeline.name,
                file=filename,
                has_schedule=pipeline.schedule is not None,
            ))
        except Exception as e:
            result.append(PipelineInfo(
                name=filename.replace(".yaml", ""),
                file=filename,
                has_schedule=False,
            ))
    return result


@router.post("/{name}/run", response_model=TriggerResponse, status_code=202)
def trigger_pipeline(name: str, background_tasks: BackgroundTasks):
    """Dispara a execução de um pipeline em background. Retorna o run_id imediatamente."""
    path = os.path.join(PIPELINES_DIR(), f"{name}.yaml")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Pipeline '{name}' not found")

    try:
        pipeline = load_pipeline(path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    executor = Executor()
    run_id, run_dir = executor.prepare_run(pipeline)

    background_tasks.add_task(
        executor.run_pipeline, pipeline, run_id=run_id, run_dir=run_dir
    )

    return TriggerResponse(
        run_id=run_id,
        pipeline_name=pipeline.name,
        status="RUNNING",
        run_dir=run_dir,
    )
