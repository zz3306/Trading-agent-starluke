"""News Analyst: company-specific and global macro news."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_global_news,
    get_language_instruction,
    get_news,
)

logger = logging.getLogger(__name__)

_MAX_ITERS = 6


def create_news_analyst(llm):
    tools = [get_news, get_global_news]
    _tool_map = {t.name: t for t in tools}
    news_llm = llm.bind_tools(tools)

    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)

        try:
            end_dt = datetime.strptime(current_date, "%Y-%m-%d")
            start_date = (end_dt - timedelta(days=7)).strftime("%Y-%m-%d")
        except Exception:
            start_date = current_date

        system_prompt = (
            f"You are a News Analyst. Your job is to research recent news relevant to trading "
            f"{ticker} and the broader macro environment.\n\n"
            f"Use your available tools to fetch company-specific and macro/sector news for {ticker} "
            f"from {start_date} to {current_date}.\n\n"
            f"Write a comprehensive news report covering:\n"
            f"- Key company-specific news events\n"
            f"- Regulatory or competitive developments\n"
            f"- Relevant macro/sector trends\n"
            f"- News sentiment and momentum\n"
            f"- Actionable insights for traders\n"
            f"Append a Markdown table summarizing news items by date/topic.\n\n"
            f"Date range: {start_date} to {current_date}. {instrument_context}"
            f"{get_language_instruction()}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Research news relevant to {ticker} and the macro environment as of {current_date}."
            ),
        ]

        report = "[News analysis unavailable]"
        try:
            for _ in range(_MAX_ITERS):
                response = news_llm.invoke(messages)
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
                messages.append(HumanMessage(content="Summarize your news findings now based on the data collected."))
                response = news_llm.invoke(messages)
                messages.append(response)
                report = response.content or report

        except Exception as exc:
            logger.warning("News analyst failed: %s", exc)

        return {"messages": messages, "news_report": report}

    return news_analyst_node
