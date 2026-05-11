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

def _img_b64(name: str) -> str:
    p = Path(__file__).parent / "assets" / name
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""

_logo_b64   = _img_b64("Starluke.png")
_bg_b64     = _img_b64("Cominc3.png")
_illus_b64  = _img_b64("1.png")

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
if "theme"         not in st.session_state: st.session_state.theme         = "dark"
if "result"        not in st.session_state: st.session_state.result        = None
if "running"       not in st.session_state: st.session_state.running       = False
if "nav"           not in st.session_state: st.session_state.nav           = "New Analysis"
if "username"      not in st.session_state: st.session_state.username      = ""
if "saas_results"  not in st.session_state: st.session_state.saas_results  = None
if "saas_running"  not in st.session_state: st.session_state.saas_running  = False

# Inject active theme
_css_map = {"dark": DARK_CSS, "light": LIGHT_CSS, "rainbow": RAINBOW_CSS}
st.markdown(f"<style>{_css_map[st.session_state.theme]}</style>", unsafe_allow_html=True)

# Background image (Cominc3.png) with per-theme overlay
if _bg_b64:
    _bg_opacity = {"dark": "0.13", "light": "0.10", "rainbow": "0.11"}[st.session_state.theme]
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: fixed;
        inset: 0;
        background-image: url("data:image/png;base64,{_bg_b64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        opacity: {_bg_opacity};
        pointer-events: none;
        z-index: 0;
    }}
    [data-testid="stMain"] > div {{ position: relative; z-index: 1; }}
    </style>
    """, unsafe_allow_html=True)

# ── Welcome screen ─────────────────────────────────────────────────────────────
if not st.session_state.username:
    _bg_url = f'url("data:image/png;base64,{_bg_b64}")' if _bg_b64 else "none"
    st.markdown(f"""
    <style>
    [data-testid="stSidebar"] {{ display: none !important; }}

    /* background fills full viewport at high opacity */
    html, body, [data-testid="stAppViewContainer"] {{
        background-image: {_bg_url} !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
        min-height: 100vh !important;
    }}

    /* thin dark vignette — just enough for readability */
    [data-testid="stAppViewContainer"]::after {{
        content: "";
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.35);
        pointer-events: none;
        z-index: 0;
    }}

    /* strip Streamlit's own background */
    [data-testid="stMain"],
    [data-testid="stMain"] > div {{
        background: transparent !important;
    }}

    /* center the card */
    [data-testid="block-container"] {{
        padding-top: 10vh !important;
        max-width: 500px !important;
        position: relative;
        z-index: 1;
    }}

    /* frosted glass card */
    [data-testid="block-container"] > div:first-child {{
        background: rgba(8, 12, 20, 0.55) !important;
        border: 1px solid rgba(255,255,255,0.13) !important;
        border-radius: 20px !important;
        padding: 36px 40px 32px !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        box-shadow: 0 8px 48px rgba(0,0,0,0.5) !important;
    }}

    .wc-logo {{
        display: block;
        width: 100%;
        max-width: 460px;
        margin: 0 auto 6px;
        filter: drop-shadow(0 0 32px #36cfc977);
    }}
    .wc-sub {{
        text-align: center;
        font-size: 0.7rem;
        letter-spacing: 5px;
        text-transform: uppercase;
        color: #ccc;
        margin-bottom: 28px;
    }}
    </style>
    """, unsafe_allow_html=True)

    if _logo_b64:
        st.markdown(
            f'<img class="wc-logo" src="data:image/png;base64,{_logo_b64}" alt="STARLUKE">',
            unsafe_allow_html=True,
        )
    st.markdown('<div class="wc-sub">Multi-Agent Stock Analysis</div>', unsafe_allow_html=True)
    name_input = st.text_input("What's your name?", placeholder="Enter your name…", label_visibility="visible")
    if st.button("Enter →", use_container_width=True, type="primary"):
        if name_input.strip():
            st.session_state.username = name_input.strip()
            st.rerun()
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

_SECTIONS = [
    ("I · Analysts",  "1_analysts",  "bar-chart", [
        ("market",       "📈 Market"),
        ("news",         "📰 News"),
        ("fundamentals", "🏢 Fundamentals"),
        ("valuation",    "🔢 Valuation"),
        ("macro",        "🌐 Macro"),
        ("sentiment",    "💬 Sentiment"),
        ("options",      "💵 Options"),
    ]),
    ("II · Research", "2_research",  "people", [
        ("bull",    "🟢 Bull"),
        ("bear",    "🔴 Bear"),
        ("manager", "👔 Research Mgr"),
    ]),
    ("III · Trading", "3_trading",   "graph-up-arrow", [
        ("trader",  "🤝 Trader"),
    ]),
    ("IV · Risk",     "4_risk",      "shield-exclamation", [
        ("aggressive",   "🔴 Aggressive"),
        ("conservative", "🟢 Conservative"),
        ("neutral",      "🟡 Neutral"),
    ]),
    ("V · Portfolio", "5_portfolio", "clipboard-check", [
        ("decision", "🏆 Final Decision"),
    ]),
]


def _read_signal_from_folder(base: Path) -> str:
    """Extract BUY/HOLD/SELL from saved portfolio decision file."""
    dec = base / "5_portfolio" / "decision.md"
    if not dec.exists():
        return "—"
    txt = dec.read_text(encoding="utf-8").upper()
    for w in ("STRONG BUY", "BUY"):
        if w in txt: return "🟢 BUY"
    for w in ("STRONG SELL", "SELL"):
        if w in txt: return "🔴 SELL"
    return "🟡 HOLD"


def _render_browse_reports():
    import shutil
    reports_dir = _get_reports_dir()
    if not reports_dir.exists():
        st.info("No reports saved yet. Run an analysis first.")
        return
    tickers = sorted([p.name for p in reports_dir.iterdir()
                      if p.is_dir() and p.name not in ("signal_log.csv", "saas_finder")])
    if not tickers:
        st.info("No reports saved yet.")
        return

    # ── Mode selector ──────────────────────────────────────────────────────────
    mode = sac.segmented(
        items=[sac.SegmentedItem(label="📄 View Report"),
               sac.SegmentedItem(label="📊 Compare Dates"),
               sac.SegmentedItem(label="🗑️ Delete")],
        label=None, size="xs", color="#36cfc9",
    )

    # ══════════════════════════════════════════════════════════════════════════
    if mode == "🗑️ Delete":
        st.warning("Select a report to permanently delete it.")
        c1, c2 = st.columns([1, 1])
        with c1:
            del_ticker = st.selectbox("Ticker", tickers, key="del_tick")
        ticker_dir = reports_dir / del_ticker
        dates = sorted([p.name for p in ticker_dir.iterdir() if p.is_dir()], reverse=True)
        if not dates:
            st.info("No reports for this ticker.")
            return
        with c2:
            del_date = st.selectbox("Date", dates, key="del_date")
        target = ticker_dir / del_date
        st.markdown(f"**Will delete:** `{target}`")
        if st.button("🗑️ Confirm Delete", type="primary"):
            shutil.rmtree(target, ignore_errors=True)
            # remove ticker folder too if now empty
            remaining = [p for p in ticker_dir.iterdir() if p.is_dir()]
            if not remaining:
                ticker_dir.rmdir()
            st.success(f"Deleted {del_ticker} / {del_date}")
            st.rerun()
        return

    # ══════════════════════════════════════════════════════════════════════════
    if mode == "📊 Compare Dates":
        import json as _json, subprocess as _sp

        c1, c2 = st.columns([1, 2])
        with c1:
            cmp_ticker = st.selectbox("Ticker", tickers, key="cmp_tick")
        ticker_dir = reports_dir / cmp_ticker
        dates = sorted([p.name for p in ticker_dir.iterdir() if p.is_dir()], reverse=True)
        if len(dates) < 2:
            st.info("Need at least 2 saved dates for the same ticker to compare.")
            return
        with c2:
            cmp_dates = st.multiselect("Select dates to compare", dates,
                                       default=dates[:min(4, len(dates))])
        if not cmp_dates:
            return

        sorted_dates = sorted(cmp_dates)

        # Load summaries (never full reports)
        summaries = {}
        for d in sorted_dates:
            sj = ticker_dir / d / "summary.json"
            if sj.exists():
                summaries[d] = _json.loads(sj.read_text(encoding="utf-8"))
            else:
                # fallback: derive signal from decision.md only
                summaries[d] = {"date": d, "signal": _read_signal_from_folder(ticker_dir / d),
                                 "_no_summary": True}

        # ── Signal timeline ────────────────────────────────────────────────────
        st.markdown("#### Signal Timeline")
        sig_cols = st.columns(len(sorted_dates))
        _sig_icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
        for i, d in enumerate(sorted_dates):
            sig = summaries[d].get("signal", "—")
            sig_cols[i].metric(d, f"{_sig_icon.get(sig, '')} {sig}")

        st.divider()

        # ── Structured diff table (from summaries only) ────────────────────────
        st.markdown("#### Key Points by Date")
        _COMPARE_FIELDS = [
            ("bull_thesis",       "🟢 Bull Thesis"),
            ("bear_thesis",       "🔴 Bear Thesis"),
            ("trader_plan",       "🤝 Trader Plan"),
            ("final_decision",    "🏆 PM Decision"),
            ("analysts.market",   "📈 Market"),
            ("analysts.news",     "📰 News"),
            ("analysts.fundamentals", "🏢 Fundamentals"),
        ]
        field_choice = st.selectbox(
            "Field to compare",
            [label for _, label in _COMPARE_FIELDS],
            key="cmp_field",
        )
        chosen_key = next(k for k, l in _COMPARE_FIELDS if l == field_choice)

        def _get_field(s: dict, key: str) -> str:
            if "." in key:
                a, b = key.split(".", 1)
                return s.get(a, {}).get(b, "_not available_")
            return s.get(key, "_not available_")

        cols = st.columns(len(sorted_dates))
        for i, d in enumerate(sorted_dates):
            with cols[i]:
                st.markdown(f"**{d}**")
                if summaries[d].get("_no_summary"):
                    st.caption("No summary.json — re-run analysis to generate")
                else:
                    val = _get_field(summaries[d], chosen_key)
                    st.markdown(val or "_empty_")

        st.divider()

        # ── AI comparison (summaries only → tiny prompt) ───────────────────────
        st.markdown("#### 🤖 AI Comparison")
        st.caption("Sends only the extracted summaries (~2 KB) — not the full reports.")

        if st.button("Compare with Claude", type="primary"):
            # Build compact prompt from summaries
            blocks = []
            for d in sorted_dates:
                s = summaries[d]
                if s.get("_no_summary"):
                    blocks.append(f"## {d}\nSignal: {s.get('signal','?')}\n(No summary available)")
                    continue
                blocks.append(
                    f"## {d}  |  Signal: {s.get('signal','?')}\n"
                    f"Bull: {s.get('bull_thesis','')}\n"
                    f"Bear: {s.get('bear_thesis','')}\n"
                    f"Trader: {s.get('trader_plan','')}\n"
                    f"PM Decision: {s.get('final_decision','')}\n"
                    f"Market: {s.get('analysts',{}).get('market','')}\n"
                    f"Fundamentals: {s.get('analysts',{}).get('fundamentals','')}"
                )

            prompt = (
                f"You are a financial analyst. Compare these {len(sorted_dates)} analyses "
                f"of {cmp_ticker} across different dates.\n\n"
                + "\n\n---\n\n".join(blocks)
                + "\n\n---\n\n"
                "Answer these questions concisely:\n"
                "1. How did the signal change and why?\n"
                "2. What changed most in the bull/bear thesis?\n"
                "3. What changed in fundamentals or market technicals?\n"
                "4. What is the trend — improving, deteriorating, or stable?\n"
                "Keep your response under 400 words."
            )

            with st.spinner("Comparing with Claude…"):
                try:
                    proc = _sp.Popen(
                        ["claude", "--output-format", "text",
                         "--dangerously-skip-permissions", "-p", prompt],
                        stdout=_sp.PIPE, stderr=_sp.PIPE,
                        stdin=_sp.DEVNULL, encoding="utf-8", errors="replace",
                    )
                    out, err = proc.communicate(timeout=120)
                    if proc.returncode == 0 and out.strip():
                        st.markdown(out.strip())
                    else:
                        st.error(f"Claude error: {err.strip()[:300]}")
                except Exception as e:
                    st.error(f"Failed: {e}")
        return

    # ══════════════════════════════════════════════════════════════════════════
    # Default: View Report
    c1, c2 = st.columns([1, 1])
    with c1:
        selected_ticker = st.selectbox("Ticker", tickers)
    ticker_dir = reports_dir / selected_ticker
    dates = sorted([p.name for p in ticker_dir.iterdir() if p.is_dir()], reverse=True)
    if not dates:
        st.info(f"No reports for {selected_ticker}.")
        return
    with c2:
        selected_date = st.selectbox("Date", dates)

    # overwrite notice
    st.caption(
        f"💡 Re-running **{selected_ticker}** on **{selected_date}** will overwrite this report. "
        "Use a different date to keep both."
    )

    base = ticker_dir / selected_date
    section_tab = sac.tabs(
        [sac.TabsItem(label, icon=icon) for label, _, icon, _ in _SECTIONS],
        color="#36cfc9", size="sm", align="start",
    )
    for label, folder, _, files in _SECTIONS:
        if section_tab != label:
            continue
        section_dir = base / folder
        if not section_dir.exists():
            st.info(f"No data for {label}.")
            break
        available = [(stem, title) for stem, title in files
                     if (section_dir / f"{stem}.md").exists()]
        if not available:
            st.info("No files saved for this section.")
            break
        if len(available) == 1:
            st.markdown((section_dir / f"{available[0][0]}.md").read_text(encoding="utf-8"))
        else:
            sub_tab = sac.tabs(
                [sac.TabsItem(title) for _, title in available],
                color="#36cfc9", size="xs", align="start",
            )
            for stem, title in available:
                if sub_tab == title:
                    st.markdown((section_dir / f"{stem}.md").read_text(encoding="utf-8"))
                    break
        break

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

def _render_saas_finder_page():
    st.markdown("### 🔍 SaaS Finder — 护城河四维度 Moat Scanner")
    st.caption(
        "Uses Claude to identify publicly-traded SaaS companies with the strongest moats "
        "across four dimensions: Distribution · Proprietary Data · Integration · Regulatory."
    )

    with st.form("saas_finder_form"):
        col1, col2 = st.columns([2, 3])
        with col1:
            n = st.slider("Number of companies", min_value=1, max_value=15, value=5)
        with col2:
            sector_hint = st.text_input(
                "Sector filter (optional)",
                placeholder="e.g. Fintech, HR-Tech, DevOps, Healthcare",
            )
        submitted = st.form_submit_button("🔍 Find SaaS Moats", type="primary", use_container_width=True)

    if submitted and not st.session_state.saas_running:
        st.session_state.saas_results = None
        st.session_state.saas_running = True
        status_box = st.empty()
        messages = []

        def _cb(msg: str):
            messages.append(msg)
            status_box.info("  \n".join(messages))

        try:
            from tradingagents.saas_finder import run_saas_finder
            with st.spinner("Running SaaS Finder analysis… (may take 1–2 min)"):
                results = run_saas_finder(
                    n=n,
                    sector_hint=sector_hint.strip(),
                    progress_cb=_cb,
                )
            st.session_state.saas_results = results
        except Exception as e:
            st.error(f"SaaS Finder error: {e}")
        finally:
            st.session_state.saas_running = False
            status_box.empty()

    results = st.session_state.saas_results
    if results:
        import pandas as pd

        st.markdown(f"#### Top {len(results)} Companies by Moat Score")

        rows = []
        for r in results:
            rows.append({
                "Ticker":       r.get("ticker", "?"),
                "Company":      r.get("company", "?"),
                "Sector":       r.get("sector", "?"),
                "Distribution": r.get("moat_distribution", 0),
                "Data":         r.get("moat_data", 0),
                "Integration":  r.get("moat_integration", 0),
                "Regulatory":   r.get("moat_regulatory", 0),
                "Total /40":    r.get("moat_total", 0),
                "AI Stance":    r.get("ai_stance", "?"),
            })
        df = pd.DataFrame(rows)

        def _color_total(val):
            if isinstance(val, (int, float)):
                if val >= 30: return "color:#00e676;font-weight:bold"
                if val >= 22: return "color:#ffb800;font-weight:bold"
                return "color:#ff5252"
            return ""

        st.dataframe(
            df.style.applymap(_color_total, subset=["Total /40"]),
            use_container_width=True,
        )

        st.divider()
        st.markdown("#### Detailed Analysis")
        for r in results:
            with st.expander(f"**{r.get('ticker','?')}** — {r.get('company','?')} (Total: {r.get('moat_total',0)}/40)"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Distribution",  f"{r.get('moat_distribution', 0)}/10")
                c2.metric("Data",          f"{r.get('moat_data', 0)}/10")
                c3.metric("Integration",   f"{r.get('moat_integration', 0)}/10")
                c4.metric("Regulatory",    f"{r.get('moat_regulatory', 0)}/10")

                st.markdown(f"**Sector:** {r.get('sector','?')}  |  **AI Stance:** {r.get('ai_stance','?')}")
                st.markdown(f"**AI Data Advantage:** {r.get('ai_data_advantage','?')}  |  **AI Threat:** {r.get('ai_threat','?')}")
                st.info(f"**Core Thesis:** {r.get('core_thesis','?')}")
                st.warning(f"**Key Risk:** {r.get('key_risk','?')}")


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
        from cli.main import save_report_to_disk, extract_and_save_summary
        for base in [config.get("results_dir_local"), config.get("results_dir")]:
            if base:
                try:
                    p = Path(base) / ticker / str(trade_date)
                    save_report_to_disk(final_state, ticker, p)
                    extract_and_save_summary(final_state, ticker, p)
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
        sac.MenuItem("SaaS Finder",    icon="search"),
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
    use_options      = st.checkbox("Options (LEAP vs Stock)", value=False,
                                   help="Fetches yfinance options chain, recommends LEAP vs buying stock")

    selected_analysts = (
        (["market"]       if use_market       else []) +
        (["news"]         if use_news         else []) +
        (["fundamentals"] if use_fundamentals else []) +
        (["valuation"]    if use_valuation    else []) +
        (["macro"]        if use_macro        else []) +
        (["social"]       if use_social       else []) +
        (["options"]      if use_options      else [])
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
# Hero banner — theme-aware background
if _logo_b64:
    _banner_bg = {
        "dark":    "linear-gradient(160deg, #050a10 0%, #0c1826 50%, #050a10 100%)",
        "light":   "linear-gradient(160deg, #e8f0fe 0%, #dbeafe 50%, #e8f0fe 100%)",
        "rainbow": "linear-gradient(160deg, #0a0010 0%, #100818 40%, #0a100a 100%)",
    }[st.session_state.theme]
    _banner_blend = "multiply" if st.session_state.theme == "light" else "screen"
    _banner_glow  = {
        "dark":    "drop-shadow(0 0 40px #36cfc966)",
        "light":   "drop-shadow(0 0 24px #0066cc55)",
        "rainbow": "drop-shadow(0 0 40px #ff33ff66)",
    }[st.session_state.theme]

    st.markdown(f"""
    <style>
    .hero-banner {{
        position: relative;
        width: 100%;
        border-radius: 16px;
        overflow: hidden;
        margin-bottom: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 220px;
        background: {_banner_bg};
        border: 1px solid var(--sl-border);
    }}
    .hero-banner::before {{
        content: "";
        position: absolute;
        inset: 0;
        background-image: url("data:image/png;base64,{_logo_b64}");
        background-size: 55%;
        background-repeat: no-repeat;
        background-position: center;
        opacity: 0.07;
        filter: blur(1px);
    }}
    .hero-banner img {{
        position: relative;
        z-index: 1;
        width: 62%;
        max-width: 740px;
        min-width: 280px;
        height: auto;
        mix-blend-mode: {_banner_blend};
        filter: {_banner_glow} brightness(1.05);
    }}
    </style>
    <div class="hero-banner">
        <img src="data:image/png;base64,{_logo_b64}" alt="STARLUKE">
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

elif page == "SaaS Finder":
    _render_saas_finder_page()

else:
    # ── New Analysis page ──────────────────────────────────────────────────────
    result = st.session_state.result

    if result is None:
        # Landing — one row: illustration | How it works | Agent pipeline
        st.info("Configure your analysis in the sidebar and click **Run Analysis**.")

        col_img, col_how, col_pipe = st.columns([1.5, 1, 1])

        with col_img:
            if _illus_b64:
                st.markdown(f"""
                <img src="data:image/png;base64,{_illus_b64}"
                     style="width:100%; border-radius:12px; margin-top:8px;
                            opacity:0.93; filter:drop-shadow(0 4px 20px #0009);">
                """, unsafe_allow_html=True)

        with col_how:
            st.markdown("""
#### How it works
1. **Analysts** pull live market data
2. **Bull & Bear** debate the thesis
3. **Trader** builds a trade proposal
4. **Risk team** stress-tests sizing
5. **Portfolio Manager** → BUY / HOLD / SELL
            """)

        with col_pipe:
            st.markdown("""
#### Agent pipeline
```
Market  ┐
News    ├→ Bull/Bear
Fund.   │     ↓
Macro   ┘  Res. Mgr
              ↓
           Trader
              ↓
       Agg/Neu/Con
              ↓
        Port. Mgr
           VERDICT
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
            sac.TabsItem("Options",           icon="currency-dollar"),
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

        elif tab == "Options":
            show("options_report", "_Options analyst not selected. Enable 'Options (LEAP vs Stock)' in the sidebar._")

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
