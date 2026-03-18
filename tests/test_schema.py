import pytest
from flowa.core.schema import validate_pipeline_data

def test_valido_simples():
    validate_pipeline_data({"name": "p", "steps": [{"name": "s", "run": "echo ok"}]})

def test_sem_name():
    with pytest.raises(ValueError, match="'name'"):
        validate_pipeline_data({"steps": [{"name": "s", "run": "echo ok"}]})

def test_sem_steps():
    with pytest.raises(ValueError, match="'steps'"):
        validate_pipeline_data({"name": "p"})

def test_steps_vazio():
    with pytest.raises(ValueError, match="non-empty"):
        validate_pipeline_data({"name": "p", "steps": []})

def test_step_sem_name():
    with pytest.raises(ValueError, match="'name'"):
        validate_pipeline_data({"name": "p", "steps": [{"run": "echo ok"}]})

def test_step_sem_run():
    with pytest.raises(ValueError, match="'run'"):
        validate_pipeline_data({"name": "p", "steps": [{"name": "s"}]})

def test_nomes_duplicados():
    data = {
        "name": "p",
        "steps": [
            {"name": "s", "run": "echo 1"},
            {"name": "s", "run": "echo 2"},
        ]
    }
    with pytest.raises(ValueError, match="Duplicate"):
        validate_pipeline_data(data)

def test_retries_negativo():
    data = {"name": "p", "steps": [{"name": "s", "run": "echo ok", "retries": -1}]}
    with pytest.raises(ValueError, match="retries"):
        validate_pipeline_data(data)

def test_timeout_zero():
    data = {"name": "p", "steps": [{"name": "s", "run": "echo ok", "timeout_seconds": 0}]}
    with pytest.raises(ValueError, match="timeout_seconds"):
        validate_pipeline_data(data)

def test_timeout_positivo_valido():
    validate_pipeline_data({
        "name": "p",
        "steps": [{"name": "s", "run": "echo ok", "timeout_seconds": 30}]
    })

def test_multiplos_steps_validos():
    data = {
        "name": "p",
        "steps": [
            {"name": "a", "run": "echo a"},
            {"name": "b", "run": "echo b", "retries": 3},
            {"name": "c", "run": "echo c", "depends_on": ["a", "b"]},
        ]
    }
    validate_pipeline_data(data)
