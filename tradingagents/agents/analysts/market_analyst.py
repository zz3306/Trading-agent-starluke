"""Market Analyst: stock price data and technical indicators."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_indicators,
    get_language_instruction,
    get_stock_data,
)

logger = logging.getLogger(__name__)

_MAX_ITERS = 6


def create_market_analyst(llm):
    tools = [get_stock_data, get_indicators]
    _tool_map = {t.name: t for t in tools}
    market_llm = llm.bind_tools(tools)

    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)

        system_prompt = (
            f"You are a Market Analyst. Your job is to analyze price trends and technical signals "
            f"for {ticker}.\n\n"
            f"Step 1 — Call get_stock_data to retrieve the price CSV for {ticker}.\n"
            f"Step 2 — Call get_indicators with up to 8 complementary indicators chosen from:\n"
            f"  Moving Averages: close_50_sma, close_200_sma, close_10_ema\n"
            f"  MACD: macd, macds, macdh\n"
            f"  Momentum: rsi\n"
            f"  Volatility: boll, boll_ub, boll_lb, atr\n"
            f"  Volume: vwma\n"
            f"Select indicators that complement each other without redundancy.\n\n"
            f"Step 3 — Write a detailed market analysis report covering:\n"
            f"- Trend direction and strength (short/medium/long-term)\n"
            f"- Key support and resistance levels\n"
            f"- Momentum and volume signals\n"
            f"- Actionable insights for traders\n"
            f"Append a Markdown table summarizing key data points.\n\n"
            f"Current date: {current_date}. {instrument_context}"
            f"{get_language_instruction()}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Perform a complete technical market analysis for {ticker} as of {current_date}."
            ),
        ]

        report = "[Market analysis unavailable]"
        try:
            for _ in range(_MAX_ITERS):
                response = market_llm.invoke(messages)
                messages.append(response)

                if not response.tool_calls:
                    report = response.content or report
                    break

                for tc in response.tool_calls:
                    tool_fn = _tool_map.get(tc["name"])
                    try:
                        result = tool_fn.invoke(tc["args"]) if tool_fn else f"[Unknown tool: {tc['name']}]"
                    except Exception as exc:
                        result = f"[Tool error: {exc}]"
                    messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            else:
                messages.append(HumanMessage(content="Summarize your market analysis now based on the data collected."))
                response = market_llm.invoke(messages)
                messages.append(response)
                report = response.content or report

        except Exception as exc:
            logger.warning("Market analyst failed: %s", exc)

        return {"messages": messages, "market_report": report}

    return market_analyst_node
