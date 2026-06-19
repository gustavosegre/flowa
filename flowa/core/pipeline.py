from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Step:
    name: str
    run: str
    depends_on: List[str] = field(default_factory=list)
    retries: int = 0
    continue_on_error: bool = False
    timeout_seconds: Optional[int] = None
    working_dir: Optional[str] = None
    use_uv: bool = False


@dataclass
class Pipeline:
    name: str
    steps: List[Step]
    schedule: Optional[object] = None
    max_parallel: int = 4
    workspace: Optional[str] = None
    teams_chat: Optional[str] = None
    use_uv: bool = False
