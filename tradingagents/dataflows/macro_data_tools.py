"""Macro-economic data tools using yfinance.

Fetches key macro indicators: 10Y/2Y treasury yields, VIX, US Dollar index.
Results are cached for MACRO_TTL_DAYS (7 days) since these don't change intraday.
"""

import logging
from datetime import datetime, timedelta
from typing import Annotated

import yfinance as yf

from .cache import cached_call
from .stockstats_utils import yf_retry

logger = logging.getLogger(__name__)

# Tickers for macro indicators available on yfinance
_MACRO_TICKERS = {
    "10Y Treasury Yield (%)": "^TNX",
    "2Y Treasury Yield (%)": "^IRX",   # 13-week T-bill as short-rate proxy
    "VIX (Fear Index)": "^VIX",
    "US Dollar Index": "DX-Y.NYB",
    "S&P 500": "^GSPC",
}


def _fetch_macro_snapshot(curr_date: str) -> str:
    """Pull latest values for key macro indicators up to curr_date."""
    end = curr_date
    start = (datetime.strptime(curr_date, "%Y-%m-%d") - timedelta(days=10)).strftime("%Y-%m-%d")

    lines = ["## Macro Indicator Snapshot", f"As of {curr_date}", ""]
    lines.append("| Indicator | Latest Value | 5-day Change |")
    lines.append("|-----------|-------------|--------------|")

    for label, ticker in _MACRO_TICKERS.items():
        try:
            data = yf_retry(lambda t=ticker: yf.Ticker(t).history(start=start, end=end))
            if data.empty:
                lines.append(f"| {label} | N/A | N/A |")
                continue
            closes = data["Close"].dropna()
            if len(closes) == 0:
                lines.append(f"| {label} | N/A | N/A |")
                continue
            latest = closes.iloc[-1]
            change = latest - closes.iloc[0] if len(closes) > 1 else 0
            sign = "+" if change >= 0 else ""
            lines.append(f"| {label} | {latest:.2f} | {sign}{change:.2f} |")
        except Exception as exc:
            logger.warning("Macro fetch failed for %s: %s", ticker, exc)
            lines.append(f"| {label} | Error | Error |")

    return "\n".join(lines)


def _fetch_yield_curve(curr_date: str) -> str:
    """Return a brief yield curve analysis (10Y minus 2Y spread)."""
    start = (datetime.strptime(curr_date, "%Y-%m-%d") - timedelta(days=10)).strftime("%Y-%m-%d")
    try:
        t10 = yf_retry(lambda: yf.Ticker("^TNX").history(start=start, end=curr_date))
        t2 = yf_retry(lambda: yf.Ticker("^IRX").history(start=start, end=curr_date))
        if t10.empty or t2.empty:
            return "Yield curve data unavailable."
        spread = t10["Close"].iloc[-1] - t2["Close"].iloc[-1]
        if spread > 0:
            shape = "normal (upward sloping)"
            implication = "Market expects growth; not signaling imminent recession."
        elif spread > -0.5:
            shape = "flat"
            implication = "Mixed signals; growth uncertainty."
        else:
            shape = "inverted"
            implication = "Historically associated with recession risk within 12-18 months."
        return (
            f"## Yield Curve\n"
            f"10Y–2Y Spread: {spread:+.2f}%  →  **{shape}**\n"
            f"{implication}"
        )
    except Exception as exc:
        logger.warning("Yield curve fetch failed: %s", exc)
        return "Yield curve data unavailable."


def get_macro_indicators(
    curr_date: Annotated[str, "Current analysis date yyyy-mm-dd"],
) -> str:
    """Fetch key macro indicators: treasury yields, VIX, dollar index, yield curve.
    Results are cached for 7 days.
    """
    def _fetch():
        snapshot = _fetch_macro_snapshot(curr_date)
        curve = _fetch_yield_curve(curr_date)
        return f"{snapshot}\n\n{curve}"

    return cached_call("macro_indicators", _fetch, (curr_date,), {}, macro=True)
