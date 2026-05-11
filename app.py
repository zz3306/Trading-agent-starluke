"""
TradingAgents Web UI — powered by Streamlit + Claude CLI bridge
Run: streamlit run app.py
"""

import base64
import os
import threading
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

os.environ.setdefault("PYTHONUTF8", "1")

_LOGO = Path(__file__).parent / "assets" / "Starluke.png"
_logo_b64 = base64.b64encode(_LOGO.read_bytes()).decode() if _LOGO.exists() else ""

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="STARLUKE",
    page_icon="⭐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme CSS definitions ──────────────────────────────────────────────────────
_COMMON = """
/* shared layout */
.starluke-header {
    display: flex; align-items: center; gap: 12px;
    padding: 12px 0 10px; margin-bottom: 20px;
}
.starluke-header img { height: 52px; }
.starluke-subtitle {
    font-size: 0.82rem; letter-spacing: 3px;
    text-transform: uppercase; margin-top: 3px;
}
.decision-box {
    padding: 26px 36px; border-radius: 12px;
    font-size: 2.1rem; font-weight: 700;
    text-align: center; margin-bottom: 24px; letter-spacing: 1px;
}
[data-testid="stSidebar"] img { display: block; margin: 0 auto; }
[data-testid="stAlert"] { border-radius: 8px !important; border-left-width: 3px !important; }
[data-testid="stDataFrame"] { border-radius: 8px !important; }
"""

DARK_CSS = _COMMON + """
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: #121212 !important; color: #e8e8e8 !important;
}
[data-testid="stSidebar"] {
    background-color: #1a1a1a !important;
    border-right: 1px solid #2a2a2a !important;
}
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
[data-testid="stTextInput"] input, [data-testid="stDateInput"] input {
    background: #1e1e1e !important; border: 1px solid #2a2a2a !important;
    color: #e8e8e8 !important; border-radius: 6px !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #1e1e1e !important; border: 1px solid #2a2a2a !important; color: #e8e8e8 !important;
}
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #00d4ff, #0099cc) !important;
    border: none !important; color: #0a0a0a !important;
    font-weight: 700 !important; border-radius: 8px !important;
    box-shadow: 0 0 14px #00d4ff44 !important;
}
[data-testid="stButton"] button[kind="primary"]:hover { box-shadow: 0 0 28px #00d4ff77 !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #1a1a1a !important; border-bottom: 1px solid #2a2a2a !important; gap: 2px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important; color: #888 !important; font-size: 0.84rem !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: #1e1e1e !important; color: #00d4ff !important;
    border-bottom: 2px solid #00d4ff !important;
}
[data-testid="stExpander"] {
    background: #1e1e1e !important; border: 1px solid #2a2a2a !important; border-radius: 8px !important;
}
[data-testid="stMarkdownContainer"] { color: #d0d0d0 !important; }
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 { color: #00d4ff !important; }
[data-testid="stMarkdownContainer"] th {
    background: #1e1e1e !important; color: #00d4ff !important;
    border: 1px solid #2a2a2a !important; padding: 8px 12px !important;
}
[data-testid="stMarkdownContainer"] td {
    border: 1px solid #2a2a2a !important; padding: 8px 12px !important; color: #d0d0d0 !important;
}
[data-testid="stMarkdownContainer"] tr:nth-child(even) td { background: #1a1a1a !important; }
hr { border-color: #2a2a2a !important; }
[data-testid="stCaptionContainer"] { color: #666 !important; }
[data-testid="stCheckbox"] label { color: #c0c0c0 !important; }
.starluke-subtitle { color: #555; }
.starluke-header { border-bottom: 1px solid #2a2a2a; }
.buy  { background:#00e67611; border:2px solid #00e676; color:#00e676;
        box-shadow:0 0 24px #00e67622, inset 0 0 40px #00e67608; }
.sell { background:#ff174411; border:2px solid #ff1744; color:#ff1744;
        box-shadow:0 0 24px #ff174422, inset 0 0 40px #ff174408; }
.hold { background:#ffb80011; border:2px solid #ffb800; color:#ffb800;
        box-shadow:0 0 24px #ffb80022, inset 0 0 40px #ffb80008; }
"""

LIGHT_CSS = _COMMON + """
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: #f4f6f9 !important; color: #1a1a2e !important;
}
[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e0e4ea !important;
    box-shadow: 2px 0 8px #0001;
}
[data-testid="stSidebar"] * { color: #2a2a3e !important; }
[data-testid="stTextInput"] input, [data-testid="stDateInput"] input {
    background: #ffffff !important; border: 1px solid #d0d4dc !important;
    color: #1a1a2e !important; border-radius: 6px !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #ffffff !important; border: 1px solid #d0d4dc !important; color: #1a1a2e !important;
}
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #0066cc, #004fa3) !important;
    border: none !important; color: #ffffff !important;
    font-weight: 700 !important; border-radius: 8px !important;
    box-shadow: 0 2px 12px #0066cc33 !important;
}
[data-testid="stButton"] button[kind="primary"]:hover { box-shadow: 0 4px 20px #0066cc55 !important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #ffffff !important; border-bottom: 2px solid #e0e4ea !important; gap: 2px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important; color: #8a8fa8 !important; font-size: 0.84rem !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: #f4f6f9 !important; color: #0066cc !important;
    border-bottom: 2px solid #0066cc !important; font-weight: 600 !important;
}
[data-testid="stExpander"] {
    background: #ffffff !important; border: 1px solid #e0e4ea !important;
    border-radius: 8px !important; box-shadow: 0 1px 4px #0001;
}
[data-testid="stMarkdownContainer"] { color: #2a2a3e !important; }
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 { color: #0052a3 !important; }
[data-testid="stMarkdownContainer"] th {
    background: #eaf1fb !important; color: #0052a3 !important;
    border: 1px solid #d0d4dc !important; padding: 8px 12px !important;
}
[data-testid="stMarkdownContainer"] td {
    border: 1px solid #e0e4ea !important; padding: 8px 12px !important; color: #2a2a3e !important;
}
[data-testid="stMarkdownContainer"] tr:nth-child(even) td { background: #f8fafc !important; }
hr { border-color: #e0e4ea !important; }
[data-testid="stCaptionContainer"] { color: #8a8fa8 !important; }
[data-testid="stCheckbox"] label { color: #3a3a5e !important; }
.starluke-subtitle { color: #8a8fa8; }
.starluke-header { border-bottom: 2px solid #e0e4ea; }
.buy  { background:#e6f9f0; border:2px solid #00843d; color:#00843d;
        box-shadow: 0 2px 12px #00843d22; }
.sell { background:#fdecea; border:2px solid #c0392b; color:#c0392b;
        box-shadow: 0 2px 12px #c0392b22; }
.hold { background:#fef8e7; border:2px solid #d4780a; color:#d4780a;
        box-shadow: 0 2px 12px #d4780a22; }
"""

RAINBOW_CSS = _COMMON + """
@keyframes rborder {
  0%  { border-color:#ff3333; box-shadow:0 0 28px #ff333344,inset 0 0 40px #ff333308; }
  25% { border-color:#3366ff; box-shadow:0 0 28px #3366ff44,inset 0 0 40px #3366ff08; }
  50% { border-color:#33cc44; box-shadow:0 0 28px #33cc4444,inset 0 0 40px #33cc4408; }
  75% { border-color:#ffdd00; box-shadow:0 0 28px #ffdd0044,inset 0 0 40px #ffdd0008; }
  100%{ border-color:#ff3333; box-shadow:0 0 28px #ff333344,inset 0 0 40px #ff333308; }
}
@keyframes rbtn {
  0%  { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100%{ background-position: 0% 50%; }
}
@keyframes rglow {
  0%  { filter: drop-shadow(0 0 8px #ff3333aa); }
  25% { filter: drop-shadow(0 0 8px #3366ffaa); }
  50% { filter: drop-shadow(0 0 8px #33cc44aa); }
  75% { filter: drop-shadow(0 0 8px #ffdd00aa); }
  100%{ filter: drop-shadow(0 0 8px #ff3333aa); }
}
@keyframes rtab {
  0%  { border-bottom-color:#ff3333; color:#ff3333; }
  25% { border-bottom-color:#3366ff; color:#3366ff; }
  50% { border-bottom-color:#33cc44; color:#33cc44; }
  75% { border-bottom-color:#ffdd00; color:#ffdd00; }
  100%{ border-bottom-color:#ff3333; color:#ff3333; }
}
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: #090909 !important; color: #efefef !important;
}
[data-testid="stSidebar"] {
    background-color: #0d0d0d !important;
    border-right: 1px solid #1f1f1f !important;
}
[data-testid="stSidebar"] * { color: #e8e8e8 !important; }
[data-testid="stSidebar"] img { animation: rglow 4s ease-in-out infinite; }
[data-testid="stTextInput"] input, [data-testid="stDateInput"] input {
    background: #141414 !important; border: 1px solid #2a2a2a !important;
    color: #efefef !important; border-radius: 6px !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #141414 !important; border: 1px solid #2a2a2a !important; color: #efefef !important;
}
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(270deg,#ff3333,#3366ff,#33cc44,#ffdd00,#ff3333) !important;
    background-size: 300% 300% !important;
    animation: rbtn 4s ease infinite !important;
    border: none !important; color: #050505 !important;
    font-weight: 800 !important; border-radius: 8px !important;
    box-shadow: 0 0 18px #ffffff22 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #0d0d0d !important; border-bottom: 1px solid #1f1f1f !important; gap: 2px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important; color: #666 !important; font-size: 0.84rem !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: #141414 !important;
    animation: rtab 4s linear infinite !important;
    border-bottom-width: 2px !important; border-bottom-style: solid !important;
}
[data-testid="stExpander"] {
    background: #141414 !important; border: 1px solid #222 !important; border-radius: 8px !important;
}
[data-testid="stMarkdownContainer"] { color: #d8d8d8 !important; }
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
    background: linear-gradient(90deg,#ff3333,#3366ff,#33cc44,#ffdd00);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
[data-testid="stMarkdownContainer"] th {
    background: #141414 !important; border: 1px solid #222 !important; padding: 8px 12px !important;
    background: linear-gradient(90deg,#ff333322,#3366ff22,#33cc4422,#ffdd0022) !important;
}
[data-testid="stMarkdownContainer"] td {
    border: 1px solid #1f1f1f !important; padding: 8px 12px !important; color: #d8d8d8 !important;
}
[data-testid="stMarkdownContainer"] tr:nth-child(even) td { background: #0d0d0d !important; }
hr { border-color: #1f1f1f !important; }
[data-testid="stCaptionContainer"] { color: #555 !important; }
[data-testid="stCheckbox"] label { color: #ccc !important; }
.starluke-subtitle { color: #444; }
.starluke-header { border-bottom: 1px solid #1f1f1f; }
.starluke-logo-wrap { animation: rglow 4s ease-in-out infinite; display:inline-block; }
.buy  { background:#0a1a0a; animation: rborder 4s linear infinite; border:2px solid #33cc44; color:#33cc44; }
.sell { background:#1a0a0a; border:2px solid #ff3333; color:#ff3333;
        box-shadow:0 0 28px #ff333344,inset 0 0 40px #ff333308;
        animation: none; }
.hold { background:#1a1600; border:2px solid #ffdd00; color:#ffdd00;
        box-shadow:0 0 28px #ffdd0044,inset 0 0 40px #ffdd0008;
        animation: none; }
"""

_THEME_MAP = {"🌙 Dark": "dark", "☀️ Light": "light", "🌈 Rainbow": "rainbow"}
_CSS_MAP   = {"dark": DARK_CSS, "light": LIGHT_CSS, "rainbow": RAINBOW_CSS}

# ── Session state ──────────────────────────────────────────────────────────────
if "theme"       not in st.session_state: st.session_state.theme       = "dark"
if "result"      not in st.session_state: st.session_state.result      = None
if "running"     not in st.session_state: st.session_state.running     = False
if "last_ticker" not in st.session_state: st.session_state.last_ticker = None

# ── Inject active theme ────────────────────────────────────────────────────────
st.markdown(f"<style>{_CSS_MAP[st.session_state.theme]}</style>", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def detect_signal(text: str) -> str:
    upper = text.upper()
    for word in ("STRONG BUY", "OVERWEIGHT", "BUY"):
        if word in upper: return "BUY"
    for word in ("STRONG SELL", "UNDERWEIGHT", "SELL"):
        if word in upper: return "SELL"
    return "HOLD"

def signal_css(signal: str) -> str:
    return {"BUY": "buy", "SELL": "sell"}.get(signal, "hold")

def signal_emoji(signal: str) -> str:
    return {"BUY": "🟢", "SELL": "🔴"}.get(signal, "🟡")

def _get_reports_dir() -> Path:
    try:
        from tradingagents.default_config import DEFAULT_CONFIG
        local = DEFAULT_CONFIG.get("results_dir_local")
        return Path(local) if local else Path(DEFAULT_CONFIG["results_dir"])
    except Exception:
        return Path("reports")

def _render_browse_reports():
    reports_dir = _get_reports_dir()
    if not reports_dir.exists():
        st.info("No reports saved yet. Run an analysis first.")
        return
    tickers = sorted([p.name for p in reports_dir.iterdir() if p.is_dir() and p.name != "signal_log.csv"])
    if not tickers:
        st.info("No reports saved yet.")
        return
    selected_ticker = st.selectbox("Select ticker", tickers)
    ticker_dir = reports_dir / selected_ticker
    dates = sorted([p.name for p in ticker_dir.iterdir() if p.is_dir()], reverse=True)
    if not dates:
        st.info(f"No dated reports for {selected_ticker}.")
        return
    selected_date = st.selectbox("Select date", dates)
    report_path = ticker_dir / selected_date / "complete_report.md"
    if report_path.exists():
        st.markdown(f"**{selected_ticker} — {selected_date}**")
        st.markdown(report_path.read_text(encoding="utf-8"))
    else:
        st.info("No complete_report.md found. Showing available section files:")
        for md_file in sorted((ticker_dir / selected_date).rglob("*.md")):
            with st.expander(md_file.relative_to(ticker_dir / selected_date).as_posix()):
                st.markdown(md_file.read_text(encoding="utf-8"))

def _render_signal_log():
    import pandas as pd
    reports_dir = _get_reports_dir()
    log_path = reports_dir / "signal_log.csv"
    if not log_path.exists():
        st.info("No signals logged yet.")
        return
    try:
        df = pd.read_csv(log_path)
        if df.empty:
            st.info("Signal log is empty.")
            return
        def color_signal(val):
            if val == "BUY":  return "background-color:#0d6e3f22;color:#0d6e3f;font-weight:bold"
            if val == "SELL": return "background-color:#8b000022;color:#8b0000;font-weight:bold"
            return "color:#b8860b;font-weight:bold"
        styled = df.style.applymap(color_signal, subset=["signal"])
        st.dataframe(styled, use_container_width=True)
        st.caption(f"Total: {len(df)} | BUY: {(df.signal=='BUY').sum()} | SELL: {(df.signal=='SELL').sum()} | HOLD: {(df.signal=='HOLD').sum()}")
    except Exception as e:
        st.error(f"Could not read signal log: {e}")

def run_analysis(ticker, trade_date, analysts, result_holder, quick_model="claude-cli", deep_model="claude-cli"):
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
        from cli.main import save_report_to_disk
        date_str = str(trade_date)
        for base in [config.get("results_dir_local"), config.get("results_dir")]:
            if base:
                try: save_report_to_disk(final_state, ticker, Path(base) / ticker / date_str)
                except Exception: pass
        result_holder["state"] = final_state
        result_holder["signal"] = signal
        result_holder["error"] = None
        try:
            from cli.main import _append_signal_log
            _append_signal_log(config, ticker, str(trade_date), signal)
        except Exception: pass
    except Exception as e:
        result_holder["error"] = str(e)
        result_holder["state"] = None


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo — the rainbow STARLUKE image in all themes
    if _logo_b64:
        st.markdown(
            f'<img src="data:image/png;base64,{_logo_b64}" '
            f'style="width:100%;padding:6px 12px 2px;" alt="STARLUKE">',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("## ⭐ STARLUKE")

    st.caption("Powered by Claude CLI · Zero API cost")

    # ── Theme switcher ────────────────────────────────────────────────────────
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    tc1, tc2, tc3 = st.columns(3)
    for col, (label, key) in zip([tc1, tc2, tc3], _THEME_MAP.items()):
        with col:
            active = st.session_state.theme == key
            if st.button(label, use_container_width=True, disabled=active, key=f"theme_{key}"):
                st.session_state.theme = key
                st.rerun()

    st.divider()

    ticker = st.text_input(
        "Stock Ticker", value="AAPL", placeholder="e.g. NVDA, TSLA, MSFT",
    ).upper().strip()

    trade_date = st.date_input(
        "Analysis Date",
        value=date.today() - timedelta(days=1),
        max_value=date.today(),
    )

    st.markdown("**Analysts to include**")
    use_market       = st.checkbox("Market (Technical)", value=True)
    use_news         = st.checkbox("News", value=True)
    use_fundamentals = st.checkbox("Fundamentals", value=True)
    use_social       = st.checkbox("Social (same data source as News)", value=False,
                                   help="yfinance doesn't provide Reddit/Twitter data; this reuses the news feed.")
    use_valuation    = st.checkbox("Valuation & Peers", value=True,
                                   help="Fetches 3-4 peers for P/E, EV/EBITDA comparison.")
    use_macro        = st.checkbox("Macro (Fed/CPI/Yield Curve)", value=True,
                                   help="Treasury yields, VIX, dollar index. Cached 7 days.")

    selected_analysts = []
    if use_market:       selected_analysts.append("market")
    if use_news:         selected_analysts.append("news")
    if use_fundamentals: selected_analysts.append("fundamentals")
    if use_valuation:    selected_analysts.append("valuation")
    if use_macro:        selected_analysts.append("macro")
    if use_social:       selected_analysts.append("social")

    st.markdown("**Model selection**")
    from tradingagents.llm_clients.model_catalog import get_model_options
    _quick_opts   = get_model_options("claude_cli", "quick")
    _deep_opts    = get_model_options("claude_cli", "deep")
    quick_labels  = [label for label, _ in _quick_opts]
    deep_labels   = [label for label, _ in _deep_opts]
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
    st.caption("💡 First run ~3-5 min depending on analysts.")


# ── Main area: logo header ─────────────────────────────────────────────────────
if _logo_b64:
    wrap = "starluke-logo-wrap" if st.session_state.theme == "rainbow" else ""
    st.markdown(f"""
    <div class="starluke-header">
        <span class="{wrap}">
            <img src="data:image/png;base64,{_logo_b64}" alt="STARLUKE" />
        </span>
        <div class="starluke-subtitle">Multi-Agent Stock Analysis</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("## ⭐ STARLUKE — Stock Analysis")

# ── Session result state ───────────────────────────────────────────────────────
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
    with st.spinner(f"Analyzing **{ticker}** on {trade_date} … (a few minutes)"):
        thread.join(timeout=1200)
    st.session_state.running = False
    st.session_state.result = result_holder


# ── Display results ────────────────────────────────────────────────────────────
result = st.session_state.result

if result is None:
    main_tabs = st.tabs(["🚀 New Analysis", "📂 Browse Reports", "📊 Signal Log"])
    with main_tabs[0]:
        st.info("Configure your analysis in the sidebar and click **Run Analysis**.")
        st.markdown("""
### How it works
1. **Analyst agents** pull real market data via yfinance (free)
2. **Research team** debates bull vs bear case
3. **Risk team** stress-tests the position sizing
4. **Portfolio Manager** issues the final verdict

All LLM calls go through your local `claude` CLI — no API keys needed.
        """)
    with main_tabs[1]: _render_browse_reports()
    with main_tabs[2]: _render_signal_log()

elif result.get("error"):
    st.error(f"Analysis failed:\n\n```\n{result['error']}\n```")

else:
    state = result["state"]
    decision_text = state.get("final_trade_decision", "")
    signal = detect_signal(decision_text)
    css    = signal_css(signal)
    emoji  = signal_emoji(signal)
    ticker_label     = state.get("company_of_interest", ticker)
    trade_date_label = state.get("trade_date", str(trade_date))

    st.markdown(f"""
    <div class="decision-box {css}">
        {emoji} {ticker_label} — {signal}
        <div style="font-size:1rem;font-weight:400;margin-top:8px;opacity:0.75;">
            Analysis date: {trade_date_label}
        </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "📋 Final Decision", "📊 Trader Plan", "🔬 Research Manager",
        "📈 Market", "📰 News", "💰 Fundamentals", "📉 Valuation",
        "🌍 Macro", "💬 Sentiment", "⚖️ Risk Debate", "📂 Browse", "📊 Signal Log",
    ])

    with tabs[0]:
        st.markdown("### Portfolio Manager Final Decision")
        st.markdown(decision_text if decision_text else "_No final decision recorded._")
    with tabs[1]:
        st.markdown("### Trader's Investment Plan")
        plan = state.get("trader_investment_plan", "")
        st.markdown(plan if plan else "_Not available_")
    with tabs[2]:
        st.markdown("### Research Manager Verdict")
        st.markdown(state.get("investment_plan", "") or "_Not available_")
    with tabs[3]:
        st.markdown("### Technical / Market Analysis")
        st.markdown(state.get("market_report", "") or "_Market analyst not selected._")
    with tabs[4]:
        st.markdown("### News Analysis")
        st.markdown(state.get("news_report", "") or "_News analyst not selected._")
    with tabs[5]:
        st.markdown("### Fundamentals Analysis")
        st.markdown(state.get("fundamentals_report", "") or "_Fundamentals analyst not selected._")
    with tabs[6]:
        st.markdown("### Valuation & Peer Comparison")
        st.markdown(state.get("valuation_report", "") or "_Valuation analyst not selected._")
    with tabs[7]:
        st.markdown("### Macro Environment")
        st.markdown(state.get("macro_report", "") or "_Macro analyst not selected._")
    with tabs[8]:
        st.markdown("### Social Media Sentiment")
        st.markdown(state.get("sentiment_report", "") or "_Sentiment analyst not selected._")
    with tabs[9]:
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
    with tabs[10]: _render_browse_reports()
    with tabs[11]: _render_signal_log()

    st.divider()
    st.caption(f"Analysis completed for **{ticker_label}** on {trade_date_label}. Change ticker/date in sidebar to run again.")
