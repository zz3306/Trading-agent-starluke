"""Simple file-based cache for yfinance data.

Historical data (date < today) is cached indefinitely — it never changes.
Today's data is never cached (intraday prices are still moving).
Macro indicators are cached for MACRO_TTL_DAYS days.
"""

import hashlib
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

MACRO_TTL_DAYS = 7

_cache_dir: Optional[Path] = None


def set_cache_dir(path: str | Path) -> None:
    global _cache_dir
    _cache_dir = Path(path)
    _cache_dir.mkdir(parents=True, exist_ok=True)


def _get_cache_dir() -> Path:
    if _cache_dir is None:
        default = Path.home() / ".tradingagents" / "data_cache"
        default.mkdir(parents=True, exist_ok=True)
        return default
    return _cache_dir


def _cache_path(key: str) -> Path:
    return _get_cache_dir() / f"{key}.json"


def _make_key(method: str, args: tuple, kwargs: dict) -> str:
    raw = json.dumps({"m": method, "a": list(args), "k": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


def _is_historical(args: tuple, kwargs: dict) -> bool:
    """Return True if any date arg is strictly before today (safe to cache forever)."""
    today = date.today().isoformat()
    for val in list(args) + list(kwargs.values()):
        if isinstance(val, str) and len(val) == 10:
            try:
                datetime.strptime(val, "%Y-%m-%d")
                if val < today:
                    return True
            except ValueError:
                pass
    return False


def cached_call(
    method: str,
    fn: Callable,
    args: tuple,
    kwargs: dict,
    macro: bool = False,
) -> Any:
    """Call fn(*args, **kwargs), using disk cache when appropriate."""
    # Never cache today's data
    if not macro and not _is_historical(args, kwargs):
        return fn(*args, **kwargs)

    key = _make_key(method, args, kwargs)
    path = _cache_path(key)

    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            # Check TTL for macro data
            if macro:
                cached_at = datetime.fromisoformat(payload.get("cached_at", "2000-01-01"))
                if datetime.now() - cached_at > timedelta(days=MACRO_TTL_DAYS):
                    logger.debug("Macro cache expired for %s", method)
                    path.unlink(missing_ok=True)
                else:
                    logger.debug("Cache HIT (macro) %s", key[:8])
                    return payload["data"]
            else:
                logger.debug("Cache HIT %s", key[:8])
                return payload["data"]
        except Exception:
            path.unlink(missing_ok=True)

    logger.debug("Cache MISS %s %s", method, key[:8])
    result = fn(*args, **kwargs)

    try:
        path.write_text(
            json.dumps({"data": result, "cached_at": datetime.now().isoformat()}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Cache write failed: %s", exc)

    return result
