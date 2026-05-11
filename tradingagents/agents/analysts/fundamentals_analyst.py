"""Fundamentals Analyst: financial statements and company profile."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
    get_language_instruction,
)

logger = logging.getLogger(__name__)

_MAX_ITERS = 8


def create_fundamentals_analyst(llm):
    tools = [get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement]
    _tool_map = {t.name: t for t in tools}
    fundamentals_llm = llm.bind_tools(tools)

    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)

        system_prompt = (
            f"You are a Fundamentals Analyst. Your job is to analyze the financial health "
            f"and business fundamentals of {ticker}.\n\n"
            f"Use the available tools:\n"
            f"- get_fundamentals: comprehensive company profile and key metrics\n"
            f"- get_balance_sheet: assets, liabilities, equity\n"
            f"- get_cashflow: operating, investing, financing cash flows\n"
            f"- get_income_statement: revenue, margins, earnings\n\n"
            f"Call all four tools to get a complete picture.\n\n"
            f"Write a comprehensive fundamentals report covering:\n"
            f"- Business overview and competitive position\n"
            f"- Revenue growth and profitability trends\n"
            f"- Balance sheet strength (debt, liquidity, equity)\n"
            f"- Cash flow generation quality\n"
            f"- Key financial ratios and red flags\n"
            f"- Actionable insights for traders and investors\n"
            f"Append a Markdown table organizing key financial metrics.\n\n"
            f"Current date: {current_date}. {instrument_context}"
            f"{get_language_instruction()}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Perform a complete fundamental analysis for {ticker} as of {current_date}."
            ),
        ]

        report = "[Fundamentals analysis unavailable]"
        try:
            for _ in range(_MAX_ITERS):
                response = fundamentals_llm.invoke(messages)
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
                messages.append(HumanMessage(content="Summarize your fundamentals findings now based on the data collected."))
                response = fundamentals_llm.invoke(messages)
                messages.append(response)
                report = response.content or report

        except Exception as exc:
            logger.warning("Fundamentals analyst failed: %s", exc)

        return {"messages": messages, "fundamentals_report": report}

    return fundamentals_analyst_node
