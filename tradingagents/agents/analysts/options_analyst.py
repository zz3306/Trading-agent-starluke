"""Options Analyst: LEAP vs stock recommendation based on options chain."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    get_options_chain,
    get_stock_price_for_options,
)

logger = logging.getLogger(__name__)

_MAX_ITERS = 5


def create_options_analyst(llm):
    tools = [get_stock_price_for_options, get_options_chain]
    _tool_map = {t.name: t for t in tools}
    options_llm = llm.bind_tools(tools)

    def options_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)

        system_prompt = (
            f"You are an Options Analyst specializing in LEAP options strategy.\n\n"
            f"Your job is to determine whether an investor should:\n"
            f"1. **BUY STOCK** — purchase shares outright\n"
            f"2. **BUY LEAP CALLS** — buy long-dated call options (6–18 months to expiry)\n"
            f"3. **SPLIT** — allocate part to stock and part to LEAPs\n\n"
            f"Workflow:\n"
            f"Step 1 — Call get_stock_price_for_options to get current price, 52-week range, and historical volatility for {ticker}.\n"
            f"Step 2 — Call get_options_chain to retrieve LEAP expirations and ATM options table.\n"
            f"Step 3 — Write a structured Options Analysis Report with:\n\n"
            f"**1. LEAP Suitability Check**\n"
            f"- Sufficient open interest and volume? (Liquidity)\n"
            f"- IV reasonable vs historical volatility? (IV rank)\n"
            f"- Binary event risk (earnings, FDA, etc.)?\n\n"
            f"**2. LEAP vs Stock Cost Comparison**\n"
            f"Pick one ATM or slightly OTM LEAP strike and show:\n"
            f"- LEAP mid price and expiration\n"
            f"- Capital required per contract (mid × 100)\n"
            f"- Equivalent stock cost for 100 shares\n"
            f"- Capital efficiency ratio\n"
            f"- Breakeven price at expiration\n\n"
            f"**3. Risk/Reward Analysis**\n"
            f"- Max loss: LEAP to $0 vs stock drawdown\n"
            f"- Upside leverage: % gain if stock rises 20%, 40%\n"
            f"- Theta burn manageability\n\n"
            f"**4. Recommendation**\n"
            f"State exactly one: BUY STOCK, BUY LEAP (with strike/expiry), or SPLIT (X%/Y%).\n\n"
            f"Current date: {current_date}. {instrument_context}"
            f"{get_language_instruction()}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Perform a LEAP vs stock options analysis for {ticker} as of {current_date}."
            ),
        ]

        report = "[Options analysis unavailable]"
        try:
            for _ in range(_MAX_ITERS):
                response = options_llm.invoke(messages)
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
                messages.append(HumanMessage(content="Summarize your options analysis now based on the data collected."))
                response = options_llm.invoke(messages)
                messages.append(response)
                report = response.content or report

        except Exception as exc:
            logger.warning("Options analyst failed: %s", exc)

        return {"messages": messages, "options_report": report}

    return options_analyst_node
