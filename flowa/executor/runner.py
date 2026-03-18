import subprocess
import os
import logging
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

LOGS_DIR = os.getenv("FLOWA_LOGS_DIR", "logs")

class Executor:

    def run_step(self, step, run_dir: str):
        log_file = os.path.join(run_dir, f"{step.name}.log")

        for attempt in range(1, step.retries + 2):
            logger.info(f"[step:{step.name}] attempt {attempt}/{step.retries + 1}")

            try:
                with open(log_file, "w") as f:
                    process = subprocess.run(
                        step.run,
                        shell=True,
                        stdout=f,
                        stderr=f,
                        timeout=step.timeout_seconds,
                    )

                if process.returncode != 0:
                    raise Exception(
                        f"[step:{step.name}] exited with code {process.returncode}"
                    )

                logger.info(f"[step:{step.name}] finished successfully")
                return

            except subprocess.TimeoutExpired:
                msg = f"[step:{step.name}] timed out after {step.timeout_seconds}s (attempt {attempt})"
                logger.warning(msg)
                if attempt > step.retries:
                    raise Exception(msg)

            except Exception as e:
                if attempt <= step.retries:
                    logger.warning(
                        f"[step:{step.name}] attempt {attempt} failed, retrying... ({e})"
                    )
                else:
                    raise

    def _execute_step(self, step, run_dir: str, pipeline_run_id: int):
        log_file = os.path.join(run_dir, f"{step.name}.log")
        step_run_id = create_step_run(pipeline_run_id, step.name, log_file)
        try:
            self.run_step(step, run_dir)
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

        completed = set()
        hard_failed = set()
        results = {}
        pending = list(pipeline.steps)

        with ThreadPoolExecutor(max_workers=pipeline.max_parallel) as pool:
            futures = {}

            while pending or futures:
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
                    future = pool.submit(self._execute_step, step, run_dir, pipeline_run_id)
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
                        if step.continue_on_error:
                            completed.add(step.name)
                            results[step.name] = "FAILED (ignored)"
                            logger.warning(f"[step:{step.name}] continue_on_error=true, proceeding")
                        else:
                            hard_failed.add(step.name)
                            results[step.name] = "FAILED"

        overall = "FAILED" if hard_failed else "SUCCESS"
        finish_pipeline_run(pipeline_run_id, overall)

        self._print_summary(pipeline.name, results)
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
