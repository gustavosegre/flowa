import pytest
import tempfile
import os
from flowa.core.parser import load_pipeline

def write_tmp(content):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(content)
    f.close()
    return f.name

def test_carrega_nome():
    path = write_tmp("name: meu_pipeline\nsteps:\n  - name: s\n    run: echo ok\n")
    p = load_pipeline(path)
    os.unlink(path)
    assert p.name == "meu_pipeline"

def test_carrega_steps():
    path = write_tmp("name: p\nsteps:\n  - name: s\n    run: echo ok\n")
    p = load_pipeline(path)
    os.unlink(path)
    assert len(p.steps) == 1
    assert p.steps[0].name == "s"
    assert p.steps[0].run == "echo ok"

def test_depends_on_string_vira_lista():
    yaml = (
        "name: p\nsteps:\n"
        "  - name: a\n    run: echo a\n"
        "  - name: b\n    run: echo b\n    depends_on: a\n"
    )
    path = write_tmp(yaml)
    p = load_pipeline(path)
    os.unlink(path)
    assert p.steps[1].depends_on == ["a"]

def test_depends_on_lista_preservada():
    yaml = (
        "name: p\nsteps:\n"
        "  - name: a\n    run: echo a\n"
        "  - name: b\n    run: echo b\n"
        "  - name: c\n    run: echo c\n    depends_on: [a, b]\n"
    )
    path = write_tmp(yaml)
    p = load_pipeline(path)
    os.unlink(path)
    assert p.steps[2].depends_on == ["a", "b"]

def test_parses_retries():
    yaml = "name: p\nsteps:\n  - name: s\n    run: echo ok\n    retries: 3\n"
    path = write_tmp(yaml)
    p = load_pipeline(path)
    os.unlink(path)
    assert p.steps[0].retries == 3

def test_parses_continue_on_error():
    yaml = "name: p\nsteps:\n  - name: s\n    run: echo ok\n    continue_on_error: true\n"
    path = write_tmp(yaml)
    p = load_pipeline(path)
    os.unlink(path)
    assert p.steps[0].continue_on_error is True

def test_parses_timeout_seconds():
    yaml = "name: p\nsteps:\n  - name: s\n    run: echo ok\n    timeout_seconds: 60\n"
    path = write_tmp(yaml)
    p = load_pipeline(path)
    os.unlink(path)
    assert p.steps[0].timeout_seconds == 60

def test_defaults_dos_novos_campos():
    yaml = "name: p\nsteps:\n  - name: s\n    run: echo ok\n"
    path = write_tmp(yaml)
    p = load_pipeline(path)
    os.unlink(path)
    assert p.steps[0].retries == 0
    assert p.steps[0].continue_on_error is False
    assert p.steps[0].timeout_seconds is None

def test_parses_max_parallel():
    yaml = "name: p\nmax_parallel: 8\nsteps:\n  - name: s\n    run: echo ok\n"
    path = write_tmp(yaml)
    p = load_pipeline(path)
    os.unlink(path)
    assert p.max_parallel == 8

def test_default_max_parallel():
    yaml = "name: p\nsteps:\n  - name: s\n    run: echo ok\n"
    path = write_tmp(yaml)
    p = load_pipeline(path)
    os.unlink(path)
    assert p.max_parallel == 4

def test_schedule_carregado():
    yaml = (
        "name: p\n"
        "schedule:\n  days: All Days\n  start: '08:00'\n  end: '17:00'\n  interval_minutes: 30\n"
        "steps:\n  - name: s\n    run: echo ok\n"
    )
    path = write_tmp(yaml)
    p = load_pipeline(path)
    os.unlink(path)
    assert p.schedule is not None
    assert p.schedule.start == "08:00"
    assert p.schedule.interval_minutes == 30

def test_sem_schedule_retorna_none():
    yaml = "name: p\nsteps:\n  - name: s\n    run: echo ok\n"
    path = write_tmp(yaml)
    p = load_pipeline(path)
    os.unlink(path)
    assert p.schedule is None

def test_arquivo_inexistente():
    with pytest.raises(FileNotFoundError):
        load_pipeline("/tmp/nao_existe_xyz.yaml")

def test_validacao_sem_nome():
    path = write_tmp("steps:\n  - name: s\n    run: echo ok\n")
    with pytest.raises(ValueError, match="'name'"):
        load_pipeline(path)
    os.unlink(path)

def test_validacao_sem_run():
    path = write_tmp("name: p\nsteps:\n  - name: s\n")
    with pytest.raises(ValueError, match="'run'"):
        load_pipeline(path)
    os.unlink(path)

def test_validacao_nome_duplicado():
    yaml = "name: p\nsteps:\n  - name: s\n    run: echo 1\n  - name: s\n    run: echo 2\n"
    path = write_tmp(yaml)
    with pytest.raises(ValueError, match="Duplicate"):
        load_pipeline(path)
    os.unlink(path)

def test_validacao_retries_invalido():
    yaml = "name: p\nsteps:\n  - name: s\n    run: echo ok\n    retries: -1\n"
    path = write_tmp(yaml)
    with pytest.raises(ValueError, match="retries"):
        load_pipeline(path)
    os.unlink(path)
