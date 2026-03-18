from datetime import datetime, timedelta



def generate_times(start: str, end: str, interval: int):
    start_time = datetime.strptime(start, "%H:%M")
    end_time = datetime.strptime(end, "%H:%M")

    times = []

    current = start_time

    while current <= end_time:
        times.append(current.time())
        current += timedelta(minutes=interval)

    return times


DAY_MAP = {
    "Mon": "mon",
    "Tue": "tue",
    "Wed": "wed",
    "Thu": "thu",
    "Fri": "fri",
    "Sat": "sat",
    "Sun": "sun"
}

def parse_days(days):
    if days in ("AllDays", "All Days"):
        return "mon,tue,wed,thu,fri,sat,sun"

    if isinstance(days, str):
        days = [d.strip() for d in days.split(",")]

    return ",".join([DAY_MAP[d] for d in days])

