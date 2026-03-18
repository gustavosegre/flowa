from pydantic import BaseModel
from typing import List, Optional


class PipelineInfo(BaseModel):
    name: str
    file: str
    has_schedule: bool


class TriggerResponse(BaseModel):
    run_id: int
    pipeline_name: str
    status: str
    run_dir: str


class StepRunSchema(BaseModel):
    id: int
    pipeline_run_id: int
    step_name: str
    status: str
    started_at: Optional[str]
    finished_at: Optional[str]
    log_file: Optional[str]


class PipelineRunSchema(BaseModel):
    id: int
    pipeline_name: str
    status: str
    started_at: str
    finished_at: Optional[str]
    run_dir: Optional[str]


class PipelineRunDetail(PipelineRunSchema):
    steps: List[StepRunSchema]


class StepLogsResponse(BaseModel):
    run_id: int
    step_name: str
    log_file: str
    content: str
