"""System hardware monitoring and per-step (script) resource usage tracking.

A background thread samples system-wide CPU/RAM/disk/network usage plus the
resource consumption of every currently running pipeline step, keeping a
short rolling history in memory for the UI's monitoring tab.
"""

import os
import threading
import time
from collections import deque
from datetime import datetime, timezone

import psutil

SAMPLE_INTERVAL_SECONDS = 2
HISTORY_LENGTH = 150  # ~5 minutes at 2s intervals

_history: deque = deque(maxlen=HISTORY_LENGTH)
_history_lock = threading.Lock()

# step_run_id -> {"pid": int, "pipeline_name": str, "step_name": str,
#                  "started_at": str, "cpu_samples": [...], "mem_samples": [...],
#                  "cpu_peak": float, "mem_peak_mb": float}
_tracked: dict = {}
_tracked_lock = threading.Lock()

_started = False
_start_lock = threading.Lock()

FLOWA_PID = os.getpid()

# System-wide process listing (for the monitor tab's "system processes" box).
# pid -> psutil.Process, cached across sampling ticks (see note in
# _sample_tracked_processes about why a fresh Process() per tick reads 0% CPU).
_system_procs_cache: dict = {}
_last_processes: list = []
_last_processes_lock = threading.Lock()


def _disk_path() -> str:
    return os.getenv("FLOWA_DISK_PATH", os.path.abspath(os.sep))


def track_step_start(step_run_id: int, pid: int, pipeline_name: str, step_name: str) -> None:
    """Register a freshly started step's process for resource sampling."""
    try:
        proc = psutil.Process(pid)
        proc.cpu_percent(interval=None)  # prime the internal counter
    except psutil.NoSuchProcess:
        proc = None

    with _tracked_lock:
        _tracked[step_run_id] = {
            "proc": proc,
            "pid": pid,
            "child_procs": {},  # child pid -> psutil.Process, cached across samples
            "pipeline_name": pipeline_name,
            "step_name": step_name,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "cpu_sum": 0.0,
            "cpu_count": 0,
            "cpu_last": 0.0,
            "cpu_peak": 0.0,
            "mem_last_mb": 0.0,
            "mem_peak_mb": 0.0,
        }


def track_step_finish(step_run_id: int) -> dict | None:
    """Unregister a step and return its aggregated resource usage stats."""
    with _tracked_lock:
        info = _tracked.pop(step_run_id, None)
    if not info:
        return None
    avg_cpu = (info["cpu_sum"] / info["cpu_count"]) if info["cpu_count"] else 0.0
    return {
        "cpu_percent_avg": round(avg_cpu, 1),
        "cpu_percent_max": round(info["cpu_peak"], 1),
        "mem_mb_avg": round(info["mem_last_mb"], 1),
        "mem_mb_max": round(info["mem_peak_mb"], 1),
    }


def active_steps() -> list:
    """Live snapshot of resource usage for all currently running steps."""
    out = []
    with _tracked_lock:
        for step_run_id, info in _tracked.items():
            out.append({
                "step_run_id": step_run_id,
                "pipeline_name": info["pipeline_name"],
                "step_name": info["step_name"],
                "pid": info["pid"],
                "started_at": info["started_at"],
                "cpu_percent": round(info["cpu_last"], 1),
                "mem_mb": round(info["mem_last_mb"], 1),
                "cpu_percent_max": round(info["cpu_peak"], 1),
                "mem_mb_max": round(info["mem_peak_mb"], 1),
            })
    return out


def _sample_tracked_processes() -> None:
    with _tracked_lock:
        items = list(_tracked.items())

    for step_run_id, info in items:
        proc = info.get("proc")
        if proc is None:
            continue
        try:
            with proc.oneshot():
                cpu = proc.cpu_percent(interval=None)
                mem_mb = proc.memory_info().rss / (1024 * 1024)
                current_children = proc.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

        # psutil.Process.cpu_percent(interval=None) always returns 0.0 on a
        # process's *first* call (no prior baseline). proc.children() returns
        # brand-new Process objects every call, so child Process instances
        # must be cached and reused across sampling passes or their CPU
        # usage would read as permanently 0.
        child_procs = info["child_procs"]
        current_pids = set()
        for child in current_children:
            current_pids.add(child.pid)
            cached = child_procs.get(child.pid)
            if cached is None:
                try:
                    child.cpu_percent(interval=None)  # prime baseline
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                child_procs[child.pid] = child
                continue  # skip this pass, no baseline yet
            try:
                cpu += cached.cpu_percent(interval=None)
                mem_mb += cached.memory_info().rss / (1024 * 1024)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                child_procs.pop(child.pid, None)

        for dead_pid in set(child_procs) - current_pids:
            child_procs.pop(dead_pid, None)

        with _tracked_lock:
            if step_run_id not in _tracked:
                continue
            entry = _tracked[step_run_id]
            entry["cpu_last"] = cpu
            entry["cpu_sum"] += cpu
            entry["cpu_count"] += 1
            entry["cpu_peak"] = max(entry["cpu_peak"], cpu)
            entry["mem_last_mb"] = mem_mb
            entry["mem_peak_mb"] = max(entry["mem_peak_mb"], mem_mb)


def _sample_system_processes() -> None:
    """Refresh the cached list of every process on the machine, CPU/mem included."""
    current_pids = set(psutil.pids())
    entries = []

    for pid in current_pids:
        proc = _system_procs_cache.get(pid)
        if proc is None:
            try:
                proc = psutil.Process(pid)
                proc.cpu_percent(interval=None)  # prime baseline
                _system_procs_cache[pid] = proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
            continue  # no reading yet on the tick a process first appears

        try:
            with proc.oneshot():
                cpu = proc.cpu_percent(interval=None)
                mem_mb = proc.memory_info().rss / (1024 * 1024)
                name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            _system_procs_cache.pop(pid, None)
            continue

        entries.append({
            "pid": pid,
            "name": name,
            "cpu_percent": round(cpu, 1),
            "mem_mb": round(mem_mb, 1),
        })

    for dead_pid in set(_system_procs_cache) - current_pids:
        _system_procs_cache.pop(dead_pid, None)

    entries.sort(key=lambda e: (e["cpu_percent"], e["mem_mb"]), reverse=True)

    global _last_processes
    with _last_processes_lock:
        _last_processes = entries


def flowa_process() -> dict | None:
    """Resource usage of the flowa server process itself (pinned in the UI)."""
    with _last_processes_lock:
        return next((e for e in _last_processes if e["pid"] == FLOWA_PID), None)


def top_processes(limit: int = 10) -> list:
    """Top system processes by CPU/memory, excluding the flowa process itself."""
    with _last_processes_lock:
        return [e for e in _last_processes if e["pid"] != FLOWA_PID][:limit]


def _take_system_snapshot() -> dict:
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
    vm = psutil.virtual_memory()

    try:
        disk = psutil.disk_usage(_disk_path())
        disk_info = {
            "total_gb": round(disk.total / (1024 ** 3), 1),
            "used_gb": round(disk.used / (1024 ** 3), 1),
            "percent": disk.percent,
        }
    except OSError:
        disk_info = None

    net = psutil.net_io_counters()

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "cpu_percent": cpu_percent,
        "cpu_per_core": cpu_per_core,
        "cpu_count": psutil.cpu_count() or 0,
        "mem": {
            "total_gb": round(vm.total / (1024 ** 3), 2),
            "used_gb": round((vm.total - vm.available) / (1024 ** 3), 2),
            "percent": vm.percent,
        },
        "disk": disk_info,
        "net": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
        },
        "boot_time": psutil.boot_time(),
        "process_count": len(psutil.pids()),
    }


def current_snapshot() -> dict:
    snapshot = _take_system_snapshot()
    snapshot["active_steps"] = active_steps()
    snapshot["flowa_process"] = flowa_process()
    snapshot["top_processes"] = top_processes()
    return snapshot


def history() -> list:
    with _history_lock:
        return list(_history)


def _run_loop() -> None:
    psutil.cpu_percent(interval=None)  # prime the system-wide counter
    while True:
        try:
            snapshot = _take_system_snapshot()
            with _history_lock:
                _history.append(snapshot)
            _sample_tracked_processes()
            _sample_system_processes()
        except Exception:
            pass
        time.sleep(SAMPLE_INTERVAL_SECONDS)


def start_monitor() -> None:
    """Start the background sampling thread (idempotent)."""
    global _started
    with _start_lock:
        if _started:
            return
        thread = threading.Thread(target=_run_loop, name="flowa-resource-monitor", daemon=True)
        thread.start()
        _started = True
