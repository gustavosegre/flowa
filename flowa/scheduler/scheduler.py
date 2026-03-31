import os
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from flowa.scheduler.time_utils import generate_times, parse_days
from flowa.core.parser import load_pipeline
from flowa.executor.runner import Executor

logger = logging.getLogger(__name__)

scheduler = BlockingScheduler()


def _pipelines_dir() -> str:
    return os.getenv("FLOWA_PIPELINES_DIR", "flowa-core/pipelines")


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
    pipelines_dir = _pipelines_dir()
    executor = Executor()

    if not os.path.isdir(pipelines_dir):
        logger.error(f"Pipelines directory not found: '{pipelines_dir}'")
        logger.error("Set FLOWA_PIPELINES_DIR or run from the project root.")
        return

    yaml_files = [f for f in os.listdir(pipelines_dir) if f.endswith(".yaml")]

    if not yaml_files:
        logger.warning(f"No .yaml files found in '{pipelines_dir}'")
        return

    for file in yaml_files:
        path = os.path.join(pipelines_dir, file)
        try:
            pipeline = load_pipeline(path)
            register_pipeline(pipeline, executor)
        except Exception as e:
            logger.error(f"Failed to load pipeline '{file}': {e}")

    logger.info("Flowa scheduler started")
    scheduler.start()


def start_scheduler_background() -> BackgroundScheduler:
    pipelines_dir = _pipelines_dir()
    bg_scheduler = BackgroundScheduler()
    executor = Executor()

    if not os.path.isdir(pipelines_dir):
        logger.error(f"Pipelines directory not found: '{pipelines_dir}'")
        logger.error("Set FLOWA_PIPELINES_DIR or run from the project root.")
        return bg_scheduler

    yaml_files = [f for f in os.listdir(pipelines_dir) if f.endswith(".yaml")]

    if not yaml_files:
        logger.warning(f"No .yaml files found in '{pipelines_dir}'")
    else:
        for file in yaml_files:
            path = os.path.join(pipelines_dir, file)
            try:
                pipeline = load_pipeline(path)
                if pipeline.schedule is None:
                    logger.warning(
                        f"[pipeline:{pipeline.name}] no schedule defined, skipping registration"
                    )
                    continue
                schedule = pipeline.schedule
                times = generate_times(schedule.start, schedule.end, schedule.interval_minutes)
                days = parse_days(schedule.days)
                for t in times:
                    bg_scheduler.add_job(
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
            except Exception as e:
                logger.error(f"Failed to load pipeline '{file}': {e}")

    bg_scheduler.start()
    logger.info("Flowa background scheduler started")
    return bg_scheduler
