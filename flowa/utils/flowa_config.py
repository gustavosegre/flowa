import os
import yaml
import logging

logger = logging.getLogger(__name__)

_cache: dict | None = None


def _config_path() -> str:
    return os.getenv("FLOWA_CONFIG_PATH", "flowa-core/config.yaml")


def load_config(force_reload: bool = False) -> dict:
    global _cache
    if _cache is not None and not force_reload:
        return _cache

    path = _config_path()
    if not os.path.exists(path):
        _cache = {}
        return _cache

    try:
        with open(path, "r", encoding="utf-8") as f:
            _cache = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"[config] failed to load {path}: {e}")
        _cache = {}

    return _cache


def get_ai_config() -> dict:
    return load_config().get("ai", {})
