import os
import typer
from typing import Optional
from datetime import datetime

from flowa.core.parser import load_pipeline
from flowa.executor.runner import Executor
from flowa.scheduler.scheduler import start_scheduler, start_scheduler_background
from flowa.utils.logger import setup_logging
from flowa.database.db import init_db
from flowa.database.repository import get_pipeline_history, get_step_runs

app = typer.Typer()

STATUS_ICON = {
    "SUCCESS":        "✓",
    "FAILED":         "✗",
    "FAILED (ignored)": "~",
    "SKIPPED":        "-",
    "RUNNING":        "…",
}


def _duration(started_at: str, finished_at: str) -> str:
    if not finished_at:
        return "running"
    try:
        fmt = "%Y-%m-%dT%H:%M:%S.%f%z"
        a = datetime.fromisoformat(started_at)
        b = datetime.fromisoformat(finished_at)
        secs = int((b - a).total_seconds())
        if secs < 60:
            return f"{secs}s"
        return f"{secs // 60}m{secs % 60:02d}s"
    except Exception:
        return ""


@app.callback()
def main():
    setup_logging()


TEAMS_CONFIG_TEMPLATE = '''\
# =============================================================================
# flowa-core/teams_config.py
# Personalizacao das notificacoes do Microsoft Teams via Flowa.
# Este arquivo e carregado automaticamente — edite conforme necessario.
# =============================================================================

import socket


# =============================================================================
# IDENTIFICACAO
# =============================================================================

# Nome exibido no cabecalho de todos os cards.
APP_NAME = "FLOWA"

# Identificacao da maquina exibida abaixo do APP_NAME.
# Por padrao usa o hostname do sistema. Voce pode fixar um nome amigavel:
# HOSTNAME = "Servidor Producao"
# HOSTNAME = "ETL-WIN-01"
HOSTNAME = socket.gethostname()


# =============================================================================
# ICONES
# =============================================================================

# Emoji exibido no titulo quando o pipeline conclui com sucesso.
# Exemplos: "✅" "🟢" "🎉" "👍"
ICON_SUCESSO = "✅"

# Emoji exibido no titulo quando o pipeline falha.
# Exemplos: "❌" "🔴" "🚨" "⚠️"
ICON_ERRO = "❌"

# Emoji exibido no titulo da secao de analise da IA.
# Exemplos: "👾" "🤖" "🧠" "💡"
ICON_IA = "👾"


# =============================================================================
# IMAGENS DO CARD
# =============================================================================

# Imagem exibida no canto do card quando o pipeline tem SUCESSO.
# Use uma URL publica acessivel pelo Teams.
# Formatos aceitos: PNG, JPG, GIF (GIFs animados funcionam).
IMG_SUCESSO = (
    "https://i.pinimg.com/originals/d6/71/b5/"
    "d671b57b99533df856544bb3f30fe559.gif"
)

# Imagem exibida no canto do card quando o pipeline FALHA.
IMG_ERRO = (
    "https://ih1.redbubble.net/image.2579899118.1732/"
    "st,small,507x507-pad,600x600,f8f8f8.jpg"
)

# Tamanho da imagem no card.
# Opcoes: "Small" | "Medium" | "Large" | "ExtraLarge" | "Auto" | "Stretch"
IMG_TAMANHO = "Large"

# Estilo da imagem.
# "Default" -> retangular | "Person" -> circular (bom para avatares/logos)
IMG_ESTILO = "Person"


# =============================================================================
# CORES DO CARD
# =============================================================================

# Cor do texto do titulo quando SUCESSO.
# Opcoes: "good" (verde) | "accent" (azul) | "dark" | "light" | "default"
COR_SUCESSO = "good"

# Cor do texto do titulo quando FALHA.
# Opcoes: "attention" (vermelho) | "warning" (laranja) | "dark" | "default"
COR_ERRO = "attention"


# =============================================================================
# FORMATO DE DATA
# =============================================================================

# Formato da data/hora exibida no card.
# Referencia: https://docs.python.org/3/library/datetime.html#strftime-codes
# Exemplos:
#   "%d/%m/%Y %H:%M:%S"  ->  18/06/2025 14:30:00
#   "%Y-%m-%d %H:%M"     ->  2025-06-18 14:30
#   "%d %b %Y %H:%M"     ->  18 Jun 2025 14:30
FORMATO_DATA = "%d/%m/%Y %H:%M:%S"


# =============================================================================
# SECAO DE DETALHES TECNICOS (TRACEBACK / LOG)
# =============================================================================

# Exibir a secao de detalhes tecnicos (log do step com falha) no card?
EXIBIR_DETALHES = True

# Numero maximo de caracteres do log exibidos no card.
# O Teams tem limite de tamanho de payload — recomendado entre 500 e 1500.
MAX_TRACEBACK_CHARS = 700


# =============================================================================
# SECAO DE ANALISE DA IA
# =============================================================================

# Exibir a secao de analise da IA no card quando disponivel?
EXIBIR_ANALISE_IA = True

# Numero maximo de caracteres da resposta da IA exibidos no card.
MAX_IA_CHARS = 1000


# =============================================================================
# REDE / SSL
# =============================================================================

# Timeout em segundos para o envio da notificacao ao Teams.
TEAMS_TIMEOUT = 10

# Verificacao de certificado SSL.
# False -> desativa verificacao (util em redes corporativas com proxy/MITM).
# True  -> verifica certificado (recomendado em ambientes sem proxy).
SSL_VERIFY = False
'''

CONFIG_TEMPLATE = """\
# Flowa global configuration
# Place this file at flowa-core/config.yaml

ai:
  # Provider to use for automatic error analysis in Teams notifications.
  # Options: groq | claude | gemini | openai | none
  provider: none

  # Set to false to disable AI analysis even when a provider is configured.
  analyze_errors: true

  groq:
    api_key: ""
    model: "llama-3.3-70b-versatile"
    max_tokens: 500
    timeout: 30

  claude:
    api_key: ""
    model: "claude-haiku-4-5-20251001"
    max_tokens: 500
    timeout: 30

  gemini:
    api_key: ""
    model: "gemini-1.5-flash"
    max_tokens: 500
    timeout: 30

  openai:
    api_key: ""
    model: "gpt-4o-mini"
    max_tokens: 500
    timeout: 30
"""

ETL_TEMPLATE = """\
name: etl_pipeline

schedule:
  days: All Days
  start: "08:00"
  end: "18:00"
  interval_minutes: 60

max_parallel: 2

steps:

  - name: extract
    run: python scripts/extract.py
    retries: 2
    timeout_seconds: 120

  - name: transform
    run: python scripts/transform.py
    depends_on: extract
    retries: 1
    timeout_seconds: 300

  - name: load
    run: python scripts/load.py
    depends_on: transform
    retries: 2
    timeout_seconds: 120
"""


@app.command()
def init():
    """Initialize a flowa project: create flowa-core/ structure and an ETL template."""
    base_dir = os.path.join(os.getcwd(), "flowa-core")
    pipelines_dir = os.path.join(base_dir, "pipelines")
    logs_dir = os.path.join(base_dir, "logs")
    data_dir = os.path.join(base_dir, "data")

    for path, label in [
        (pipelines_dir, "flowa-core/pipelines"),
        (logs_dir, "flowa-core/logs"),
        (data_dir, "flowa-core/data"),
    ]:
        if not os.path.exists(path):
            os.makedirs(path)
            typer.echo(f"Created {label}/")
        else:
            typer.echo(f"{label}/ already exists, skipping")

    etl_path = os.path.join(pipelines_dir, "etl.yaml")
    if not os.path.exists(etl_path):
        with open(etl_path, "w") as f:
            f.write(ETL_TEMPLATE)
        typer.echo(f"Created template flowa-core/pipelines/etl.yaml")
    else:
        typer.echo(f"flowa-core/pipelines/etl.yaml already exists, skipping")

    config_path = os.path.join(base_dir, "config.yaml")
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            f.write(CONFIG_TEMPLATE)
        typer.echo(f"Created flowa-core/config.yaml")
    else:
        typer.echo(f"flowa-core/config.yaml already exists, skipping")


@app.command(name="teams-init")
def teams_init():
    """Generate flowa-core/teams_config.py with Teams notification presets to customize."""
    base_dir = os.path.join(os.getcwd(), "flowa-core")
    config_path = os.path.join(base_dir, "teams_config.py")

    if not os.path.exists(base_dir):
        typer.echo("flowa-core/ not found. Run 'flowa init' first.")
        raise typer.Exit(1)

    if os.path.exists(config_path):
        typer.echo("flowa-core/teams_config.py already exists, skipping")
        return

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(TEAMS_CONFIG_TEMPLATE)
    typer.echo("Created flowa-core/teams_config.py — edit it to customize your Teams notifications.")


@app.command()
def start():
    start_scheduler()


@app.command()
def run(pipeline_file: str):
    pipeline = load_pipeline(pipeline_file)
    executor = Executor()
    executor.run_pipeline(pipeline)


@app.command()
def history(
    pipeline_name: Optional[str] = typer.Argument(None, help="Filter by pipeline name"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max rows to show"),
):
    init_db()
    runs = get_pipeline_history(pipeline_name, limit)

    if not runs:
        msg = f"No runs found"
        if pipeline_name:
            msg += f" for pipeline '{pipeline_name}'"
        typer.echo(msg)
        raise typer.Exit()

    header = f"{'ID':>5}  {'PIPELINE':<25}  {'STATUS':<16}  {'STARTED':^19}  {'DURATION':>8}  {'RUN DIR'}"
    typer.echo(header)
    typer.echo("-" * len(header))

    for r in runs:
        icon = STATUS_ICON.get(r["status"], "?")
        started = r["started_at"][:19].replace("T", " ")
        dur = _duration(r["started_at"], r["finished_at"])
        typer.echo(
            f"{r['id']:>5}  {r['pipeline_name']:<25}  {icon} {r['status']:<14}  {started}  {dur:>8}  {r['run_dir'] or ''}"
        )


@app.command()
def logs(run_id: int = typer.Argument(..., help="Pipeline run ID (from 'flowa history')")):
    init_db()
    steps = get_step_runs(run_id)

    if not steps:
        typer.echo(f"No steps found for run_id={run_id}")
        raise typer.Exit()

    typer.echo(f"\nSteps for run #{run_id}:\n")
    header = f"  {'STEP':<25}  {'STATUS':<16}  {'STARTED':^19}  {'DURATION':>8}  {'LOG'}"
    typer.echo(header)
    typer.echo("  " + "-" * (len(header) - 2))

    for s in steps:
        icon = STATUS_ICON.get(s["status"], "?")
        started = (s["started_at"] or "")[:19].replace("T", " ")
        dur = _duration(s["started_at"] or "", s["finished_at"] or "")
        log = s["log_file"] or ""
        typer.echo(
            f"  {s['step_name']:<25}  {icon} {s['status']:<14}  {started}  {dur:>8}  {log}"
        )


@app.command()
def server(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
    no_scheduler: bool = typer.Option(False, "--no-scheduler", help="Disable the background scheduler"),
):
    import uvicorn
    if not no_scheduler:
        start_scheduler_background()
    uvicorn.run("flowa.api.app:app", host=host, port=port)


if __name__ == "__main__":
    app()
