"""Valuation Analyst: peer comparison, valuation multiples, and stock personality classification."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_fundamentals,
    get_income_statement,
    get_language_instruction,
)


def create_valuation_analyst(llm):
    def valuation_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)
        fundamentals_report = state.get("fundamentals_report", "")

        tools = [get_fundamentals, get_income_statement]

        if fundamentals_report:
            target_instruction = (
                f"The target company ({ticker}) has already been analyzed by the Fundamentals Analyst. "
                f"Existing report for reference:\n\n{fundamentals_report}\n\n"
                f"Do NOT call tools for {ticker} itself — only fetch data for its 3-4 peers."
            )
        else:
            target_instruction = (
                f"Fetch fundamentals and income statement for {ticker} AND its 3-4 direct competitors."
            )

        system_message = f"""You are a Valuation Analyst. Your job is to assess {ticker}'s valuation relative to its peers and classify its investment personality.

{target_instruction}

Step 1 — Identify 3-4 direct competitor ticker symbols for {ticker} from your knowledge.
Step 2 — Call get_fundamentals and get_income_statement for each peer to get real data.
Step 3 — Write a structured valuation report with these sections:

**1. Stock Personality Classification**
Classify as exactly one of:
- 长期复利股 (Compounder): recurring revenue, low beta, crosses cycles
- 高速成长股 (High-growth): 30%+ revenue growth, clear product-market fit
- 周期股 (Cyclical): revenue tied to macro/commodity cycles
- 价值股 (Value): low multiples, stable cash flow, slow growth
- Story股 (Story): valuation driven by narrative more than fundamentals
- 价值陷阱 (Value Trap): cheap-looking but business is permanently deteriorating

State your classification and justify it in 2-3 sentences.

**2. Peer Comparison Table**
Build a markdown table with these columns:
| Company | Ticker | Market Cap | Rev Growth (YoY) | Gross Margin | Op Margin | P/E | EV/Revenue |

Fill with real data from your tool calls. Mark unavailable fields as "N/A".

**3. Valuation Assessment**
- Premium or discount vs peer median? By how much?
- Is the gap justified by {ticker}'s growth or margin profile?
- What growth rate does current valuation imply the market is pricing in?

**4. Key Risks to Valuation**
List 2-3 specific risks that could compress the multiple (e.g. margin deterioration, competitive pressure, rate sensitivity).

Use get_fundamentals first to get an overview, then get_income_statement for revenue and margin details.{get_language_instruction()}"""

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a helpful AI assistant collaborating with other assistants. "
                "Use the provided tools to fetch peer financial data and build a valuation comparison. "
                "You have access to the following tools: {tool_names}.\n{system_message}"
                "The current date is {current_date}. {instrument_context}",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ])

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([t.name for t in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "valuation_report": report,
        }

    return valuation_analyst_node
