from pydantic import BaseModel
from typing import List, Optional


class StepInfo(BaseModel):
    name: str
    depends_on: List[str] = []


class PipelineInfo(BaseModel):
    name: str
    file: str
    has_schedule: bool
    workspace: Optional[str] = None
    teams_chat: Optional[str] = None
    steps: List[StepInfo] = []
    last_run_id: Optional[int] = None
    last_status: Optional[str] = None


class TriggerResponse(BaseModel):
    run_id: int
    pipeline_name: str
    status: str
    run_dir: str


class StopResponse(BaseModel):
    stopped: bool
    run_id: int


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


class StepResourceUsage(BaseModel):
    id: int
    step_name: str
    status: str
    started_at: Optional[str]
    finished_at: Optional[str]
    cpu_percent_avg: Optional[float]
    cpu_percent_max: Optional[float]
    mem_mb_avg: Optional[float]
    mem_mb_max: Optional[float]
    pipeline_run_id: int
    pipeline_name: str
