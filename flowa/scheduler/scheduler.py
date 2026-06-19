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


def _job_id(pipeline_name: str, t) -> str:
    return f"{pipeline_name}__{t.hour:02d}{t.minute:02d}"


def _remove_pipeline_jobs(sched, pipeline_name: str) -> None:
    prefix = f"{pipeline_name}__"
    for job in sched.get_jobs():
        if job.id.startswith(prefix):
            job.remove()


def _register_pipeline(sched, pipeline, executor) -> int:
    if pipeline.schedule is None:
        return 0

    schedule = pipeline.schedule
    times = generate_times(schedule.start, schedule.end, schedule.interval_minutes)
    days = parse_days(schedule.days)

    for t in times:
        sched.add_job(
            executor.run_pipeline,
            trigger="cron",
            id=_job_id(pipeline.name, t),
            day_of_week=days,
            hour=t.hour,
            minute=t.minute,
            args=[pipeline],
            max_instances=3,
            replace_existing=True,
        )

    logger.info(
        f"[pipeline:{pipeline.name}] registered {len(times)} cron job(s)"
        f" | days={days} | {schedule.start}-{schedule.end}"
        f" every {schedule.interval_minutes}min"
    )
    return len(times)


def _build_reload_job(sched, executor, pipelines_dir: str, file_mtimes: dict):
    def _reload():
        if not os.path.isdir(pipelines_dir):
            return

        current_files = {f for f in os.listdir(pipelines_dir) if f.endswith(".yaml")}

        # Check for new or changed files
        for filename in current_files:
            path = os.path.join(pipelines_dir, filename)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue

            if file_mtimes.get(filename) == mtime:
                continue

            logger.info(f"[autoupdate] detected change in '{filename}', reloading...")
            try:
                pipeline = load_pipeline(path)
                _remove_pipeline_jobs(sched, pipeline.name)
                _register_pipeline(sched, pipeline, executor)
                file_mtimes[filename] = mtime
                logger.info(f"[autoupdate] '{filename}' reloaded successfully")
            except Exception as e:
                logger.error(f"[autoupdate] failed to reload '{filename}': {e}")

        # Check for removed files
        removed = set(file_mtimes) - current_files
        for filename in removed:
            pipeline_name = filename.replace(".yaml", "")
            logger.info(f"[autoupdate] '{filename}' removed, unregistering jobs...")
            _remove_pipeline_jobs(sched, pipeline_name)
            del file_mtimes[filename]

    return _reload


def register_pipeline(pipeline, executor):
    _register_pipeline(scheduler, pipeline, executor)


def start_scheduler():
    pipelines_dir = _pipelines_dir()
    executor = Executor()

    if not os.path.isdir(pipelines_dir):
        logger.error(f"Pipelines directory not found: '{pipelines_dir}'")
        return

    yaml_files = [f for f in os.listdir(pipelines_dir) if f.endswith(".yaml")]
    file_mtimes: dict = {}

    for file in yaml_files:
        path = os.path.join(pipelines_dir, file)
        try:
            pipeline = load_pipeline(path)
            _register_pipeline(scheduler, pipeline, executor)
            file_mtimes[file] = os.path.getmtime(path)
        except Exception as e:
            logger.error(f"Failed to load pipeline '{file}': {e}")

    reload_fn = _build_reload_job(scheduler, executor, pipelines_dir, file_mtimes)
    scheduler.add_job(reload_fn, trigger="interval", seconds=30, id="__autoupdate__")

    logger.info("Flowa scheduler started")
    scheduler.start()


def start_scheduler_background() -> BackgroundScheduler:
    pipelines_dir = _pipelines_dir()
    bg_scheduler = BackgroundScheduler()
    executor = Executor()
    file_mtimes: dict = {}

    if not os.path.isdir(pipelines_dir):
        logger.error(f"Pipelines directory not found: '{pipelines_dir}'")
        bg_scheduler.start()
        return bg_scheduler

    yaml_files = [f for f in os.listdir(pipelines_dir) if f.endswith(".yaml")]

    for file in yaml_files:
        path = os.path.join(pipelines_dir, file)
        try:
            pipeline = load_pipeline(path)
            if pipeline.schedule is None:
                logger.warning(f"[pipeline:{pipeline.name}] no schedule, skipping")
                continue
            _register_pipeline(bg_scheduler, pipeline, executor)
            file_mtimes[file] = os.path.getmtime(path)
        except Exception as e:
            logger.error(f"Failed to load pipeline '{file}': {e}")

    reload_fn = _build_reload_job(bg_scheduler, executor, pipelines_dir, file_mtimes)
    bg_scheduler.add_job(reload_fn, trigger="interval", seconds=30, id="__autoupdate__")

    bg_scheduler.start()
    logger.info("Flowa background scheduler started (autoupdate every 30s)")
    return bg_scheduler
