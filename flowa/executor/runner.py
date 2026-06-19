import subprocess
import sys
import os
import time
import logging
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from flowa.database.db import init_db
from flowa.database.repository import (
    create_pipeline_run,
    finish_pipeline_run,
    create_step_run,
    finish_step_run,
    record_step_skipped,
)

logger = logging.getLogger(__name__)

LOGS_DIR = os.getenv("FLOWA_LOGS_DIR", "flowa-core/logs")

# run_id -> {"stop_event": threading.Event, "proc": subprocess.Popen | None}
_active_runs: dict = {}
_runs_lock = threading.Lock()


def _register_run(run_id: int) -> threading.Event:
    stop_event = threading.Event()
    with _runs_lock:
        _active_runs[run_id] = {"stop_event": stop_event, "proc": None}
    return stop_event


def _set_active_proc(run_id: int, proc) -> None:
    with _runs_lock:
        if run_id in _active_runs:
            _active_runs[run_id]["proc"] = proc


def _unregister_run(run_id: int) -> None:
    with _runs_lock:
        _active_runs.pop(run_id, None)


def request_stop(run_id: int) -> bool:
    with _runs_lock:
        if run_id not in _active_runs:
            return False
        info = _active_runs[run_id]
        info["stop_event"].set()
        proc = info.get("proc")
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        return True


def _build_command(run: str, use_uv: bool = False) -> str:
    first_token = run.split()[0]
    ext = os.path.splitext(first_token)[1].lower()

    if ext == ".sh":
        return f"bash {run}"

    if ext == ".bat":
        if sys.platform == "win32":
            return f"cmd /c {run}"
        logger.warning(f"Running .bat file on non-Windows platform: {run}")
        return f"cmd /c {run}"

    if use_uv and (first_token in ("python", "python3") or first_token.endswith("python") or first_token.endswith("python3")):
        return f"uv run {run}"

    return run


def _subprocess_env() -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


class Executor:

    def run_step(self, step, run_dir: str, run_id: int = None, stop_event: threading.Event = None):
        log_file = os.path.join(run_dir, f"{step.name}.log")
        command = _build_command(step.run, use_uv=step.use_uv)
        env = _subprocess_env()

        for attempt in range(1, step.retries + 2):
            logger.info(f"[step:{step.name}] attempt {attempt}/{step.retries + 1}")

            try:
                with open(log_file, "wb") as f:
                    proc = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=f,
                        stderr=f,
                        cwd=step.working_dir or None,
                        env=env,
                    )

                    if run_id is not None:
                        _set_active_proc(run_id, proc)

                    deadline = (time.monotonic() + step.timeout_seconds) if step.timeout_seconds else None

                    while proc.poll() is None:
                        if stop_event and stop_event.is_set():
                            proc.terminate()
                            try:
                                proc.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                proc.kill()
                                proc.wait()
                            raise Exception(f"[step:{step.name}] stopped by user request")

                        if deadline and time.monotonic() > deadline:
                            proc.kill()
                            proc.wait()
                            raise subprocess.TimeoutExpired(command, step.timeout_seconds)

                        time.sleep(0.05)

                with open(log_file, "ab") as f:
                    f.write(f"\n[flowa] exit code: {proc.returncode}\n".encode("utf-8"))

                if proc.returncode != 0:
                    raise Exception(
                        f"[step:{step.name}] exited with code {proc.returncode}"
                    )

                logger.info(f"[step:{step.name}] finished successfully")
                return

            except subprocess.TimeoutExpired:
                msg = f"[step:{step.name}] timed out after {step.timeout_seconds}s (attempt {attempt})"
                logger.warning(msg)
                if attempt > step.retries:
                    raise Exception(msg)

            except Exception as e:
                if "stopped by user request" in str(e):
                    raise
                if attempt <= step.retries:
                    logger.warning(
                        f"[step:{step.name}] attempt {attempt} failed, retrying... ({e})"
                    )
                else:
                    raise

    def _execute_step(self, step, run_dir: str, pipeline_run_id: int, stop_event: threading.Event = None):
        log_file = os.path.join(run_dir, f"{step.name}.log")
        step_run_id = create_step_run(pipeline_run_id, step.name, log_file)
        try:
            self.run_step(step, run_dir, run_id=pipeline_run_id, stop_event=stop_event)
            finish_step_run(step_run_id, "SUCCESS")
        except Exception:
            finish_step_run(step_run_id, "FAILED")
            raise

    def prepare_run(self, pipeline) -> tuple:
        init_db()
        run_dir = self._create_run_dir(pipeline.name)
        run_id = create_pipeline_run(pipeline.name, run_dir)
        return run_id, run_dir

    def run_pipeline(self, pipeline, *, run_id: int = None, run_dir: str = None):
        init_db()
        logger.info(f"[pipeline:{pipeline.name}] starting")

        if run_id is None:
            run_dir = self._create_run_dir(pipeline.name)
            pipeline_run_id = create_pipeline_run(pipeline.name, run_dir)
        else:
            pipeline_run_id = run_id
            if run_dir is None:
                run_dir = self._create_run_dir(pipeline.name)

        logger.info(f"[pipeline:{pipeline.name}] logs at {run_dir} | run_id={pipeline_run_id}")

        stop_event = _register_run(pipeline_run_id)
        started_at = datetime.now()
        overall = "FAILED"

        try:
            completed = set()
            hard_failed = set()
            results = {}
            pending = list(pipeline.steps)

            with ThreadPoolExecutor(max_workers=pipeline.max_parallel) as pool:
                futures = {}

                while pending or futures:
                    if stop_event.is_set():
                        for step in pending:
                            results[step.name] = "SKIPPED"
                            record_step_skipped(pipeline_run_id, step.name)
                        break

                    ready = []
                    still_pending = []

                    for step in pending:
                        if any(dep in hard_failed for dep in step.depends_on):
                            results[step.name] = "SKIPPED"
                            record_step_skipped(pipeline_run_id, step.name)
                            logger.warning(f"[step:{step.name}] skipped (dependency failed)")
                            continue

                        if all(dep in completed for dep in step.depends_on):
                            ready.append(step)
                        else:
                            still_pending.append(step)

                    pending = still_pending

                    for step in ready:
                        logger.info(f"[step:{step.name}] queued for execution")
                        future = pool.submit(
                            self._execute_step, step, run_dir, pipeline_run_id, stop_event
                        )
                        futures[future] = step

                    if not futures:
                        for step in pending:
                            results[step.name] = "SKIPPED"
                            record_step_skipped(pipeline_run_id, step.name)
                            logger.warning(f"[step:{step.name}] skipped (unresolvable dependency)")
                        break

                    done, _ = wait(futures, return_when=FIRST_COMPLETED)

                    for future in done:
                        step = futures.pop(future)
                        try:
                            future.result()
                            completed.add(step.name)
                            results[step.name] = "SUCCESS"
                        except Exception as e:
                            logger.error(f"[step:{step.name}] failed: {e}")
                            if "stopped by user request" in str(e):
                                hard_failed.add(step.name)
                                results[step.name] = "STOPPED"
                            elif step.continue_on_error:
                                completed.add(step.name)
                                results[step.name] = "FAILED (ignored)"
                                logger.warning(f"[step:{step.name}] continue_on_error=true, proceeding")
                            else:
                                hard_failed.add(step.name)
                                results[step.name] = "FAILED"

            if stop_event.is_set():
                overall = "STOPPED"
            else:
                overall = "FAILED" if hard_failed else "SUCCESS"

        finally:
            _unregister_run(pipeline_run_id)
            finish_pipeline_run(pipeline_run_id, overall)
            self._print_summary(pipeline.name, results)

            # Teams notification
            if getattr(pipeline, "teams_chat", None):
                try:
                    from flowa.utils.teams_notifier import notify
                    from flowa.utils.ai_analyzer import analyze_error
                    from flowa.utils.flowa_config import get_ai_config

                    duration = (datetime.now() - started_at).total_seconds()
                    success = overall == "SUCCESS"
                    failed_steps = [s for s, r in results.items() if "FAIL" in r]

                    details = None
                    ai_analysis = None

                    if failed_steps:
                        log_snippets = []
                        for step_name in failed_steps:
                            log_file = os.path.join(run_dir, f"{step_name}.log")
                            if os.path.exists(log_file):
                                try:
                                    with open(log_file, "r", encoding="utf-8", errors="replace") as lf:
                                        content = lf.read()
                                    log_snippets.append(f"[{step_name}]\n{content[-1500:]}")
                                except Exception:
                                    pass
                        details = "\n\n".join(log_snippets) if log_snippets else f"Steps com falha: {', '.join(failed_steps)}"

                        ai_cfg = get_ai_config()
                        if ai_cfg.get("analyze_errors", True) and details:
                            ai_analysis = analyze_error(
                                details=details,
                                context=f"Pipeline '{pipeline.name}' — steps com falha: {', '.join(failed_steps)}",
                                ai_config=ai_cfg,
                            )

                    notify(
                        webhook_url=pipeline.teams_chat,
                        title=f"Pipeline '{pipeline.name}' — {overall}",
                        message=f"Execução finalizada com status {overall}.",
                        success=success,
                        details=details,
                        duration=duration,
                        ai_analysis=ai_analysis,
                    )
                except Exception as e:
                    logger.warning(f"[teams] failed to send notification: {e}")

        return results

    def _print_summary(self, pipeline_name, results):
        logger.info(f"{'---' * 5} Execution Summary {'---' * 5}")
        for step, status in results.items():
            logger.info(f"  {step} -> {status}")
        logger.info(f"[pipeline:{pipeline_name}] completed")

    def _create_run_dir(self, pipeline_name: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(LOGS_DIR, pipeline_name, f"run_{timestamp}")
        os.makedirs(run_dir, exist_ok=True)
        return run_dir
