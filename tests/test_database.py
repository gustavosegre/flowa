
import os
import pytest
from flowa.database.db import init_db
from flowa.database.repository import (
    create_pipeline_run,
    finish_pipeline_run,
    create_step_run,
    finish_step_run,
    record_step_skipped,
    get_pipeline_history,
    get_step_runs,
)

@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Cada teste usa um banco isolado em tmp_path."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("FLOWA_DB_PATH", db_file)
    init_db()


def test_create_pipeline_run_retorna_id():
    run_id = create_pipeline_run("meu_pipeline", "logs/meu_pipeline/run_1")
    assert isinstance(run_id, int)
    assert run_id > 0

def test_pipeline_run_status_inicial_running():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    history = get_pipeline_history()
    assert history[0]["status"] == "RUNNING"
    assert history[0]["id"] == run_id

def test_finish_pipeline_run_success():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    finish_pipeline_run(run_id, "SUCCESS")
    history = get_pipeline_history()
    assert history[0]["status"] == "SUCCESS"
    assert history[0]["finished_at"] is not None

def test_finish_pipeline_run_failed():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    finish_pipeline_run(run_id, "FAILED")
    history = get_pipeline_history()
    assert history[0]["status"] == "FAILED"

def test_history_multiplos_pipelines():
    create_pipeline_run("alpha", "logs/alpha/run_1")
    create_pipeline_run("beta",  "logs/beta/run_1")
    create_pipeline_run("alpha", "logs/alpha/run_2")

    all_runs = get_pipeline_history()
    assert len(all_runs) == 3

    alpha_runs = get_pipeline_history("alpha")
    assert len(alpha_runs) == 2
    assert all(r["pipeline_name"] == "alpha" for r in alpha_runs)

def test_history_limit():
    for i in range(10):
        create_pipeline_run("p", f"logs/p/run_{i}")
    runs = get_pipeline_history(limit=3)
    assert len(runs) == 3

def test_history_ordenado_mais_recente_primeiro():
    id1 = create_pipeline_run("p", "logs/p/run_1")
    id2 = create_pipeline_run("p", "logs/p/run_2")
    history = get_pipeline_history()
    assert history[0]["id"] == id2
    assert history[1]["id"] == id1

def test_history_pipeline_inexistente_retorna_vazio():
    runs = get_pipeline_history("nao_existe")
    assert runs == []

def test_create_step_run_retorna_id():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    step_id = create_step_run(run_id, "step_a", "logs/p/run_1/step_a.log")
    assert isinstance(step_id, int)
    assert step_id > 0

def test_step_run_status_inicial_running():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    create_step_run(run_id, "step_a", "logs/p/run_1/step_a.log")
    steps = get_step_runs(run_id)
    assert steps[0]["status"] == "RUNNING"
    assert steps[0]["step_name"] == "step_a"

def test_finish_step_run_success():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    step_id = create_step_run(run_id, "s", "logs/p/run_1/s.log")
    finish_step_run(step_id, "SUCCESS")
    steps = get_step_runs(run_id)
    assert steps[0]["status"] == "SUCCESS"
    assert steps[0]["finished_at"] is not None

def test_finish_step_run_failed():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    step_id = create_step_run(run_id, "s", "logs/p/run_1/s.log")
    finish_step_run(step_id, "FAILED")
    steps = get_step_runs(run_id)
    assert steps[0]["status"] == "FAILED"

def test_record_step_skipped():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    record_step_skipped(run_id, "step_pulado")
    steps = get_step_runs(run_id)
    assert steps[0]["status"] == "SKIPPED"
    assert steps[0]["step_name"] == "step_pulado"
    assert steps[0]["log_file"] is None

def test_multiplos_steps_em_ordem():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    id1 = create_step_run(run_id, "a", "logs/p/run_1/a.log")
    id2 = create_step_run(run_id, "b", "logs/p/run_1/b.log")
    finish_step_run(id1, "SUCCESS")
    finish_step_run(id2, "FAILED")

    steps = get_step_runs(run_id)
    assert len(steps) == 2
    assert steps[0]["step_name"] == "a"
    assert steps[0]["status"] == "SUCCESS"
    assert steps[1]["step_name"] == "b"
    assert steps[1]["status"] == "FAILED"

def test_steps_isolados_por_pipeline_run():
    run1 = create_pipeline_run("p", "logs/p/run_1")
    run2 = create_pipeline_run("p", "logs/p/run_2")
    create_step_run(run1, "s", "logs/p/run_1/s.log")
    create_step_run(run2, "s", "logs/p/run_2/s.log")

    assert len(get_step_runs(run1)) == 1
    assert len(get_step_runs(run2)) == 1

def test_run_sem_steps_retorna_vazio():
    run_id = create_pipeline_run("p", "logs/p/run_1")
    assert get_step_runs(run_id) == []
