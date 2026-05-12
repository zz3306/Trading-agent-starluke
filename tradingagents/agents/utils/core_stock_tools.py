from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_stock_data(
    symbol: Annotated[str, "Full ticker symbol including exchange suffix, e.g. AAPL, 600973.SS, 0700.HK, 7203.T. NEVER strip the suffix — pass the exact ticker as given."],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve stock price data (OHLCV) for a given ticker symbol.
    Uses the configured core_stock_apis vendor.
    Args:
        symbol (str): Full ticker symbol including any exchange suffix.
            Examples: AAPL (US), 600973.SS (Shanghai A-share), 0700.HK (Hong Kong), 7203.T (Tokyo).
            IMPORTANT: always pass the complete symbol — never truncate or drop the exchange suffix.
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
    Returns:
        str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
    """
    return route_to_vendor("get_stock_data", symbol, start_date, end_date)
