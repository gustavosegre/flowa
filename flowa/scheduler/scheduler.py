import os
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from flowa.scheduler.time_utils import generate_times, parse_days
from flowa.core.parser import load_pipeline
from flowa.executor.runner import Executor

logger = logging.getLogger(__name__)

scheduler = BlockingScheduler()

PIPELINES_DIR = os.getenv("FLOWA_PIPELINES_DIR", "pipelines")


def register_pipeline(pipeline, executor):
    if pipeline.schedule is None:
        logger.warning(
            f"[pipeline:{pipeline.name}] no schedule defined, skipping registration"
        )
        return

    schedule = pipeline.schedule

    times = generate_times(schedule.start, schedule.end, schedule.interval_minutes)
    days = parse_days(schedule.days)

    for t in times:
        scheduler.add_job(
            executor.run_pipeline,
            trigger="cron",
            day_of_week=days,
            hour=t.hour,
            minute=t.minute,
            args=[pipeline],
            max_instances=3,
        )

    logger.info(
        f"[pipeline:{pipeline.name}] registered {len(times)} cron job(s)"
        f" | days={days} | {schedule.start}-{schedule.end}"
        f" every {schedule.interval_minutes}min"
    )


def start_scheduler():
    executor = Executor()

    if not os.path.isdir(PIPELINES_DIR):
        logger.error(f"Pipelines directory not found: '{PIPELINES_DIR}'")
        logger.error("Set FLOWA_PIPELINES_DIR or run from the project root.")
        return

    yaml_files = [f for f in os.listdir(PIPELINES_DIR) if f.endswith(".yaml")]

    if not yaml_files:
        logger.warning(f"No .yaml files found in '{PIPELINES_DIR}'")
        return

    for file in yaml_files:
        path = os.path.join(PIPELINES_DIR, file)
        try:
            pipeline = load_pipeline(path)
            register_pipeline(pipeline, executor)
        except Exception as e:
            logger.error(f"Failed to load pipeline '{file}': {e}")

    logger.info("Flowa scheduler started")
    scheduler.start()
