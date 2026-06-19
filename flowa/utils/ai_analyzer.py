import logging
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

SSL_VERIFY = False
MAX_TRACEBACK_CHARS = 3000

_PROMPT = """You are a senior Python software engineer.

Analyze the pipeline failure below and return:
1. Probable cause
2. How to fix it
3. Suspicious line
4. Fix example

Keep it short and objective. Answer in the same language as the error/context.

Context: {context}

Error details:
{details}
"""

_DEFAULTS = {
    "groq":   ("llama-3.3-70b-versatile", 500, 30),
    "openai": ("gpt-4o-mini",              500, 30),
    "claude": ("claude-haiku-4-5-20251001", 500, 30),
    "gemini": ("gemini-1.5-flash",          500, 30),
}


def _openai_compat(url: str, api_key: str, model: str, prompt: str, max_tokens: int, timeout: int) -> str:
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        },
        timeout=timeout,
        verify=SSL_VERIFY,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_groq(api_key: str, model: str, prompt: str, max_tokens: int, timeout: int) -> str:
    return _openai_compat("https://api.groq.com/openai/v1/chat/completions", api_key, model, prompt, max_tokens, timeout)


def _call_openai(api_key: str, model: str, prompt: str, max_tokens: int, timeout: int) -> str:
    return _openai_compat("https://api.openai.com/v1/chat/completions", api_key, model, prompt, max_tokens, timeout)


def _call_claude(api_key: str, model: str, prompt: str, max_tokens: int, timeout: int) -> str:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
        verify=SSL_VERIFY,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def _call_gemini(api_key: str, model: str, prompt: str, max_tokens: int, timeout: int) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    resp = requests.post(
        url,
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2},
        },
        timeout=timeout,
        verify=SSL_VERIFY,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


_CALLERS = {
    "groq":   _call_groq,
    "openai": _call_openai,
    "claude": _call_claude,
    "gemini": _call_gemini,
}


def analyze_error(details: str, context: str = "", ai_config: dict = None) -> str | None:
    if not ai_config:
        return None

    provider = ai_config.get("provider", "none")
    if not provider or provider == "none":
        return None

    caller = _CALLERS.get(provider)
    if not caller:
        logger.warning(f"[ai] unknown provider '{provider}'")
        return None

    default_model, default_tokens, default_timeout = _DEFAULTS[provider]
    cfg = ai_config.get(provider, {})
    api_key = cfg.get("api_key", "")

    if not api_key:
        logger.warning(f"[ai] api_key not set for provider '{provider}'")
        return None

    model = cfg.get("model", default_model)
    max_tokens = cfg.get("max_tokens", default_tokens)
    timeout = cfg.get("timeout", default_timeout)
    prompt = _PROMPT.format(context=context or "Flowa pipeline", details=details[-MAX_TRACEBACK_CHARS:])

    try:
        result = caller(api_key, model, prompt, max_tokens, timeout)
        logger.info(f"[ai] analysis done via {provider}/{model}")
        return result
    except Exception as e:
        logger.warning(f"[ai] {provider} failed: {type(e).__name__}: {e}")
        return None
