"""Social Media Analyst: company news and sentiment from social sources."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    get_news,
)

logger = logging.getLogger(__name__)

_MAX_ITERS = 5


def create_social_media_analyst(llm):
    tools = [get_news]
    _tool_map = {t.name: t for t in tools}
    social_llm = llm.bind_tools(tools)

    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)

        try:
            end_dt = datetime.strptime(current_date, "%Y-%m-%d")
            start_date = (end_dt - timedelta(days=7)).strftime("%Y-%m-%d")
        except Exception:
            start_date = current_date

        system_prompt = (
            f"You are a Social Media and Sentiment Analyst. Your job is to analyze recent "
            f"public sentiment and company-specific news for {ticker} over the past week.\n\n"
            f"Use get_news to search for relevant news and social media discussions. "
            f"Make multiple searches with different queries to get broad coverage:\n"
            f"- Search for '{ticker} stock sentiment'\n"
            f"- Search for '{ticker} news'\n"
            f"- Search for '{ticker} analyst opinions'\n\n"
            f"Write a comprehensive report covering:\n"
            f"- Overall public sentiment (bullish/neutral/bearish)\n"
            f"- Key themes and narratives in social media\n"
            f"- Recent company-specific news highlights\n"
            f"- Sentiment shift or momentum\n"
            f"- Actionable insights for traders\n"
            f"Append a Markdown table summarizing sentiment by source/date.\n\n"
            f"Date range: {start_date} to {current_date}. {instrument_context}"
            f"{get_language_instruction()}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Research social media sentiment and news for {ticker} from {start_date} to {current_date}."
            ),
        ]

        report = "[Sentiment analysis unavailable]"
        try:
            for _ in range(_MAX_ITERS):
                response = social_llm.invoke(messages)
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
                messages.append(HumanMessage(content="Summarize your sentiment findings now based on the data collected."))
                response = social_llm.invoke(messages)
                messages.append(response)
                report = response.content or report

        except Exception as exc:
            logger.warning("Social media analyst failed: %s", exc)

        return {"messages": messages, "sentiment_report": report}

    return social_media_analyst_node
