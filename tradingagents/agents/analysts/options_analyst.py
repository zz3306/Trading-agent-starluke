"""Options Analyst: LEAP vs stock recommendation based on yfinance options chain."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.options_tools import (
    get_options_chain,
    get_stock_price_for_options,
)


def create_options_analyst(llm):
    def options_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)

        tools = [get_stock_price_for_options, get_options_chain]

        system_message = f"""You are an Options Analyst specializing in LEAP options strategy.

Your job is to determine whether an investor should:
1. **BUY STOCK** — purchase shares outright
2. **BUY LEAP CALLS** — buy long-dated call options (typically 6–18 months to expiry)
3. **SPLIT** — allocate part to stock and part to LEAPs

**Workflow:**
Step 1 — Call `get_stock_price_for_options` to get the current price, 52-week range, and historical volatility for {ticker}.
Step 2 — Call `get_options_chain` to retrieve the available LEAP expirations and the ATM options table.
Step 3 — Write a structured Options Analysis Report with these sections:

---

**1. LEAP Suitability Check**
Answer these questions:
- Is there sufficient open interest and volume in the LEAP strikes? (Liquidity)
- Is implied volatility reasonable relative to historical volatility? (IV rank assessment)
- Does {ticker} have binary event risk (upcoming earnings, FDA approval, etc.) that could spike IV?

**2. LEAP vs Stock Cost Comparison**
Pick one representative LEAP strike (ATM or slightly OTM) and show:
- LEAP mid price and expiration
- Capital required per contract (mid × 100)
- Equivalent stock cost for 100 shares
- Capital efficiency ratio (stock cost ÷ LEAP cost)
- Breakeven price at expiration

**3. Risk/Reward Analysis**
- Max loss scenario: LEAP goes to $0 vs stock drawdown risk
- Upside leverage: % gain if stock rises 20%, 40%
- Time decay pressure (theta burn — is theta manageable relative to the expected move?)

**4. Recommendation**
State exactly one of:
- **BUY STOCK** — with justification
- **BUY LEAP** — specify the recommended strike and expiration
- **SPLIT (X% stock / Y% LEAP)** — with justification

Include a one-paragraph rationale referencing the data you fetched.

---

Keep the report data-driven and concise. Always use specific numbers from the options chain.{get_language_instruction()}"""

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a helpful AI assistant collaborating with other assistants. "
                "Use the provided tools to fetch live options data and produce a LEAP vs stock recommendation. "
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
            "options_report": report,
        }

    return options_analyst_node
