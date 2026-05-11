"""Per-analyst report cache — skips re-running an analyst if today's report exists on disk."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)

# Analyst type → state key that holds its report
_REPORT_KEY: dict[str, str] = {
    "market":       "market_report",
    "social":       "sentiment_report",
    "news":         "news_report",
    "fundamentals": "fundamentals_report",
    "valuation":    "valuation_report",
    "macro":        "macro_report",
    "options":      "options_report",
}


def _cache_path(cache_dir: str, ticker: str, trade_date: str, analyst_type: str) -> Path:
    return Path(cache_dir) / "analyst_cache" / ticker / trade_date / f"{analyst_type}.txt"


def with_analyst_cache(analyst_type: str, node_fn: Callable) -> Callable:
    """Wrap an analyst node so it reads/writes a per-day disk cache.

    On cache hit  → returns cached report instantly (no LLM call).
    On cache miss → runs node_fn normally, then saves the report to disk.
    """
    report_key = _REPORT_KEY.get(analyst_type, f"{analyst_type}_report")

    def cached_node(state: dict) -> dict:
        from tradingagents.dataflows.config import get_config
        config = get_config()
        cache_dir = config.get("data_cache_dir", "dataflows/data")

        ticker = state.get("company_of_interest", "UNKNOWN")
        trade_date = state.get("trade_date", "unknown")

        path = _cache_path(cache_dir, ticker, str(trade_date), analyst_type)

        # ── Cache hit ──────────────────────────────────────────────────
        if path.exists():
            try:
                cached = path.read_text(encoding="utf-8").strip()
                _poisoned = (
                    len(cached) < 80
                    or "prompt injection" in cached.lower()
                    or "i need to flag" in cached[:300].lower()
                    or cached.startswith("[ERROR]")
                    or "not comply" in cached[:300].lower()
                )
                if cached and not _poisoned:
                    logger.info("Cache hit: %s for %s on %s", analyst_type, ticker, trade_date)
                    return {
                        "messages": [AIMessage(content=f"[{analyst_type} report loaded from cache]")],
                        report_key: cached,
                    }
                elif _poisoned:
                    logger.warning("Poisoned cache for %s — deleting and re-running", analyst_type)
                    path.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning("Cache read failed for %s: %s — re-running analyst", analyst_type, exc)

        # ── Cache miss — run the analyst ───────────────────────────────
        result = node_fn(state)

        report = result.get(report_key, "")
        # Only cache real reports (not short error/refusal placeholders)
        _should_cache = (
            report
            and len(report) > 80
            and "prompt injection" not in report.lower()
            and not report.startswith("[ERROR]")
        )
        if _should_cache:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(report, encoding="utf-8")
                logger.info("Cache saved: %s for %s on %s", analyst_type, ticker, trade_date)
            except Exception as exc:
                logger.warning("Cache write failed for %s: %s", analyst_type, exc)

        return result

    cached_node.__name__ = f"cached_{analyst_type}_node"
    return cached_node
