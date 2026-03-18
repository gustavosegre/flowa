import os
import shutil
import pytest
from fastapi.testclient import TestClient

from flowa.api.app import app
from flowa.database.db import init_db
from flowa.database.repository import create_pipeline_run, finish_pipeline_run, create_step_run, finish_step_run

client = TestClient(app, raise_server_exceptions=True)


@pytest.fixture(autouse=True)
def tmp_env(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOWA_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FLOWA_LOGS_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("FLOWA_PIPELINES_DIR", str(tmp_path / "pipelines"))
    os.makedirs(tmp_path / "pipelines", exist_ok=True)
    init_db()


def write_pipeline(tmp_path, name: str, content: str):
    pipelines_dir = os.path.join(str(tmp_path), "pipelines")
    path = os.path.join(pipelines_dir, f"{name}.yaml")
    with open(path, "w") as f:
        f.write(content)
    return path


YAML_SIMPLES = """\
name: {name}
steps:
  - name: hello
    run: echo hello
"""



def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_list_pipelines_vazio(tmp_path):
    r = client.get("/pipelines")
    assert r.status_code == 200
    assert r.json() == []


def test_list_pipelines_retorna_arquivo(tmp_path):
    write_pipeline(tmp_path, "meu_pipeline", YAML_SIMPLES.format(name="meu_pipeline"))
    r = client.get("/pipelines")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "meu_pipeline"
    assert data[0]["file"] == "meu_pipeline.yaml"
    assert data[0]["has_schedule"] is False


def test_list_pipelines_com_schedule(tmp_path):
    yaml = (
        "name: agendado\n"
        "schedule:\n  days: All Days\n  start: '09:00'\n  end: '17:00'\n  interval_minutes: 60\n"
        "steps:\n  - name: s\n    run: echo ok\n"
    )
    write_pipeline(tmp_path, "agendado", yaml)
    r = client.get("/pipelines")
    assert r.json()[0]["has_schedule"] is True


def test_trigger_pipeline_retorna_202(tmp_path):
    write_pipeline(tmp_path, "pipe", YAML_SIMPLES.format(name="pipe"))
    r = client.post("/pipelines/pipe/run")
    assert r.status_code == 202
    body = r.json()
    assert "run_id" in body
    assert body["pipeline_name"] == "pipe"
    assert body["status"] == "RUNNING"


def test_trigger_pipeline_inexistente():
    r = client.post("/pipelines/nao_existe/run")
    assert r.status_code == 404


def test_trigger_pipeline_yaml_invalido(tmp_path):
    path = os.path.join(str(tmp_path), "pipelines", "ruim.yaml")
    with open(path, "w") as f:
        f.write("steps:\n  - name: s\n    run: echo ok\n") 
    r = client.post("/pipelines/ruim/run")
    assert r.status_code == 422


def test_list_runs_vazio():
    r = client.get("/runs")
    assert r.status_code == 200
    assert r.json() == []


def test_list_runs_retorna_historico():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    finish_pipeline_run(run_id, "SUCCESS")
    r = client.get("/runs")
    data = r.json()
    assert len(data) == 1
    assert data[0]["pipeline_name"] == "p"
    assert data[0]["status"] == "SUCCESS"

def test_list_runs_filtra_por_pipeline():
    r1 = create_pipeline_run("alpha", "logs/alpha/run_1")
    r2 = create_pipeline_run("beta",  "logs/beta/run_1")
    finish_pipeline_run(r1, "SUCCESS")
    finish_pipeline_run(r2, "FAILED")

    r = client.get("/runs?pipeline=alpha")
    data = r.json()
    assert len(data) == 1
    assert data[0]["pipeline_name"] == "alpha"

def test_list_runs_limit():
    for i in range(10):
        create_pipeline_run("p", f"logs/p/run_{i}")
    r = client.get("/runs?limit=3")
    assert len(r.json()) == 3

def test_get_run_com_steps():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    sid = create_step_run(run_id, "step_a", "logs/p/run_1/step_a.log")
    finish_step_run(sid, "SUCCESS")
    finish_pipeline_run(run_id, "SUCCESS")

    r = client.get(f"/runs/{run_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == run_id
    assert body["status"] == "SUCCESS"
    assert len(body["steps"]) == 1
    assert body["steps"][0]["step_name"] == "step_a"


def test_get_run_inexistente():
    r = client.get("/runs/9999")
    assert r.status_code == 404

def test_get_step_logs(tmp_path):
    log_file = str(tmp_path / "step_a.log")
    with open(log_file, "w") as f:
        f.write("linha 1\nlinha 2\n")

    run_id = create_pipeline_run("p", "logs/p/run_1")
    sid = create_step_run(run_id, "step_a", log_file)
    finish_step_run(sid, "SUCCESS")

    r = client.get(f"/runs/{run_id}/steps/step_a/logs")
    assert r.status_code == 200
    body = r.json()
    assert body["step_name"] == "step_a"
    assert "linha 1" in body["content"]
    assert "linha 2" in body["content"]

def test_get_step_logs_step_inexistente():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    r = client.get(f"/runs/{run_id}/steps/nao_existe/logs")
    assert r.status_code == 404

def test_get_step_logs_arquivo_ausente(tmp_path):
    run_id = create_pipeline_run("p", "logs/p/run_1")
    sid = create_step_run(run_id, "step_b", "/tmp/arquivo_que_nao_existe_xyz.log")
    finish_step_run(sid, "FAILED")
    r = client.get(f"/runs/{run_id}/steps/step_b/logs")
    assert r.status_code == 404
