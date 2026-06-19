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
- **REST API** — trigger, stop and query pipelines programmatically
- **Web UI** — built-in dashboard to manage and monitor pipelines
- **Script support** — run `.py`, `.sh` and `.bat` files natively
- **Working directory** — set per-step `working_dir` for scripts that rely on relative paths
- **Workspaces** — group pipelines by team or domain directly in the YAML
- **Microsoft Teams notifications** — send success/failure alerts to Teams channels via webhook
- **Stop running pipelines** — cancel an active run from the UI or API
- **Auto-reload** — pipeline changes are picked up automatically without restarting the server

---

## What's New

### v0.1.6
- **Workspaces** — add `workspace: NAME` to any pipeline YAML to group pipelines in the UI under a collapsible section
- **Microsoft Teams integration** — add `teams_chat: <WEBHOOK_URL>` to send Adaptive Card notifications on pipeline success/failure
- **Stop runs** — new `POST /runs/{id}/stop` endpoint and ⏹ stop button in the UI
- **Dependency tree on cards** — pipelines with `depends_on` show a visual tree on the pipeline card
- **Run button fix** — trigger now uses the filename (not the internal `name:`) to locate the pipeline, preventing "not found" errors
- **Encoding fix** — scripts with special characters, emojis or non-ASCII output no longer cause runner errors
- **Exit code detection** — flowa now reliably detects success/failure from the process exit code regardless of whether the script calls `sys.exit()`
- **Auto-reload** — editing a `.yaml` file is picked up on the next scheduled tick without restarting the server

### v0.1.5
- **Dashboard view** — new home page in the web UI with stat cards, 7-day bar chart and success rate donut
- **New `GET /stats` endpoint** — powers the dashboard
- **`.sh` and `.bat` support** — shell/batch scripts auto-detected by extension
- **`working_dir` per step** — run scripts from the correct directory
- **Exit code in log file** — every step log ends with `[flowa] exit code: X`
- **New project structure** — `flowa init` creates `flowa-core/` with `pipelines/`, `logs/` and `data/`

### v0.1.4
- Initial public release

---

## Installation

```bash
pip install flowa-core
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install flowa-core
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
flowa server
# → API + scheduler + web UI at http://127.0.0.1:8000
```

Open `http://127.0.0.1:8000` to see the dashboard, monitor runs, and trigger pipelines.

---

## Pipeline YAML Reference

```yaml
name: my_pipeline          # required — display name
workspace: Finance         # optional — groups pipelines in the UI
max_parallel: 4            # max concurrent steps (default: 4)
use_uv: false              # run python steps via uv (default: false)
teams_chat: https://...    # optional — Teams webhook URL for notifications

schedule:                  # optional
  days: All Days           # All Days | Mon,Tue,Wed,Thu,Fri | ["Mon", "Fri"]
  start: "09:00"
  end:   "18:00"
  interval_minutes: 60

steps:
  - name: step_name           # required, must be unique within the pipeline
    run: command or script    # required — see examples below
    depends_on: other_step    # optional — string or list
    retries: 0                # optional, default 0
    timeout_seconds: 60       # optional, no limit by default
    continue_on_error: false  # optional, default false
    working_dir: /path/to/dir # optional, working directory for this step
    use_uv: false             # optional, overrides pipeline-level use_uv
```

### Workspaces

Add `workspace` to group related pipelines together in the UI. Pipelines with the same workspace are shown under a collapsible dropdown:

```yaml
# finance/etl.yaml
name: ETL Finance
workspace: Finance
steps:
  - name: extract
    run: scripts/extract.py
```

```yaml
# finance/report.yaml
name: Monthly Report
workspace: Finance
steps:
  - name: generate
    run: scripts/report.py
```

Pipelines without a `workspace` field appear ungrouped.

### Teams Notifications

Add `teams_chat` with a Teams incoming webhook URL to receive Adaptive Card notifications when the pipeline finishes:

```yaml
name: ETL Finance
teams_chat: https://your-org.webhook.office.com/webhookb2/...

steps:
  - name: extract
    run: scripts/extract.py
```

Flowa sends a **success** card (✅) or **failure** card (❌) automatically after each run. The card includes the pipeline name, host, timestamp, duration and last error details (if any).

To use different channels per team, just set a different webhook URL in each pipeline YAML.

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

Pipelines with `depends_on` show a dependency tree on their card in the UI.

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
| `POST` | `/runs/{id}/stop` | Stop an active run |
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

**Stop a running pipeline:**

```bash
curl -X POST http://localhost:8000/runs/42/stop
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
