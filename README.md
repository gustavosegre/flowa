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


## Installation

```bash
pip install flowa-core
```

**Requirements:** Python 3.11+


## Quick Start

**1. Create a pipeline**

```yaml
# pipelines/etl.yaml
name: etl

steps:
  - name: extract
    run: python scripts/extract.py
    retries: 3
    timeout_seconds: 120

  - name: transform
    run: python scripts/transform.py
    depends_on: extract

  - name: load
    run: python scripts/load.py
    depends_on: transform

  - name: notify
    run: python scripts/notify.py
    depends_on: transform
    continue_on_error: true
```

**2. Run it**

```bash
flowa run pipelines/etl.yaml
```

**3. Open the dashboard**

```bash
flowa serve
# → http://127.0.0.1:8000
```


## Pipeline YAML Reference

```yaml
name: my_pipeline          # required
max_parallel: 4            # max concurrent steps (default: 4)

schedule:                  # optional
  days: All Days           # All Days | Mon,Tue,Wed,Thu,Fri | ["Mon", "Fri"]
  start: "09:00"
  end:   "18:00"
  interval_minutes: 60
  timezone: UTC

steps:
  - name: step_name        # required, must be unique
    run: command to run    # required, executed in shell
    depends_on: other_step # optional — string or list
    retries: 0             # optional, default 0
    timeout_seconds: 60    # optional, no limit by default
    continue_on_error: false  # optional, default false
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
flowa run <pipeline.yaml>       # run a pipeline manually
flowa start                     # start the scheduler
flowa serve                     # start the API + web UI
flowa history                   # show recent runs
flowa history <pipeline_name>   # filter by pipeline
flowa logs <run_id>             # show steps for a run
```

### `flowa serve` options

```bash
flowa serve --host 0.0.0.0 --port 8080 --reload
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
| `GET` | `/health` | Health check |

Interactive docs available at `http://localhost:8000/docs`.

<img width="1132" height="739" alt="image" src="https://github.com/user-attachments/assets/0ad298bb-ce4b-441a-ad91-6a3d13e25436" />

<img width="1133" height="248" alt="image" src="https://github.com/user-attachments/assets/fe0e4b50-83f3-427d-bc33-abe2a269ba41" />

<img width="1135" height="477" alt="image" src="https://github.com/user-attachments/assets/858ec210-bd10-4520-b44c-c9fed7d541e4" />

<img width="1135" height="477" alt="image" src="https://github.com/user-attachments/assets/710b7ac4-dd5f-4d44-ad17-58086ea8546b" />


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
| `FLOWA_PIPELINES_DIR` | `pipelines` | Directory scanned by the scheduler |
| `FLOWA_LOGS_DIR` | `logs` | Where step log files are written |
| `FLOWA_DB_PATH` | `flowa.db` | SQLite database file path |
| `FLOWA_LOG_LEVEL` | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## Project Layout

A typical project using flowa:

```
my-project/
├── pipelines/
│   ├── etl.yaml
│   └── reporting.yaml
├── scripts/
│   ├── extract.py
│   ├── transform.py
│   └── load.py
├── logs/           ← created automatically
└── flowa.db        ← created automatically
```

---

## License

MIT
