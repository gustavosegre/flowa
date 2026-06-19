import socket
import logging
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

HOSTNAME = socket.gethostname()
SSL_VERIFY = False
IMG_ERRO = (
    "https://ih1.redbubble.net/image.2579899118.1732/"
    "st,small,507x507-pad,600x600,f8f8f8.jpg"
)
IMG_SUCESSO = (
    "https://i.pinimg.com/originals/d6/71/b5/"
    "d671b57b99533df856544bb3f30fe559.gif"
)
MAX_TRACEBACK_CHARS = 700


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
) -> dict:
    color = "good" if success else "attention"
    icon = "✅" if success else "❌"
    image = IMG_SUCESSO if success else IMG_ERRO

    body = [
        {
            "type": "ColumnSet",
            "columns": [
                {
                    "type": "Column",
                    "width": "auto",
                    "items": [
                        {
                            "type": "Image",
                            "url": image,
                            "size": "Large",
                            "style": "Person",
                        }
                    ],
                },
                {
                    "type": "Column",
                    "width": "stretch",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "FLOWA",
                            "weight": "Bolder",
                            "size": "Medium",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": HOSTNAME,
                            "isSubtle": True,
                            "spacing": "None",
                            "wrap": True,
                        },
                    ],
                },
            ],
        },
        {
            "type": "TextBlock",
            "text": f"{icon} {_clean(title)}",
            "weight": "Bolder",
            "size": "Large",
            "color": color,
            "wrap": True,
        },
        {"type": "TextBlock", "text": _clean(message), "wrap": True},
    ]

    facts = [{"title": "Data:", "value": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}]
    if duration is not None:
        facts.append({"title": "Duração:", "value": f"{duration:.2f}s"})
    body.append({"type": "FactSet", "facts": facts})

    if details:
        body.append(
            {
                "type": "TextBlock",
                "text": "Detalhes:",
                "weight": "Bolder",
                "spacing": "Medium",
                "wrap": True,
            }
        )
        body.append(
            {
                "type": "TextBlock",
                "text": _clean(details[-MAX_TRACEBACK_CHARS:]),
                "wrap": True,
                "size": "Small",
            }
        )

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
        )
        resp = requests.post(webhook_url, json=payload, timeout=10, verify=SSL_VERIFY)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"[teams] notification failed: {type(e).__name__}: {e}")
