import pytest
import os
import shutil
from flowa.core.pipeline import Pipeline, Step
from flowa.executor.runner import Executor

@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOWA_DB_PATH", str(tmp_path / "test.db"))

@pytest.fixture(autouse=True)
def limpa_logs():
    yield
    if os.path.exists("logs/test_exec"):
        shutil.rmtree("logs/test_exec")


def make_pipeline(*steps):
    return Pipeline(name="test_exec", steps=list(steps))


def test_step_com_sucesso(tmp_path):
    step = Step(name="ok", run="echo sucesso")
    executor = Executor()
    executor.run_step(step, str(tmp_path))
    log = tmp_path / "ok.log"
    assert log.exists()
    assert "sucesso" in log.read_text()

def test_step_com_falha(tmp_path):
    step = Step(name="falha", run="exit 1")
    executor = Executor()
    with pytest.raises(Exception, match="exited with code"):
        executor.run_step(step, str(tmp_path))

def test_pipeline_completa():
    pipeline = make_pipeline(
        Step(name="passo1", run="echo passo1"),
        Step(name="passo2", run="echo passo2", depends_on=["passo1"]),
    )
    results = Executor().run_pipeline(pipeline)
    assert results["passo1"] == "SUCCESS"
    assert results["passo2"] == "SUCCESS"


def test_status_failed_na_saida():
    pipeline = make_pipeline(Step(name="quebra", run="exit 2"))
    results = Executor().run_pipeline(pipeline)
    assert results["quebra"] == "FAILED"

def test_retry_esgotado_marca_failed():
    pipeline = make_pipeline(
        Step(name="sempre_falha", run="exit 1", retries=2)
    )
    results = Executor().run_pipeline(pipeline)
    assert results["sempre_falha"] == "FAILED"


def test_retry_sucesso_na_segunda_tentativa(tmp_path):
    counter = tmp_path / "count.txt"
    counter.write_text("0")
    script = tmp_path / "flaky.sh"
    script.write_text(
        f"#!/bin/bash\n"
        f"c=$(cat {counter})\n"
        f"echo $((c+1)) > {counter}\n"
        f"if [ $c -lt 1 ]; then exit 1; fi\n"
    )
    script.chmod(0o755)

    step = Step(name="flaky", run=f"bash {script}", retries=2)
    executor = Executor()
    executor.run_step(step, str(tmp_path))
    assert counter.read_text().strip() == "2"

def test_timeout_levanta_excecao(tmp_path):
    step = Step(name="lento", run="sleep 10", timeout_seconds=1)
    executor = Executor()
    with pytest.raises(Exception, match="timed out"):
        executor.run_step(step, str(tmp_path))

def test_continue_on_error_pipeline_nao_para():
    pipeline = make_pipeline(
        Step(name="falha_ok", run="exit 1", continue_on_error=True),
        Step(name="continua",  run="echo ok", depends_on=["falha_ok"]),
    )
    results = Executor().run_pipeline(pipeline)
    assert results["falha_ok"] == "FAILED (ignored)"
    assert results["continua"] == "SUCCESS"

def test_sem_continue_on_error_skip_dependentes():
    pipeline = make_pipeline(
        Step(name="falha",     run="exit 1"),
        Step(name="dependente", run="echo ok", depends_on=["falha"]),
    )
    results = Executor().run_pipeline(pipeline)
    assert results["falha"] == "FAILED"
    assert results["dependente"] == "SKIPPED"

def test_steps_independentes_todos_executam():
    pipeline = Pipeline(
        name="test_exec",
        steps=[
            Step(name="a", run="echo a"),
            Step(name="b", run="echo b"),
            Step(name="c", run="echo c"),
        ],
        max_parallel=3,
    )
    results = Executor().run_pipeline(pipeline)
    assert all(v == "SUCCESS" for v in results.values())

def test_paralelo_respeita_dependencias():
    pipeline = Pipeline(
        name="test_exec",
        steps=[
            Step(name="base",   run="echo base"),
            Step(name="filho1", run="echo filho1", depends_on=["base"]),
            Step(name="filho2", run="echo filho2", depends_on=["base"]),
            Step(name="neto",   run="echo neto",   depends_on=["filho1", "filho2"]),
        ],
        max_parallel=4,
    )
    results = Executor().run_pipeline(pipeline)
    assert all(v == "SUCCESS" for v in results.values())
