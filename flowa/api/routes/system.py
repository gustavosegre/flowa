from typing import List

from fastapi import APIRouter

from flowa.api.schemas import StepResourceUsage
from flowa.database.db import init_db
from flowa.database.repository import get_recent_step_resource_usage
from flowa.utils import resource_monitor

router = APIRouter(prefix="/system", tags=["system"])


@router.get("")
def snapshot():
    """Current hardware snapshot: CPU, memory, disk, network, active scripts."""
    resource_monitor.start_monitor()
    return resource_monitor.current_snapshot()


@router.get("/history")
def history():
    """Rolling history of system snapshots for charting."""
    return resource_monitor.history()


@router.get("/processes", response_model=List[StepResourceUsage])
def processes(limit: int = 30):
    """Resource consumption log for recently finished pipeline steps."""
    init_db()
    return get_recent_step_resource_usage(limit=limit)
