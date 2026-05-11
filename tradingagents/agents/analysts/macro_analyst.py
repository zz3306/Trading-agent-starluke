import logging
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Annotated

from tradingagents.dataflows.macro_data_tools import get_macro_indicators
from tradingagents.agents.utils.agent_utils import get_language_instruction

logger = logging.getLogger(__name__)


@tool
def fetch_macro_data(
    curr_date: Annotated[str, "Current analysis date yyyy-mm-dd"],
) -> str:
    """Fetch key macro-economic indicators: treasury yields, VIX, US Dollar index, yield curve."""
    return get_macro_indicators(curr_date)


def create_macro_analyst(llm):
    macro_llm = llm.bind_tools([fetch_macro_data])

    def macro_node(state) -> dict:
        company = state.get("company_of_interest", "")
        trade_date = state.get("trade_date", "")

        messages = [
            SystemMessage(content=(
                "You are a Macro-Economic Analyst. Your job is to assess the current macro "
                "environment — interest rates, yield curve, market fear (VIX), and dollar strength — "
                "and explain how these conditions affect the stock being analyzed. "
                "Use the fetch_macro_data tool to retrieve current indicators. "
                "Then write a concise macro report covering:\n"
                "1. Interest rate environment (Fed direction, yield curve shape)\n"
                "2. Market risk appetite (VIX level)\n"
                "3. Dollar strength and its sector implications\n"
                "4. Overall macro tailwinds or headwinds for equities\n"
                "Keep it practical — tie the macro picture directly to the stock being analyzed."
                + get_language_instruction()
            )),
            HumanMessage(content=(
                f"Analyze the macro environment as of {trade_date} and explain how it affects {company}. "
                f"Call fetch_macro_data with curr_date='{trade_date}'."
            )),
        ]

        try:
            # Agentic loop: allow up to 3 rounds (tool call → result → final answer)
            for _ in range(3):
                response = macro_llm.invoke(messages)
                messages.append(response)

                if not response.tool_calls:
                    break

                from langchain_core.messages import ToolMessage
                for tc in response.tool_calls:
                    try:
                        result = fetch_macro_data.invoke(tc["args"])
                    except Exception as exc:
                        result = f"[Tool error: {exc}]"
                    messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

            report = response.content or "[Macro analyst produced no output]"
        except Exception as exc:
            logger.warning("Macro analyst failed: %s", exc)
            report = "[Macro analysis unavailable due to an error.]"

        return {"messages": messages, "macro_report": report}

    return macro_node
