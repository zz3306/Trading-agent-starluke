"""
TradingAgents Web UI — powered by Streamlit + Claude CLI bridge
Run: streamlit run app.py
"""

import os
import re
import threading
from datetime import date, timedelta

import streamlit as st

os.environ.setdefault("PYTHONUTF8", "1")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TradingAgents",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.decision-box {
    padding: 24px 32px;
    border-radius: 12px;
    font-size: 2rem;
    font-weight: 700;
    text-align: center;
    margin-bottom: 24px;
}
.buy    { background: #0d6e3f22; border: 2px solid #0d6e3f; color: #0d6e3f; }
.sell   { background: #8b000022; border: 2px solid #8b0000; color: #8b0000; }
.hold   { background: #7c5c0022; border: 2px solid #b8860b; color: #b8860b; }
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    margin-top: 8px;
    padding: 6px 0;
    border-bottom: 1px solid #e0e0e0;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def detect_signal(text: str) -> str:
    """Return BUY / SELL / HOLD from decision text."""
    upper = text.upper()
    for word in ("STRONG BUY", "OVERWEIGHT", "BUY"):
        if word in upper:
            return "BUY"
    for word in ("STRONG SELL", "UNDERWEIGHT", "SELL"):
        if word in upper:
            return "SELL"
    return "HOLD"


def signal_css(signal: str) -> str:
    return {"BUY": "buy", "SELL": "sell"}.get(signal, "hold")


def signal_emoji(signal: str) -> str:
    return {"BUY": "🟢", "SELL": "🔴"}.get(signal, "🟡")


def run_analysis(ticker, trade_date, analysts, result_holder, quick_model="claude-cli", deep_model="claude-cli"):
    """Run in a background thread; deposit result into result_holder dict."""
    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        config = DEFAULT_CONFIG.copy()
        config["max_debate_rounds"] = 1
        config["max_risk_discuss_rounds"] = 1
        config["selected_analysts"] = analysts
        config["quick_think_llm"] = quick_model
        config["deep_think_llm"] = deep_model

        ta = TradingAgentsGraph(debug=False, config=config)
        final_state, signal = ta.propagate(ticker, str(trade_date))

        # Auto-save to both locations
        from pathlib import Path
        from cli.main import save_report_to_disk
        date_str = str(trade_date)
        for base in [config.get("results_dir_local"), config.get("results_dir")]:
            if base:
                try:
                    save_report_to_disk(final_state, ticker, Path(base) / ticker / date_str)
                except Exception:
                    pass

        result_holder["state"] = final_state
        result_holder["signal"] = signal
        result_holder["error"] = None
    except Exception as e:
        result_holder["error"] = str(e)
        result_holder["state"] = None


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 TradingAgents")
    st.caption("Powered by Claude CLI · Zero API cost")
    st.divider()

    ticker = st.text_input(
        "Stock Ticker",
        value="AAPL",
        placeholder="e.g. NVDA, TSLA, MSFT",
    ).upper().strip()

    trade_date = st.date_input(
        "Analysis Date",
        value=date.today() - timedelta(days=1),
        max_value=date.today(),
    )

    st.markdown("**Analysts to include**")
    use_market = st.checkbox("Market (Technical)", value=True)
    use_news = st.checkbox("News", value=True)
    use_fundamentals = st.checkbox("Fundamentals", value=True)
    use_social = st.checkbox("Social (uses same news data as News analyst)", value=False,
                             help="yfinance 不提供 Reddit/Twitter 数据，Social 分析师实际调用的数据源与 News 相同，选了会增加耗时但不会增加数据维度。")
    use_valuation = st.checkbox("Valuation & Peers", value=True,
                                help="拉取同行公司数据进行估值倍数对比，自动复用 Fundamentals 报告（如已选）避免重复请求。")

    selected_analysts = []
    if use_market:       selected_analysts.append("market")
    if use_news:         selected_analysts.append("news")
    if use_fundamentals: selected_analysts.append("fundamentals")
    if use_valuation:    selected_analysts.append("valuation")
    if use_social:       selected_analysts.append("social")

    st.markdown("**Model selection**")
    from tradingagents.llm_clients.model_catalog import get_model_options
    _quick_opts = get_model_options("claude_cli", "quick")
    _deep_opts  = get_model_options("claude_cli", "deep")
    quick_labels = [label for label, _ in _quick_opts]
    deep_labels  = [label for label, _ in _deep_opts]
    quick_model_label = st.selectbox("Analysts & Trader (quick)", options=quick_labels, index=0)
    deep_model_label  = st.selectbox("Research & Portfolio Mgr (deep)", options=deep_labels, index=0)
    quick_model = dict(_quick_opts)[quick_model_label]
    deep_model  = dict(_deep_opts)[deep_model_label]

    st.divider()
    run_btn = st.button(
        "🚀 Run Analysis",
        use_container_width=True,
        type="primary",
        disabled=not ticker or not selected_analysts,
    )

    if not selected_analysts:
        st.warning("Select at least one analyst.")

    st.divider()
    st.caption("💡 First run takes ~3-5 min depending on analysts selected.")


# ── Main area ──────────────────────────────────────────────────────────────────
st.title(f"Stock Analysis")

if "result" not in st.session_state:
    st.session_state.result = None
if "running" not in st.session_state:
    st.session_state.running = False
if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = None

# Trigger new analysis
if run_btn and not st.session_state.running:
    st.session_state.result = None
    st.session_state.running = True
    st.session_state.last_ticker = ticker
    result_holder = {}
    thread = threading.Thread(
        target=run_analysis,
        args=(ticker, trade_date, selected_analysts, result_holder, quick_model, deep_model),
        daemon=True,
    )
    thread.start()

    # Spinner while waiting
    with st.spinner(f"Analyzing **{ticker}** on {trade_date} … (this takes a few minutes)"):
        thread.join(timeout=1200)

    st.session_state.running = False
    st.session_state.result = result_holder


# ── Display results ────────────────────────────────────────────────────────────
result = st.session_state.result

if result is None:
    st.info("Configure your analysis in the sidebar and click **Run Analysis**.")
    st.markdown("""
    ### How it works
    1. **Analyst agents** pull real market data via yfinance (free)
    2. **Research team** debates bull vs bear case
    3. **Risk team** stress-tests the position sizing
    4. **Portfolio Manager** issues the final verdict

    All LLM calls go through your local `claude` CLI — no API keys needed.
    """)

elif result.get("error"):
    st.error(f"Analysis failed:\n\n```\n{result['error']}\n```")

else:
    state = result["state"]
    decision_text = state.get("final_trade_decision", "")
    signal = detect_signal(decision_text)
    css = signal_css(signal)
    emoji = signal_emoji(signal)

    ticker_label = state.get("company_of_interest", ticker)
    trade_date_label = state.get("trade_date", str(trade_date))

    # ── Decision banner ──────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="decision-box {css}">
        {emoji} {ticker_label} — {signal}
        <div style="font-size:1rem; font-weight:400; margin-top:8px; opacity:0.75;">
            Analysis date: {trade_date_label}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "📋 Final Decision",
        "📊 Trader Plan",
        "🔬 Research Manager",
        "📈 Market Report",
        "📰 News Report",
        "💰 Fundamentals",
        "📉 Valuation & Peers",
        "💬 Sentiment",
        "⚖️ Risk Debate",
    ])

    with tabs[0]:
        st.markdown("### Portfolio Manager Final Decision")
        if decision_text:
            st.markdown(decision_text)
        else:
            st.info("No final decision recorded.")

    with tabs[1]:
        plan = state.get("trader_investment_plan", "")
        st.markdown("### Trader's Investment Plan")
        st.markdown(plan if plan else "_Not available_")

    with tabs[2]:
        inv_plan = state.get("investment_plan", "")
        st.markdown("### Research Manager Verdict")
        st.markdown(inv_plan if inv_plan else "_Not available_")

    with tabs[3]:
        report = state.get("market_report", "")
        st.markdown("### Technical / Market Analysis")
        st.markdown(report if report else "_Market analyst not selected or no report generated._")

    with tabs[4]:
        report = state.get("news_report", "")
        st.markdown("### News & Macro Analysis")
        st.markdown(report if report else "_News analyst not selected or no report generated._")

    with tabs[5]:
        report = state.get("fundamentals_report", "")
        st.markdown("### Fundamentals Analysis")
        st.markdown(report if report else "_Fundamentals analyst not selected or no report generated._")

    with tabs[6]:
        report = state.get("valuation_report", "")
        st.markdown("### Valuation & Peer Comparison")
        st.markdown(report if report else "_Valuation analyst not selected or no report generated._")

    with tabs[7]:
        report = state.get("sentiment_report", "")
        st.markdown("### Social Media Sentiment")
        st.markdown(report if report else "_Sentiment analyst not selected or no report generated._")

    with tabs[8]:
        st.markdown("### Risk Team Debate")
        rds = state.get("risk_debate_state", {})

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**🔴 Aggressive**")
            agg = rds.get("current_aggressive_response", "_Not available_")
            st.markdown(agg[:3000] + ("…" if len(agg) > 3000 else ""))
        with col2:
            st.markdown("**🟡 Neutral**")
            neu = rds.get("current_neutral_response", "_Not available_")
            st.markdown(neu[:3000] + ("…" if len(neu) > 3000 else ""))
        with col3:
            st.markdown("**🟢 Conservative**")
            con = rds.get("current_conservative_response", "_Not available_")
            st.markdown(con[:3000] + ("…" if len(con) > 3000 else ""))

    # ── Divider + re-run hint ─────────────────────────────────────────────
    st.divider()
    st.caption(f"Analysis completed for **{ticker_label}** on {trade_date_label}. Change the ticker or date in the sidebar to run a new analysis.")
