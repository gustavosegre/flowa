import pytest
from flowa.scheduler.schedule_parser import parse_schedule
from flowa.scheduler.time_utils import generate_times, parse_days

def test_schedule_completo():
    data = {
        "schedule": {
            "days": "All Days",
            "start": "09:00",
            "end": "17:00",
            "interval_minutes": 60,
            "timezone": "America/Sao_Paulo"
        }
    }
    cfg = parse_schedule(data)
    assert cfg.start == "09:00"
    assert cfg.end == "17:00"
    assert cfg.interval_minutes == 60
    assert cfg.timezone == "America/Sao_Paulo"

def test_schedule_ausente_retorna_none():
    assert parse_schedule({}) is None
    assert parse_schedule({"name": "x"}) is None

def test_schedule_defaults():
    cfg = parse_schedule({"schedule": {}})
    assert cfg.timezone == "UTC"
    assert cfg.start == "00:00"
    assert cfg.end == "23:59"
    assert cfg.interval_minutes == 60

def test_gera_horarios_corretos():
    times = generate_times("09:00", "11:00", 60)
    horas = [(t.hour, t.minute) for t in times]
    assert (9, 0) in horas
    assert (10, 0) in horas
    assert (11, 0) in horas

def test_intervalo_30_minutos():
    times = generate_times("08:00", "09:00", 30)
    assert len(times) == 3  # 08:00, 08:30, 09:00

def test_start_igual_end():
    times = generate_times("10:00", "10:00", 15)
    assert len(times) == 1

def test_all_days_sem_espaco():
    result = parse_days("AllDays")
    assert "mon" in result
    assert "sun" in result

def test_all_days_com_espaco():
    result = parse_days("All Days")
    assert "mon" in result
    assert "sun" in result

def test_dias_especificos():
    result = parse_days(["Mon", "Wed", "Fri"])
    assert result == "mon,wed,fri"

def test_dia_invalido():
    with pytest.raises(KeyError):
        parse_days(["Xxx"])
