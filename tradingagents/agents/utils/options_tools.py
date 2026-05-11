"""Options data tools using yfinance — free, no API key required."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf
from langchain_core.tools import tool


@tool
def get_options_chain(ticker: str, min_dte: int = 180, max_dte: int = 730) -> str:
    """Fetch the options chain for a ticker, filtered to LEAP-range expirations.

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL")
        min_dte: Minimum days-to-expiry to include (default 180 = ~6 months)
        max_dte: Maximum days-to-expiry to include (default 730 = ~2 years)

    Returns a markdown-formatted report with:
    - Current stock price
    - Available LEAP expiration dates
    - Top calls by open interest for each expiration (ATM ±20%)
    - IV, delta estimate, breakeven, and cost-vs-stock metrics
    """
    try:
        tk = yf.Ticker(ticker)
        info = tk.fast_info
        spot = float(info.last_price)

        today = datetime.today().date()
        cutoff_min = today + timedelta(days=min_dte)
        cutoff_max = today + timedelta(days=max_dte)

        all_expirations = tk.options  # tuple of date strings "YYYY-MM-DD"
        leap_expirations = [
            d for d in all_expirations
            if cutoff_min <= datetime.strptime(d, "%Y-%m-%d").date() <= cutoff_max
        ]

        if not leap_expirations:
            return (
                f"**{ticker} Options Data**\n\n"
                f"Spot price: ${spot:.2f}\n\n"
                f"No options expirations found in the {min_dte}–{max_dte} DTE window. "
                f"Available expirations: {', '.join(all_expirations[:10]) if all_expirations else 'none'}."
            )

        sections = [
            f"## {ticker} Options Chain — LEAP Analysis\n",
            f"**Spot price:** ${spot:.2f}  |  **Analysis window:** {min_dte}–{max_dte} DTE\n",
            f"**LEAP expirations found:** {', '.join(leap_expirations)}\n",
        ]

        for exp_date in leap_expirations[:4]:  # cap at 4 expirations to stay concise
            try:
                chain = tk.option_chain(exp_date)
                calls = chain.calls.copy()

                dte = (datetime.strptime(exp_date, "%Y-%m-%d").date() - today).days

                # Filter ATM ±20%
                lo, hi = spot * 0.80, spot * 1.20
                atm_calls = calls[
                    (calls["strike"] >= lo) & (calls["strike"] <= hi)
                ].copy()

                if atm_calls.empty:
                    atm_calls = calls  # fallback: use all strikes

                # Sort by open interest descending, take top 8
                atm_calls = atm_calls.sort_values("openInterest", ascending=False).head(8)

                rows = []
                for _, row in atm_calls.iterrows():
                    strike = row["strike"]
                    ask = row.get("ask", 0) or 0
                    bid = row.get("bid", 0) or 0
                    iv = row.get("impliedVolatility", 0) or 0
                    oi = int(row.get("openInterest", 0) or 0)
                    vol = int(row.get("volume", 0) or 0)

                    mid = (ask + bid) / 2 if ask and bid else ask or bid
                    breakeven = strike + mid if mid else None
                    cost_vs_stock = (mid / spot * 100) if mid and spot else None
                    moneyness = ((spot - strike) / spot * 100) if spot else 0

                    be_str = f"${breakeven:.2f}" if breakeven else "N/A"
                    cvs_str = f"{cost_vs_stock:.1f}%" if cost_vs_stock else "N/A"
                    iv_str = f"{iv*100:.1f}%" if iv else "N/A"
                    itm_str = f"{'ITM' if moneyness > 0 else 'OTM'} {abs(moneyness):.1f}%"

                    rows.append(
                        f"| ${strike:.0f} | {itm_str} | ${mid:.2f} | {iv_str} | {be_str} | {cvs_str} | {oi:,} | {vol:,} |"
                    )

                header = (
                    f"\n### Expiration: {exp_date} ({dte} DTE)\n\n"
                    "| Strike | Moneyness | Mid Price | IV | Breakeven | Cost/Spot | OI | Volume |\n"
                    "|--------|-----------|-----------|-----|-----------|-----------|-----|--------|\n"
                )
                sections.append(header + "\n".join(rows))

            except Exception as e:
                sections.append(f"\n### Expiration: {exp_date}\n_Data unavailable: {e}_")

        return "\n".join(sections)

    except Exception as e:
        return f"Error fetching options data for {ticker}: {e}"


@tool
def get_stock_price_for_options(ticker: str) -> str:
    """Get current stock price, 52-week range, and basic stats for options context.

    Args:
        ticker: Stock ticker symbol
    """
    try:
        tk = yf.Ticker(ticker)
        info = tk.fast_info
        hist = tk.history(period="1y")

        spot = float(info.last_price)
        week52_hi = float(hist["High"].max()) if not hist.empty else None
        week52_lo = float(hist["Low"].min()) if not hist.empty else None

        # Rough HV30 using log returns
        hv30 = None
        if len(hist) >= 30:
            import math
            closes = hist["Close"].tail(31)
            returns = [math.log(closes.iloc[i] / closes.iloc[i-1]) for i in range(1, len(closes))]
            hv30 = (sum(r**2 for r in returns) / len(returns)) ** 0.5 * math.sqrt(252) * 100

        lines = [
            f"**{ticker} Price Summary**",
            f"- Spot: ${spot:.2f}",
        ]
        if week52_hi and week52_lo:
            lines.append(f"- 52-week range: ${week52_lo:.2f} – ${week52_hi:.2f}")
            pct_from_hi = (spot / week52_hi - 1) * 100
            lines.append(f"- vs 52-week high: {pct_from_hi:.1f}%")
        if hv30:
            lines.append(f"- 30-day historical volatility: {hv30:.1f}%")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching price data for {ticker}: {e}"
