from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from tradingagents.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradingagents.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_insider_transactions,
    get_global_news
)
from tradingagents.agents.utils.options_tools import (
    get_options_chain,
    get_stock_price_for_options,
)


def get_language_instruction() -> str:
    """Return a prompt instruction for the configured output language.

    Returns empty string when English (default), so no extra tokens are used.
    Only applied to user-facing agents (analysts, portfolio manager).
    Internal debate agents stay in English for reasoning quality.
    """
    from tradingagents.dataflows.config import get_config
    lang = get_config().get("output_language", "English")
    if lang.strip().lower() == "english":
        return ""
    return f" Write your entire response in {lang}."


def build_instrument_context(ticker: str) -> str:
    """Describe the exact instrument so agents preserve exchange-qualified tickers."""
    base = (
        f"The instrument to analyze is `{ticker}`. "
        "Use this exact ticker in every tool call, report, and recommendation, "
        "preserving any exchange suffix (e.g. `.TO`, `.L`, `.HK`, `.T`)."
    )

    upper = ticker.upper()
    if upper.endswith(".SS") or upper.endswith(".SZ"):
        base += (
            " This is a Chinese A-share listed on "
            + ("the Shanghai Stock Exchange (SSE)" if upper.endswith(".SS") else "the Shenzhen Stock Exchange (SZSE)")
            + ". Price data is quoted in CNY (Chinese Yuan). "
            "All OHLCV values, technical indicators, and financial figures returned by tools "
            "are valid and correct — do NOT report them as N/A, unavailable, or unresolvable "
            "simply because the format differs from US equities. "
            "Analyze the data as-is and write a full report."
        )
    elif upper.endswith(".HK"):
        base += (
            " This is a Hong Kong-listed stock (HKEX). "
            "Price data is quoted in HKD. Treat all tool-returned data as valid."
        )

    return base

def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


        
