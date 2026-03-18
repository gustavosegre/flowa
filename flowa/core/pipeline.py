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


@dataclass
class Pipeline:
    name: str
    steps: List[Step]
    schedule: Optional[object] = None
    max_parallel: int = 4
