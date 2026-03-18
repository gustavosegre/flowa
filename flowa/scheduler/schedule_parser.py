from dataclasses import dataclass
from typing import List, Union

@dataclass
class ScheduleConfig:
    timezone: str
    days: Union[str, List[str]]
    start: str
    end: str
    interval_minutes: int

def parse_schedule(data: dict) -> ScheduleConfig:

    schedule = data.get("schedule")

    if schedule is None:
        return None

    return ScheduleConfig(
        timezone=schedule.get("timezone", "UTC"),
        days=schedule.get("days", "AllDays"),
        start=schedule.get("start", "00:00"),
        end=schedule.get("end", "23:59"),
        interval_minutes=schedule.get("interval_minutes", 60)
    )