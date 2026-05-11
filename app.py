"""
STARLUKE Web UI — powered by Streamlit + streamlit-antd-components
Run: streamlit run app.py
"""

import base64
import os
import threading
from datetime import date, timedelta
from pathlib import Path

import streamlit as st
import streamlit_antd_components as sac

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

# ── Theme CSS ──────────────────────────────────────────────────────────────────
_COMMON_CSS = """
.logo-wrap { padding: 20px 16px 12px; border-bottom: 1px solid var(--sl-border); margin-bottom: 4px; }
.logo-wrap img { width: 100%; max-width: 260px; display: block; margin: 0 auto; }
.logo-sub { text-align:center; font-size:10px; letter-spacing:3px; text-transform:uppercase; margin-top:6px; color: var(--sl-muted); }
.sig-banner { border-radius:10px; padding:22px 32px; font-size:2rem; font-weight:700; text-align:center; margin-bottom:20px; letter-spacing:1px; }
.sig-sub { font-size:0.9rem; font-weight:400; opacity:0.65; margin-top:6px; }
.main-header { display:flex; align-items:center; gap:14px; padding:18px 0 14px; border-bottom:1px solid var(--sl-border); margin-bottom:20px; }
.main-header img { height:60px; }
.main-header-sub { font-size:10px; letter-spacing:3px; text-transform:uppercase; color: var(--sl-muted); }
[data-testid="stMarkdownContainer"] table { border-collapse:collapse !important; width:100% !important; }
[data-testid="stMarkdownContainer"] th { border:1px solid var(--sl-border) !important; padding:8px 12px !important; }
[data-testid="stMarkdownContainer"] td { border:1px solid var(--sl-border) !important; padding:8px 12px !important; }
[data-testid="stAlert"] { border-radius:8px !important; }
[data-testid="stDataFrame"] { border-radius:8px !important; }
"""

DARK_CSS = _COMMON_CSS + """
:root { --sl-border:#222; --sl-muted:#555; }
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]
    { background-color:#0f0f0f !important; color:#e8e8e8 !important; }
[data-testid="stSidebar"] { background-color:#141414 !important; border-right:1px solid #222 !important; padding-top:0 !important; }
[data-testid="stTextInput"] input,[data-testid="stDateInput"] input
    { background:#1a1a1a !important; border:1px solid #2a2a2a !important; color:#e8e8e8 !important; border-radius:6px !important; }
[data-testid="stSelectbox"]>div>div { background:#1a1a1a !important; border:1px solid #2a2a2a !important; color:#e8e8e8 !important; }
[data-testid="stButton"] button[kind="primary"]
    { background:linear-gradient(135deg,#36cfc9,#0d9e99) !important; border:none !important; color:#050505 !important;
      font-weight:700 !important; border-radius:8px !important; box-shadow:0 0 16px #36cfc944 !important; }
[data-testid="stButton"] button[kind="primary"]:hover { box-shadow:0 0 28px #36cfc966 !important; }
[data-testid="stMarkdownContainer"] { color:#ccc !important; }
[data-testid="stMarkdownContainer"] h1,[data-testid="stMarkdownContainer"] h2,[data-testid="stMarkdownContainer"] h3 { color:#36cfc9 !important; }
[data-testid="stMarkdownContainer"] th { background:#1a1a1a !important; color:#36cfc9 !important; }
[data-testid="stMarkdownContainer"] tr:nth-child(even) td { background:#161616 !important; }
[data-testid="stCheckbox"] label { color:#aaa !important; }
[data-testid="stCaptionContainer"] { color:#555 !important; }
hr { border-color:#222 !important; }
.sig-buy  { background:#00e67608; border:2px solid #00e676; color:#00e676; box-shadow:0 0 28px #00e67618; }
.sig-sell { background:#ff174408; border:2px solid #ff1744; color:#ff1744; box-shadow:0 0 28px #ff174418; }
.sig-hold { background:#ffb80008; border:2px solid #ffb800; color:#ffb800; box-shadow:0 0 28px #ffb80018; }
"""

LIGHT_CSS = _COMMON_CSS + """
:root { --sl-border:#e0e4ea; --sl-muted:#8a8fa8; }
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]
    { background-color:#f4f6f9 !important; color:#1a1a2e !important; }
[data-testid="stSidebar"] { background-color:#ffffff !important; border-right:1px solid #e0e4ea !important; padding-top:0 !important; box-shadow:2px 0 8px #0001; }
[data-testid="stSidebar"] * { color:#2a2a3e !important; }
[data-testid="stTextInput"] input,[data-testid="stDateInput"] input
    { background:#fff !important; border:1px solid #d0d4dc !important; color:#1a1a2e !important; border-radius:6px !important; }
[data-testid="stSelectbox"]>div>div { background:#fff !important; border:1px solid #d0d4dc !important; color:#1a1a2e !important; }
[data-testid="stButton"] button[kind="primary"]
    { background:linear-gradient(135deg,#0066cc,#004fa3) !important; border:none !important; color:#fff !important;
      font-weight:700 !important; border-radius:8px !important; box-shadow:0 2px 12px #0066cc33 !important; }
[data-testid="stButton"] button[kind="primary"]:hover { box-shadow:0 4px 20px #0066cc55 !important; }
[data-testid="stMarkdownContainer"] { color:#2a2a3e !important; }
[data-testid="stMarkdownContainer"] h1,[data-testid="stMarkdownContainer"] h2,[data-testid="stMarkdownContainer"] h3 { color:#0052a3 !important; }
[data-testid="stMarkdownContainer"] th { background:#eaf1fb !important; color:#0052a3 !important; }
[data-testid="stMarkdownContainer"] tr:nth-child(even) td { background:#f8fafc !important; }
[data-testid="stCheckbox"] label { color:#3a3a5e !important; }
[data-testid="stCaptionContainer"] { color:#8a8fa8 !important; }
hr { border-color:#e0e4ea !important; }
.sig-buy  { background:#e6f9f0; border:2px solid #00843d; color:#00843d; box-shadow:0 2px 12px #00843d22; }
.sig-sell { background:#fdecea; border:2px solid #c0392b; color:#c0392b; box-shadow:0 2px 12px #c0392b22; }
.sig-hold { background:#fef8e7; border:2px solid #d4780a; color:#d4780a; box-shadow:0 2px 12px #d4780a22; }
"""

RAINBOW_CSS = _COMMON_CSS + """
:root { --sl-border:#1f1f1f; --sl-muted:#444; }
@keyframes rbtn { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
@keyframes rglow { 0%{filter:drop-shadow(0 0 8px #ff3333aa)} 25%{filter:drop-shadow(0 0 8px #3366ffaa)}
  50%{filter:drop-shadow(0 0 8px #33cc44aa)} 75%{filter:drop-shadow(0 0 8px #ffdd00aa)} 100%{filter:drop-shadow(0 0 8px #ff3333aa)} }
@keyframes rborder { 0%{border-color:#ff3333;box-shadow:0 0 28px #ff333430}
  25%{border-color:#3366ff;box-shadow:0 0 28px #3366ff30} 50%{border-color:#33cc44;box-shadow:0 0 28px #33cc4430}
  75%{border-color:#ffdd00;box-shadow:0 0 28px #ffdd0030} 100%{border-color:#ff3333;box-shadow:0 0 28px #ff333430} }
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]
    { background-color:#090909 !important; color:#efefef !important; }
[data-testid="stSidebar"] { background-color:#0d0d0d !important; border-right:1px solid #1f1f1f !important; padding-top:0 !important; }
[data-testid="stSidebar"] img { animation:rglow 4s ease-in-out infinite; }
[data-testid="stTextInput"] input,[data-testid="stDateInput"] input
    { background:#141414 !important; border:1px solid #2a2a2a !important; color:#efefef !important; border-radius:6px !important; }
[data-testid="stSelectbox"]>div>div { background:#141414 !important; border:1px solid #2a2a2a !important; color:#efefef !important; }
[data-testid="stButton"] button[kind="primary"]
    { background:linear-gradient(270deg,#ff3333,#3366ff,#33cc44,#ffdd00,#ff3333) !important;
      background-size:300% 300% !important; animation:rbtn 4s ease infinite !important;
      border:none !important; color:#050505 !important; font-weight:800 !important; border-radius:8px !important; }
[data-testid="stMarkdownContainer"] { color:#d8d8d8 !important; }
[data-testid="stMarkdownContainer"] h1,[data-testid="stMarkdownContainer"] h2,[data-testid="stMarkdownContainer"] h3
    { background:linear-gradient(90deg,#ff3333,#3366ff,#33cc44,#ffdd00);
      -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
[data-testid="stMarkdownContainer"] th { background:#141414 !important; }
[data-testid="stMarkdownContainer"] tr:nth-child(even) td { background:#0d0d0d !important; }
[data-testid="stCheckbox"] label { color:#ccc !important; }
[data-testid="stCaptionContainer"] { color:#555 !important; }
hr { border-color:#1f1f1f !important; }
.sig-buy  { background:#0a1a0a; border:2px solid #33cc44; color:#33cc44; animation:rborder 4s linear infinite; }
.sig-sell { background:#1a0a0a; border:2px solid #ff3333; color:#ff3333; box-shadow:0 0 28px #ff333430; }
.sig-hold { background:#1a1600; border:2px solid #ffdd00; color:#ffdd00; box-shadow:0 0 28px #ffdd0030; }
"""

# ── Session state ──────────────────────────────────────────────────────────────
if "theme"    not in st.session_state: st.session_state.theme    = "dark"
if "result"   not in st.session_state: st.session_state.result   = None
if "running"  not in st.session_state: st.session_state.running  = False
if "nav"      not in st.session_state: st.session_state.nav      = "New Analysis"
if "username" not in st.session_state: st.session_state.username = ""

# Inject active theme
_css_map = {"dark": DARK_CSS, "light": LIGHT_CSS, "rainbow": RAINBOW_CSS}
st.markdown(f"<style>{_css_map[st.session_state.theme]}</style>", unsafe_allow_html=True)

# ── Welcome screen ─────────────────────────────────────────────────────────────
if not st.session_state.username:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    .welcome-wrap {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; min-height: 80vh; gap: 24px;
    }
    .welcome-wrap img { width: 340px; margin-bottom: 8px; }
    .welcome-title {
        font-size: 1.1rem; color: #888;
        letter-spacing: 4px; text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown('<div class="welcome-wrap">', unsafe_allow_html=True)
        if _logo_b64:
            st.markdown(
                f'<img src="data:image/png;base64,{_logo_b64}" '
                f'style="width:320px;display:block;margin:0 auto 8px;">',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div class="welcome-title">Multi-Agent Stock Analysis</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        name_input = st.text_input(
            "What's your name?", placeholder="Enter your name…",
            label_visibility="visible",
        )
        if st.button("Enter →", use_container_width=True, type="primary"):
            if name_input.strip():
                st.session_state.username = name_input.strip()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()




# ── Helpers ────────────────────────────────────────────────────────────────────
def detect_signal(text: str) -> str:
    upper = text.upper()
    for w in ("STRONG BUY", "OVERWEIGHT", "BUY"):
        if w in upper: return "BUY"
    for w in ("STRONG SELL", "UNDERWEIGHT", "SELL"):
        if w in upper: return "SELL"
    return "HOLD"

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
    tickers = sorted([p.name for p in reports_dir.iterdir()
                      if p.is_dir() and p.name != "signal_log.csv"])
    if not tickers:
        st.info("No reports saved yet.")
        return
    selected_ticker = st.selectbox("Ticker", tickers)
    ticker_dir = reports_dir / selected_ticker
    dates = sorted([p.name for p in ticker_dir.iterdir() if p.is_dir()], reverse=True)
    if not dates:
        st.info(f"No reports for {selected_ticker}.")
        return
    selected_date = st.selectbox("Date", dates)
    report_path = ticker_dir / selected_date / "complete_report.md"
    if report_path.exists():
        st.markdown(f"**{selected_ticker} — {selected_date}**")
        st.markdown(report_path.read_text(encoding="utf-8"))
    else:
        for md_file in sorted((ticker_dir / selected_date).rglob("*.md")):
            with st.expander(md_file.relative_to(ticker_dir / selected_date).as_posix()):
                st.markdown(md_file.read_text(encoding="utf-8"))

def _render_signal_log():
    import pandas as pd
    log_path = _get_reports_dir() / "signal_log.csv"
    if not log_path.exists():
        st.info("No signals logged yet. Signal log is created after your first analysis.")
        return
    try:
        df = pd.read_csv(log_path)
        if df.empty:
            st.info("Signal log is empty.")
            return
        def color_signal(val):
            if val == "BUY":  return "color:#00e676;font-weight:bold"
            if val == "SELL": return "color:#ff1744;font-weight:bold"
            return "color:#ffb800;font-weight:bold"
        st.dataframe(df.style.applymap(color_signal, subset=["signal"]),
                     use_container_width=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total",  len(df))
        c2.metric("BUY",  int((df.signal == "BUY").sum()))
        c3.metric("SELL", int((df.signal == "SELL").sum()))
        c4.metric("HOLD", int((df.signal == "HOLD").sum()))
    except Exception as e:
        st.error(f"Could not read signal log: {e}")

def run_analysis(ticker, trade_date, analysts, result_holder,
                 quick_model="claude-cli", deep_model="claude-cli"):
    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG.copy()
        config.update({"max_debate_rounds": 1, "max_risk_discuss_rounds": 1,
                        "selected_analysts": analysts,
                        "quick_think_llm": quick_model, "deep_think_llm": deep_model})
        ta = TradingAgentsGraph(debug=False, config=config)
        final_state, signal = ta.propagate(ticker, str(trade_date))
        from cli.main import save_report_to_disk
        for base in [config.get("results_dir_local"), config.get("results_dir")]:
            if base:
                try: save_report_to_disk(final_state, ticker,
                                         Path(base) / ticker / str(trade_date))
                except Exception: pass
        result_holder.update({"state": final_state, "signal": signal, "error": None})
        try:
            from cli.main import _append_signal_log
            _append_signal_log(config, ticker, str(trade_date), signal)
        except Exception: pass
    except Exception as e:
        result_holder.update({"error": str(e), "state": None})


# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo
    if _logo_b64:
        st.markdown(f"""
        <div class="logo-wrap">
            <img src="data:image/png;base64,{_logo_b64}" alt="STARLUKE">
            <div class="logo-sub">Powered by Claude CLI</div>
        </div>
        """, unsafe_allow_html=True)

    # Greeting
    st.markdown(
        f"<div style='text-align:center;font-size:0.85rem;color:#888;"
        f"padding:6px 0 10px;'>👋 Hi, <b>{st.session_state.username}</b>!</div>",
        unsafe_allow_html=True,
    )

    # Theme switcher
    theme_choice = sac.segmented(
        items=[
            sac.SegmentedItem(label="🌙 Dark"),
            sac.SegmentedItem(label="☀️ Light"),
            sac.SegmentedItem(label="🌈 Rainbow"),
        ],
        label=None, size="xs", color="#36cfc9", use_container_width=True,
        index={"dark": 0, "light": 1, "rainbow": 2}[st.session_state.theme],
    )
    _label_map = {"🌙 Dark": "dark", "☀️ Light": "light", "🌈 Rainbow": "rainbow"}
    if theme_choice and _label_map.get(theme_choice, st.session_state.theme) != st.session_state.theme:
        st.session_state.theme = _label_map[theme_choice]
        st.rerun()

    # Navigation menu
    nav = sac.menu([
        sac.MenuItem("New Analysis",   icon="rocket-takeoff"),
        sac.MenuItem("Browse Reports", icon="folder2-open"),
        sac.MenuItem("Signal Log",     icon="bar-chart-line"),
    ], color="#36cfc9", size="sm", indent=16, open_all=True)
    if nav: st.session_state.nav = nav

    sac.divider(label="Configuration", align="center", color="#333")

    ticker = st.text_input(
        "Stock Ticker", value="AAPL", placeholder="e.g. NVDA, TSLA, 0700.HK"
    ).upper().strip()

    trade_date = st.date_input(
        "Analysis Date",
        value=date.today() - timedelta(days=1),
        max_value=date.today(),
    )

    sac.divider(label="Analysts", align="center", color="#333")

    use_market       = st.checkbox("Market (Technical)",      value=True)
    use_news         = st.checkbox("News",                    value=True)
    use_fundamentals = st.checkbox("Fundamentals",            value=True)
    use_valuation    = st.checkbox("Valuation & Peers",       value=True,
                                   help="Peer P/E, EV/EBITDA comparison")
    use_macro        = st.checkbox("Macro (Fed/CPI/Yield)",   value=True,
                                   help="Cached 7 days — very fast on repeats")
    use_social       = st.checkbox("Social (= News data)",    value=False,
                                   help="yfinance doesn't have Reddit/Twitter data")

    selected_analysts = (
        (["market"]       if use_market       else []) +
        (["news"]         if use_news         else []) +
        (["fundamentals"] if use_fundamentals else []) +
        (["valuation"]    if use_valuation    else []) +
        (["macro"]        if use_macro        else []) +
        (["social"]       if use_social       else [])
    )

    sac.divider(label="Model", align="center", color="#333")

    from tradingagents.llm_clients.model_catalog import get_model_options
    _qopts = get_model_options("claude_cli", "quick")
    _dopts = get_model_options("claude_cli", "deep")
    quick_model = dict(_qopts)[st.selectbox("Quick (analysts)", [l for l,_ in _qopts], index=0)]
    deep_model  = dict(_dopts)[st.selectbox("Deep (PM & research)", [l for l,_ in _dopts], index=0)]

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    run_btn = st.button(
        "🚀  Run Analysis", use_container_width=True, type="primary",
        disabled=not ticker or not selected_analysts,
    )
    if not selected_analysts:
        st.warning("Select at least one analyst.")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.caption("💡 First run ~3–5 min · Results auto-saved to reports/")


# ── MAIN AREA ──────────────────────────────────────────────────────────────────
# Header
if _logo_b64:
    st.markdown(f"""
    <div class="main-header">
        <img src="data:image/png;base64,{_logo_b64}" alt="STARLUKE">
        <div class="main-header-sub">Multi-Agent Stock Analysis</div>
    </div>
    """, unsafe_allow_html=True)

# Run analysis
if run_btn and not st.session_state.running:
    st.session_state.result  = None
    st.session_state.running = True
    st.session_state.nav     = "New Analysis"
    result_holder = {}
    thread = threading.Thread(
        target=run_analysis,
        args=(ticker, trade_date, selected_analysts, result_holder, quick_model, deep_model),
        daemon=True,
    )
    thread.start()
    with st.spinner(f"Analyzing **{ticker}** on {trade_date}… (a few minutes)"):
        thread.join(timeout=1200)
    st.session_state.running = False
    st.session_state.result  = result_holder

# ── Page routing ───────────────────────────────────────────────────────────────
page = st.session_state.nav

if page == "Browse Reports":
    st.markdown("### 📂 Browse Reports")
    _render_browse_reports()

elif page == "Signal Log":
    st.markdown("### 📊 Signal Log")
    _render_signal_log()

else:
    # ── New Analysis page ──────────────────────────────────────────────────────
    result = st.session_state.result

    if result is None:
        # Landing
        st.info("Configure your analysis in the sidebar and click **Run Analysis**.")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
#### How it works
1. **Analyst agents** pull real market data (yfinance, free)
2. **Bull & Bear researchers** debate the investment thesis
3. **Trader** converts research into a trade proposal
4. **Risk team** stress-tests position sizing
5. **Portfolio Manager** issues the final BUY / HOLD / SELL
            """)
        with col2:
            st.markdown("""
#### Agent pipeline
```
Market  ┐
News    ├─→ Bull/Bear → Research Mgr
Fund.   │         ↓
Macro   ┘       Trader
                  ↓
         Aggressive / Neutral / Conservative
                  ↓
           Portfolio Manager → VERDICT
```
            """)

    elif result.get("error"):
        st.error(f"Analysis failed: {result['error']}")

    else:
        state  = result["state"]
        signal = detect_signal(state.get("final_trade_decision", ""))
        ticker_label = state.get("company_of_interest", ticker)
        date_label   = state.get("trade_date", str(trade_date))

        sig_cls = {"BUY": "sig-buy", "SELL": "sig-sell"}.get(signal, "sig-hold")
        sig_ico = {"BUY": "🟢", "SELL": "🔴"}.get(signal, "🟡")

        st.markdown(f"""
        <div class="sig-banner {sig_cls}">
            {sig_ico}&nbsp; {ticker_label} — {signal}
            <div class="sig-sub">Analysis date: {date_label}</div>
        </div>
        """, unsafe_allow_html=True)

        # Results tabs
        tab = sac.tabs([
            sac.TabsItem("Final Decision",    icon="clipboard-check"),
            sac.TabsItem("Trader Plan",       icon="graph-up-arrow"),
            sac.TabsItem("Research Manager",  icon="people"),
            sac.TabsItem("Market",            icon="bar-chart"),
            sac.TabsItem("News",              icon="newspaper"),
            sac.TabsItem("Fundamentals",      icon="building"),
            sac.TabsItem("Valuation",         icon="calculator"),
            sac.TabsItem("Macro",             icon="globe"),
            sac.TabsItem("Sentiment",         icon="chat-square-text"),
            sac.TabsItem("Risk Debate",       icon="shield-exclamation"),
        ], color="#36cfc9", size="sm", align="start")

        def show(key, fallback="_Not available_"):
            txt = state.get(key, "")
            st.markdown(txt if txt else fallback)

        if tab == "Final Decision":
            show("final_trade_decision", "_No final decision recorded._")

        elif tab == "Trader Plan":
            show("trader_investment_plan")

        elif tab == "Research Manager":
            show("investment_plan")

        elif tab == "Market":
            show("market_report", "_Market analyst not selected._")

        elif tab == "News":
            show("news_report", "_News analyst not selected._")

        elif tab == "Fundamentals":
            show("fundamentals_report", "_Fundamentals analyst not selected._")

        elif tab == "Valuation":
            show("valuation_report", "_Valuation analyst not selected._")

        elif tab == "Macro":
            show("macro_report", "_Macro analyst not selected._")

        elif tab == "Sentiment":
            show("sentiment_report", "_Sentiment analyst not selected._")

        elif tab == "Risk Debate":
            rds = state.get("risk_debate_state", {})
            c1, c2, c3 = st.columns(3)
            with c1:
                sac.divider(label="🔴 Aggressive", color="#ff1744")
                agg = rds.get("current_aggressive_response", "_Not available_")
                st.markdown(agg[:3000] + ("…" if len(agg) > 3000 else ""))
            with c2:
                sac.divider(label="🟡 Neutral", color="#ffb800")
                neu = rds.get("current_neutral_response", "_Not available_")
                st.markdown(neu[:3000] + ("…" if len(neu) > 3000 else ""))
            with c3:
                sac.divider(label="🟢 Conservative", color="#00e676")
                con = rds.get("current_conservative_response", "_Not available_")
                st.markdown(con[:3000] + ("…" if len(con) > 3000 else ""))

        st.divider()
        st.caption(f"Completed: **{ticker_label}** · {date_label} · Change ticker/date in sidebar to rerun.")
