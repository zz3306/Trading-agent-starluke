"""Valuation Analyst: peer comparison, valuation multiples, and stock personality classification."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_fundamentals,
    get_income_statement,
    get_language_instruction,
)

logger = logging.getLogger(__name__)

# Maximum tool-call iterations inside one node execution.
# Each iteration = one Claude CLI call (~30-90 s), so 10 allows up to ~6 peers
# without the graph ever looping back to this node.
_MAX_ITERS = 10


def create_valuation_analyst(llm):
    tools = [get_fundamentals, get_income_statement]
    _tool_map = {t.name: t for t in tools}
    valuation_llm = llm.bind_tools(tools)

    def valuation_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)
        fundamentals_report = state.get("fundamentals_report", "")

        if fundamentals_report:
            target_instruction = (
                f"The target company ({ticker}) has already been analyzed by the "
                f"Fundamentals Analyst. Existing report for reference:\n\n"
                f"{fundamentals_report}\n\n"
                f"Do NOT call tools for {ticker} itself — only fetch data for its 3-4 peers."
            )
        else:
            target_instruction = (
                f"Fetch fundamentals and income statement for {ticker} AND its "
                f"3-4 direct competitors."
            )

        system_prompt = (
            f"You are a Valuation Analyst. Your job is to assess {ticker}'s valuation "
            f"relative to its peers and classify its investment personality.\n\n"
            f"{target_instruction}\n\n"
            f"Step 1 — Identify 3-4 direct competitor ticker symbols for {ticker} "
            f"from your knowledge.\n"
            f"Step 2 — Call get_fundamentals and get_income_statement for each peer "
            f"to get real data.\n"
            f"Step 3 — Write a structured valuation report with these sections:\n\n"
            f"**1. Stock Personality Classification**\n"
            f"Classify as exactly one of:\n"
            f"- 长期复利股 (Compounder): recurring revenue, low beta, crosses cycles\n"
            f"- 高速成长股 (High-growth): 30%+ revenue growth, clear product-market fit\n"
            f"- 周期股 (Cyclical): revenue tied to macro/commodity cycles\n"
            f"- 价值股 (Value): low multiples, stable cash flow, slow growth\n"
            f"- Story股 (Story): valuation driven by narrative more than fundamentals\n"
            f"- 价值陷阱 (Value Trap): cheap-looking but business is permanently deteriorating\n\n"
            f"State your classification and justify it in 2-3 sentences.\n\n"
            f"**2. Peer Comparison Table**\n"
            f"Build a markdown table with these columns:\n"
            f"| Company | Ticker | Market Cap | Rev Growth (YoY) | Gross Margin | "
            f"Op Margin | P/E | EV/Revenue |\n\n"
            f"Fill with real data from your tool calls. Mark unavailable fields as 'N/A'.\n\n"
            f"**3. Valuation Assessment**\n"
            f"- Premium or discount vs peer median? By how much?\n"
            f"- Is the gap justified by {ticker}'s growth or margin profile?\n"
            f"- What growth rate does current valuation imply the market is pricing in?\n\n"
            f"**4. Key Risks to Valuation**\n"
            f"List 2-3 specific risks that could compress the multiple.\n\n"
            f"Current date: {current_date}. {instrument_context}"
            f"{get_language_instruction()}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Perform a complete peer valuation analysis for {ticker} as of {current_date}."
            ),
        ]

        report = "[Valuation analysis unavailable]"
        try:
            for _ in range(_MAX_ITERS):
                response = valuation_llm.invoke(messages)
                messages.append(response)

                if not response.tool_calls:
                    report = response.content or report
                    break

                # Execute each tool call directly (no graph round-trip)
                for tc in response.tool_calls:
                    tool_fn = _tool_map.get(tc["name"])
                    try:
                        result = tool_fn.invoke(tc["args"]) if tool_fn else f"[Unknown tool: {tc['name']}]"
                    except Exception as exc:
                        result = f"[Tool error: {exc}]"
                    messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            else:
                # Hit iteration limit — ask for a summary with data collected so far
                messages.append(HumanMessage(content="Summarize your valuation findings now based on the data collected so far."))
                response = valuation_llm.invoke(messages)
                messages.append(response)
                report = response.content or report

        except Exception as exc:
            logger.warning("Valuation analyst failed: %s", exc)

        return {"messages": messages, "valuation_report": report}

    return valuation_analyst_node
