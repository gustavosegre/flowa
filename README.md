<img width="1252" height="336" alt="flowa_banner" src="https://github.com/user-attachments/assets/0ebc7d12-5bf1-4d64-bacb-4e0ab52e215d" />

A lightweight pipeline orchestration tool inspired by Apache Airflow.
Define workflows in YAML, run them from the CLI, schedule them with cron, and monitor everything through a REST API and web UI.

<img width="1180" height="45" alt="flowa_div" src="https://github.com/user-attachments/assets/0be78671-c192-41b7-9f27-510f159b0044" />

## Features

- **DAG-based execution** — topological sort with cycle detection
- **Parallel steps** — independent steps run concurrently via thread pool
- **Retry & timeout** — configurable per step
- **Continue on error** — mark steps as non-blocking for their dependents
- **Cron scheduling** — schedule pipelines by day/time/interval
- **SQLite history** — every run and step is recorded automatically
- **REST API** — trigger pipelines and query history programmatically
- **Web UI** — built-in dashboard to manage and monitor pipelines
- **Script support** — run `.py`, `.sh` and `.bat` files natively
- **Working directory** — set per-step `working_dir` for scripts that rely on relative paths
- **Dashboard** — visual overview with charts, success rate and per-pipeline breakdown

---

## What's New

### v0.1.5
- **Dashboard view** — new home page in the web UI with:
  - Stat cards: total runs, success, failed, avg duration
  - Last 7 days bar chart (SVG, no external libs)
  - Success rate donut chart with dynamic color (green/orange/red)
  - Per-pipeline breakdown table with last run status
- **New `GET /stats` endpoint** — powers the dashboard, returns totals, daily activity and per-pipeline metrics
- **`.sh` and `.bat` support** — use shell/batch scripts directly in the `run` field; flowa auto-prepends the correct interpreter
- **`working_dir` per step** — fix issues where scripts fail when run from a different working directory
- **Exit code in log file** — every step log now ends with `[flowa] exit code: X` so failures are always visible
- **New project structure** — `flowa init` now creates `flowa-core/` with `pipelines/`, `logs/` and `data/` subdirectories

### v0.1.4
- Initial public release
- CLI: `init`, `run`, `start`, `server`, `history`, `logs`
- REST API with FastAPI
- SQLite-backed run history
- APScheduler-based cron scheduling
- Web UI: pipelines and history views

---

## Installation

```bash
pip install flowa-core
```

**Requirements:** Python 3.11+

---

## Getting Started

**Step 1 — Install**

```bash
pip install flowa-core
```

**Step 2 — Initialize your project**

```bash
flowa init
```

This creates the `flowa-core/` directory structure and a ready-to-use `etl.yaml` template:

```
my-project/
└── flowa-core/
    ├── pipelines/
    │   └── etl.yaml    ← edit this to match your scripts
    ├── logs/
    └── data/
```

**Step 3 — Run a pipeline manually**

```bash
flowa run flowa-core/pipelines/etl.yaml
```

**Step 4 — Start the server**

```bash
python -m uvicorn flowa.api.app:app --reload
# or
flowa server
# → API + scheduler + web UI at http://127.0.0.1:8000
```

Open `http://127.0.0.1:8000` to see the dashboard, monitor runs, and trigger pipelines.

---

## Pipeline YAML Reference

```yaml
name: my_pipeline          # required
max_parallel: 4            # max concurrent steps (default: 4)

schedule:                  # optional
  days: All Days           # All Days | Mon,Tue,Wed,Thu,Fri | ["Mon", "Fri"]
  start: "09:00"
  end:   "18:00"
  interval_minutes: 60

steps:
  - name: step_name           # required, must be unique
    run: command or script    # required — see examples below
    depends_on: other_step    # optional — string or list
    retries: 0                # optional, default 0
    timeout_seconds: 60       # optional, no limit by default
    continue_on_error: false  # optional, default false
    working_dir: /path/to/dir # optional, working directory for this step
```

### Running scripts

Flowa detects the file extension and picks the right interpreter automatically:

```yaml
steps:
  - name: extract
    run: scripts/extract.py       # python scripts/extract.py
    working_dir: /my/project

  - name: transform
    run: scripts/transform.sh     # bash scripts/transform.sh
    depends_on: extract

  - name: load
    run: scripts/load.bat         # cmd /c scripts/load.bat  (Windows)
    depends_on: transform
```

### `depends_on`

Accepts a single step name or a list:

```yaml
depends_on: extract
# or
depends_on: [extract, validate]
```

### Step status values

| Status | Description |
|---|---|
| `SUCCESS` | Step completed with exit code 0 |
| `FAILED` | Step failed after all retries |
| `FAILED (ignored)` | Step failed but `continue_on_error: true` |
| `SKIPPED` | Step skipped because a dependency hard-failed |

---

## CLI Reference

```bash
flowa init                          # create flowa-core/ structure and etl.yaml template
flowa run <pipeline.yaml>           # run a pipeline manually
flowa start                         # start only the scheduler (blocking)
flowa server                        # start API + web UI + scheduler
flowa history                       # show recent runs
flowa history <pipeline_name>       # filter by pipeline
flowa logs <run_id>                 # show steps for a run
```

### `flowa server` options

```bash
flowa server --host 0.0.0.0 --port 8080
flowa server --no-scheduler
```

---

## REST API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/pipelines` | List available pipelines |
| `POST` | `/pipelines/{name}/run` | Trigger a pipeline (async) |
| `GET` | `/runs` | Execution history |
| `GET` | `/runs/{id}` | Run detail with steps |
| `GET` | `/runs/{id}/steps/{step}/logs` | Step log content |
| `GET` | `/stats` | Dashboard statistics (totals, daily, per-pipeline) |
| `GET` | `/health` | Health check |

Interactive docs available at `http://localhost:8000/docs`.

<img width="1132" height="739" alt="image" src="https://github.com/user-attachments/assets/0ad298bb-ce4b-441a-ad91-6a3d13e25436" />

<img width="1133" height="248" alt="image" src="https://github.com/user-attachments/assets/fe0e4b50-83f3-427d-bc33-abe2a269ba41" />

<img width="1135" height="477" alt="image" src="https://github.com/user-attachments/assets/858ec210-bd10-4520-b44c-c9fed7d541e4" />

**Trigger a pipeline:**

```bash
curl -X POST http://localhost:8000/pipelines/etl/run
# {"run_id": 42, "status": "RUNNING", ...}
```

**Check run status:**

```bash
curl http://localhost:8000/runs/42
```

---

## Configuration

All settings are controlled via environment variables:

| Variable | Default | Description |
|---|---|---|
| `FLOWA_PIPELINES_DIR` | `flowa-core/pipelines` | Directory scanned by the scheduler |
| `FLOWA_LOGS_DIR` | `flowa-core/logs` | Where step log files are written |
| `FLOWA_DB_PATH` | `flowa-core/data/flowa.db` | SQLite database file path |
| `FLOWA_LOG_LEVEL` | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## Project Layout

A typical project using flowa:

```
my-project/
├── flowa-core/
│   ├── pipelines/
│   │   ├── etl.yaml
│   │   └── reporting.yaml
│   ├── logs/           ← step logs written here automatically
│   └── data/
│       └── flowa.db    ← SQLite database, created automatically
└── scripts/
    ├── extract.py
    ├── transform.sh
    └── load.py
```

---

## License

MIT
