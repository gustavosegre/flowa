import os
import socket
import logging
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Defaults — overridden by flowa-core/teams_config.py if present
HOSTNAME = socket.gethostname()
SSL_VERIFY = False
APP_NAME = "FLOWA"
ICON_SUCESSO = "✅"
ICON_ERRO = "❌"
ICON_IA = "👾"
IMG_SUCESSO = (
    "https://i.pinimg.com/originals/d6/71/b5/"
    "d671b57b99533df856544bb3f30fe559.gif"
)
IMG_ERRO = (
    "https://ih1.redbubble.net/image.2579899118.1732/"
    "st,small,507x507-pad,600x600,f8f8f8.jpg"
)
IMG_TAMANHO = "Large"
IMG_ESTILO = "Person"
COR_SUCESSO = "good"
COR_ERRO = "attention"
FORMATO_DATA = "%d/%m/%Y %H:%M:%S"
EXIBIR_DETALHES = True
EXIBIR_ANALISE_IA = True
MAX_TRACEBACK_CHARS = 700
MAX_IA_CHARS = 1000
TEAMS_TIMEOUT = 10


def _load_user_config():
    global HOSTNAME, SSL_VERIFY, APP_NAME, ICON_SUCESSO, ICON_ERRO, ICON_IA
    global IMG_SUCESSO, IMG_ERRO, IMG_TAMANHO, IMG_ESTILO, COR_SUCESSO, COR_ERRO
    global FORMATO_DATA, EXIBIR_DETALHES, EXIBIR_ANALISE_IA, MAX_TRACEBACK_CHARS
    global MAX_IA_CHARS, TEAMS_TIMEOUT

    config_path = os.path.normpath(os.path.join(
        os.getenv("FLOWA_PIPELINES_DIR", "flowa-core/pipelines"),
        "..", "teams_config.py",
    ))
    if not os.path.exists(config_path):
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("teams_config", config_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        HOSTNAME            = getattr(mod, "HOSTNAME",            HOSTNAME)
        SSL_VERIFY          = getattr(mod, "SSL_VERIFY",          SSL_VERIFY)
        APP_NAME            = getattr(mod, "APP_NAME",            APP_NAME)
        ICON_SUCESSO        = getattr(mod, "ICON_SUCESSO",        ICON_SUCESSO)
        ICON_ERRO           = getattr(mod, "ICON_ERRO",           ICON_ERRO)
        ICON_IA             = getattr(mod, "ICON_IA",             ICON_IA)
        IMG_SUCESSO         = getattr(mod, "IMG_SUCESSO",         IMG_SUCESSO)
        IMG_ERRO            = getattr(mod, "IMG_ERRO",            IMG_ERRO)
        IMG_TAMANHO         = getattr(mod, "IMG_TAMANHO",         IMG_TAMANHO)
        IMG_ESTILO          = getattr(mod, "IMG_ESTILO",          IMG_ESTILO)
        COR_SUCESSO         = getattr(mod, "COR_SUCESSO",         COR_SUCESSO)
        COR_ERRO            = getattr(mod, "COR_ERRO",            COR_ERRO)
        FORMATO_DATA        = getattr(mod, "FORMATO_DATA",        FORMATO_DATA)
        EXIBIR_DETALHES     = getattr(mod, "EXIBIR_DETALHES",     EXIBIR_DETALHES)
        EXIBIR_ANALISE_IA   = getattr(mod, "EXIBIR_ANALISE_IA",   EXIBIR_ANALISE_IA)
        MAX_TRACEBACK_CHARS = getattr(mod, "MAX_TRACEBACK_CHARS", MAX_TRACEBACK_CHARS)
        MAX_IA_CHARS        = getattr(mod, "MAX_IA_CHARS",        MAX_IA_CHARS)
        TEAMS_TIMEOUT       = getattr(mod, "TEAMS_TIMEOUT",       TEAMS_TIMEOUT)

        logger.info("[teams] loaded teams_config.py")
    except Exception as e:
        logger.warning(f"[teams] failed to load teams_config.py: {e}")


_load_user_config()


def _clean(text: str) -> str:
    if not text:
        return ""
    return (
        str(text)
        .replace("```", "")
        .replace("**", "")
        .replace("__", "")
        .replace("\r", "")
        .replace("\t", "    ")
        .strip()
    )


def _build_card(
    title: str,
    message: str,
    success: bool = True,
    details: str = None,
    duration: float = None,
    ai_analysis: str = None,
) -> dict:
    color = COR_SUCESSO if success else COR_ERRO
    icon = ICON_SUCESSO if success else ICON_ERRO
    image = IMG_SUCESSO if success else IMG_ERRO

    body = [
        {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": "auto",
                    "items": [{"type": "Image", "url": image, "size": IMG_TAMANHO, "style": IMG_ESTILO}],
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {"type": "TextBlock", "text": APP_NAME, "weight": "Bolder", "size": "Medium", "wrap": True},
                        {"type": "TextBlock", "text": HOSTNAME, "isSubtle": True, "spacing": "None", "wrap": True},
                    ],
                },
            ],
        },
        {"type": "TextBlock", "text": f"{icon} {_clean(title)}", "weight": "Bolder", "size": "Large", "color": color, "wrap": True},
        {"type": "TextBlock", "text": _clean(message), "wrap": True},
    ]

    facts = [{"title": "Data:", "value": datetime.now().strftime(FORMATO_DATA)}]
    if duration is not None:
        facts.append({"title": "Duração:", "value": f"{duration:.2f}s"})
    body.append({"type": "FactSet", "facts": facts})

    if ai_analysis and EXIBIR_ANALISE_IA:
        body.append({
            "type": "TextBlock",
            "text": f"{ICON_IA} Análise automática (IA)",
            "weight": "Bolder",
            "spacing": "Medium",
            "wrap": True,
        })
        body.append({
            "type": "FactSet",
            "facts": [{"title": "IA:", "value": _clean(ai_analysis)[:MAX_IA_CHARS]}],
        })

    if details and EXIBIR_DETALHES:
        body.append({"type": "TextBlock", "text": "Detalhes técnicos:", "weight": "Bolder", "spacing": "Medium", "wrap": True})
        body.append({"type": "TextBlock", "text": _clean(details[-MAX_TRACEBACK_CHARS:]), "wrap": True, "size": "Small"})

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.2",
                    "body": body,
                },
            }
        ],
    }


def notify(
    webhook_url: str,
    title: str,
    message: str,
    success: bool = True,
    details: str = None,
    duration: float = None,
    ai_analysis: str = None,
):
    if not webhook_url:
        return
    try:
        payload = _build_card(
            title=title,
            message=message,
            success=success,
            details=details,
            duration=duration,
            ai_analysis=ai_analysis,
        )
        resp = requests.post(webhook_url, json=payload, timeout=TEAMS_TIMEOUT, verify=SSL_VERIFY)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"[teams] notification failed: {type(e).__name__}: {e}")
