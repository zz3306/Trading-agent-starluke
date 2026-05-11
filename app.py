"""
STARLUKE Web UI — powered by Streamlit + streamlit-antd-components
Run: streamlit run app.py
"""

import base64
import json
import os
import threading
import time
from datetime import date, timedelta
from pathlib import Path

import streamlit as st
import streamlit_antd_components as sac

os.environ.setdefault("PYTHONUTF8", "1")

# ── Module-level run state (persists across Streamlit reruns) ──────────────────
_RUN_LOCK = threading.Lock()
_RUN: dict = {"active": False, "progress": [], "result": None, "done": False, "error": None}

_NODE_LABELS: dict = {
    "Market Analyst":        "📈 Market Analyst",
    "News Analyst":          "📰 News Analyst",
    "Fundamentals Analyst":  "🏢 Fundamentals Analyst",
    "Valuation Analyst":     "🔢 Valuation Analyst",
    "Macro Analyst":         "🌐 Macro Analyst",
    "Social Analyst":        "💬 Social Analyst",
    "Options Analyst":       "💵 Options Analyst",
    "Bull Researcher":       "🟢 Bull Researcher",
    "Bear Researcher":       "🔴 Bear Researcher",
    "Research Manager":      "👔 Research Manager",
    "Trader":                "🤝 Trader",
    "Aggressive Analyst":    "🔴 Risk · Aggressive",
    "Neutral Analyst":       "🟡 Risk · Neutral",
    "Conservative Analyst":  "🟢 Risk · Conservative",
    "Portfolio Manager":     "🏆 Portfolio Manager",
}

_DEPTH_CFG = {
    "⚡ Shallow":  {"max_debate_rounds": 1, "max_risk_discuss_rounds": 1},
    "⚖️ Standard": {"max_debate_rounds": 1, "max_risk_discuss_rounds": 2},
    "🔬 Deep":     {"max_debate_rounds": 2, "max_risk_discuss_rounds": 3},
}

def _img_b64(name: str) -> str:
    p = Path(__file__).parent / "assets" / name
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""

_logo_b64     = _img_b64("Starluke.png")
_desert_bg_b64 = _img_b64("Cominc3.png")
_rock_bg_b64  = _img_b64("comic7.png")
_light_bg_b64 = _img_b64("微信图片_20260424015903_165_2.jpg")
_illus_b64    = _img_b64("1.png")

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

ROCK_CSS = _COMMON_CSS + """
:root { --sl-border:#222; --sl-muted:#888; }
html,body { background-color:#080808 !important; color:#f0f0f0 !important; }
[data-testid="stAppViewContainer"],[data-testid="stMain"]
    { background-color:transparent !important; color:#f0f0f0 !important; }
/* dark scrim over main content for readability */
[data-testid="stMain"] { background-color:rgba(0,0,0,0.62) !important; }
[data-testid="stSidebar"] { background-color:rgba(8,8,8,0.82) !important; border-right:1px solid #333 !important; padding-top:0 !important; }
[data-testid="stTextInput"] input,[data-testid="stDateInput"] input
    { background:#1c1c1c !important; border:1px solid #333 !important; color:#f0f0f0 !important; border-radius:6px !important; }
[data-testid="stSelectbox"]>div>div { background:#1c1c1c !important; border:1px solid #333 !important; color:#f0f0f0 !important; }
[data-testid="stButton"] button[kind="primary"]
    { background:linear-gradient(135deg,#36cfc9,#0d9e99) !important; border:none !important; color:#050505 !important;
      font-weight:700 !important; border-radius:8px !important; box-shadow:0 0 16px #36cfc944 !important; }
[data-testid="stButton"] button[kind="primary"]:hover { box-shadow:0 0 28px #36cfc966 !important; }
[data-testid="stMarkdownContainer"] { color:#e8e8e8 !important; }
[data-testid="stMarkdownContainer"] h1,[data-testid="stMarkdownContainer"] h2,[data-testid="stMarkdownContainer"] h3 { color:#36cfc9 !important; text-shadow:0 1px 8px #000a; }
[data-testid="stMarkdownContainer"] th { background:#1a1a1a !important; color:#36cfc9 !important; }
[data-testid="stMarkdownContainer"] tr:nth-child(even) td { background:#161616 !important; }
[data-testid="stCheckbox"] label { color:#ddd !important; }
[data-testid="stCaptionContainer"] { color:#888 !important; }
hr { border-color:#333 !important; }
.sig-buy  { background:#00e67612; border:2px solid #00e676; color:#00e676; box-shadow:0 0 28px #00e67630; }
.sig-sell { background:#ff174412; border:2px solid #ff1744; color:#ff1744; box-shadow:0 0 28px #ff174430; }
.sig-hold { background:#ffb80012; border:2px solid #ffb800; color:#ffb800; box-shadow:0 0 28px #ffb80030; }
"""

LIGHT_CSS = _COMMON_CSS + """
:root { --sl-border:#e0e4ea; --sl-muted:#8a8fa8; }
html,body { background-color:#e8edf5 !important; color:#0a0a1e !important; }
[data-testid="stAppViewContainer"],[data-testid="stMain"]
    { background-color:transparent !important; color:#0a0a1e !important; }
/* light scrim for readability over bg image */
[data-testid="stMain"] { background-color:rgba(240,244,252,0.72) !important; }
[data-testid="stSidebar"] { background-color:rgba(255,255,255,0.88) !important; border-right:1px solid #d0d4e0 !important; padding-top:0 !important; box-shadow:2px 0 12px #0002; }
[data-testid="stSidebar"] * { color:#1a1a2e !important; }
[data-testid="stTextInput"] input,[data-testid="stDateInput"] input
    { background:#fff !important; border:1px solid #c0c6d8 !important; color:#0a0a1e !important; border-radius:6px !important; }
[data-testid="stSelectbox"]>div>div { background:#fff !important; border:1px solid #c0c6d8 !important; color:#0a0a1e !important; }
[data-testid="stButton"] button[kind="primary"]
    { background:linear-gradient(135deg,#0066cc,#004fa3) !important; border:none !important; color:#fff !important;
      font-weight:700 !important; border-radius:8px !important; box-shadow:0 2px 12px #0066cc33 !important; }
[data-testid="stButton"] button[kind="primary"]:hover { box-shadow:0 4px 20px #0066cc55 !important; }
[data-testid="stMarkdownContainer"] { color:#0d0d2a !important; }
[data-testid="stMarkdownContainer"] h1,[data-testid="stMarkdownContainer"] h2,[data-testid="stMarkdownContainer"] h3 { color:#0044aa !important; font-weight:700 !important; }
[data-testid="stMarkdownContainer"] th { background:#dce8f8 !important; color:#003d99 !important; font-weight:700 !important; }
[data-testid="stMarkdownContainer"] tr:nth-child(even) td { background:#f0f4fc !important; }
[data-testid="stCheckbox"] label { color:#1a1a3e !important; font-weight:500 !important; }
[data-testid="stCaptionContainer"] { color:#5a6080 !important; }
hr { border-color:#c8d0e0 !important; }
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
html,body { background-color:#090909 !important; color:#f0f0f0 !important; }
[data-testid="stAppViewContainer"],[data-testid="stMain"]
    { background-color:transparent !important; color:#f0f0f0 !important; }
/* dark scrim for readability */
[data-testid="stMain"] { background-color:rgba(0,0,0,0.62) !important; }
[data-testid="stSidebar"] { background-color:rgba(10,10,10,0.85) !important; border-right:1px solid #2a2a2a !important; padding-top:0 !important; }
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

DESERT_CSS = _COMMON_CSS + """
:root { --sl-border:#c8a97a; --sl-muted:#9a7a50; }
html,body { background-color:#f7ede0 !important; color:#2c1a08 !important; }
[data-testid="stAppViewContainer"],[data-testid="stMain"]
    { background-color:transparent !important; color:#1a0a00 !important; }
/* warm scrim over bg image */
[data-testid="stMain"] { background-color:rgba(245,235,215,0.70) !important; }
[data-testid="stSidebar"] { background-color:rgba(253,244,232,0.90) !important; border-right:1px solid #c8a97a !important; padding-top:0 !important; box-shadow:2px 0 10px #b8813030; }
[data-testid="stSidebar"] * { color:#2c1a08 !important; }
[data-testid="stTextInput"] input,[data-testid="stDateInput"] input
    { background:#fffaf4 !important; border:1px solid #b89060 !important; color:#1a0a00 !important; border-radius:6px !important; }
[data-testid="stSelectbox"]>div>div { background:#fffaf4 !important; border:1px solid #b89060 !important; color:#1a0a00 !important; }
[data-testid="stButton"] button[kind="primary"]
    { background:linear-gradient(135deg,#c47c2b,#a05a14) !important; border:none !important; color:#fff !important;
      font-weight:700 !important; border-radius:8px !important; box-shadow:0 2px 12px #c47c2b55 !important; }
[data-testid="stButton"] button[kind="primary"]:hover { box-shadow:0 4px 20px #c47c2b88 !important; }
[data-testid="stMarkdownContainer"] { color:#1a0a00 !important; }
[data-testid="stMarkdownContainer"] h1,[data-testid="stMarkdownContainer"] h2,[data-testid="stMarkdownContainer"] h3 { color:#7a3010 !important; font-weight:700 !important; }
[data-testid="stMarkdownContainer"] th { background:#e8d0a8 !important; color:#7a3010 !important; font-weight:700 !important; }
[data-testid="stMarkdownContainer"] tr:nth-child(even) td { background:#f5ead8 !important; }
[data-testid="stCheckbox"] label { color:#3a2010 !important; font-weight:500 !important; }
[data-testid="stCaptionContainer"] { color:#8a6040 !important; }
hr { border-color:#c8a97a !important; }
.sig-buy  { background:#e8f5e2; border:2px solid #2d7a1e; color:#1a5010; box-shadow:0 2px 12px #2d7a1e33; }
.sig-sell { background:#f5e8e8; border:2px solid #a02020; color:#7a1010; box-shadow:0 2px 12px #a0202033; }
.sig-hold { background:#fdf0d0; border:2px solid #c47c2b; color:#7a4010; box-shadow:0 2px 12px #c47c2b33; }
"""

# ── Persistent preferences ─────────────────────────────────────────────────────
_PREFS_FILE = Path(__file__).parent / ".starluke_prefs.json"

def _load_prefs() -> dict:
    try:
        return json.loads(_PREFS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_prefs(**kwargs) -> None:
    try:
        prefs = _load_prefs()
        prefs.update(kwargs)
        _PREFS_FILE.write_text(json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

_prefs = _load_prefs()

# ── Session state ──────────────────────────────────────────────────────────────
if "theme"         not in st.session_state: st.session_state.theme         = _prefs.get("theme", "rock")
if "result"        not in st.session_state: st.session_state.result        = None
if "running"       not in st.session_state: st.session_state.running       = False
if "nav"           not in st.session_state: st.session_state.nav           = "New Analysis"
if "username"      not in st.session_state: st.session_state.username      = _prefs.get("username", "")
if "saas_results"  not in st.session_state: st.session_state.saas_results  = None
if "saas_running"  not in st.session_state: st.session_state.saas_running  = False

# Inject active theme
_css_map = {"rock": ROCK_CSS, "light": LIGHT_CSS, "desert": DESERT_CSS, "rainbow": RAINBOW_CSS}
st.markdown(f"<style>{_css_map[st.session_state.theme]}</style>", unsafe_allow_html=True)

# Per-theme background image injection  (b64, mime, opacity)
_theme_bg = {
    "rock":    (_rock_bg_b64,   "image/png",  "0.45"),
    "light":   (_light_bg_b64,  "image/jpeg", "0.35"),
    "desert":  (_desert_bg_b64, "image/png",  "0.40"),
    "rainbow": (_desert_bg_b64, "image/png",  "0.15"),
}
_active_bg_b64, _active_bg_mime, _active_bg_opacity = _theme_bg.get(
    st.session_state.theme, (_desert_bg_b64, "image/png", "0.13")
)
if _active_bg_b64:
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: fixed;
        inset: 0;
        background-image: url("data:{_active_bg_mime};base64,{_active_bg_b64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        opacity: {_active_bg_opacity};
        pointer-events: none;
        z-index: 0;
    }}
    [data-testid="stMain"] > div {{ position: relative; z-index: 1; }}
    </style>
    """, unsafe_allow_html=True)

# ── Welcome screen ─────────────────────────────────────────────────────────────
if not st.session_state.username:
    _wc_bg_url = f'url("data:image/png;base64,{_desert_bg_b64}")' if _desert_bg_b64 else "none"
    st.markdown(f"""
    <style>
    [data-testid="stSidebar"] {{ display: none !important; }}

    /* background fills full viewport at high opacity */
    html, body, [data-testid="stAppViewContainer"] {{
        background-image: {_wc_bg_url} !important;
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
        font-size: 1.05rem;
        letter-spacing: 4px;
        text-transform: uppercase;
        color: #ddd;
        margin-bottom: 24px;
        font-weight: 500;
    }}
    /* bigger label for the name input */
    [data-testid="stTextInput"] label p {{
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        color: #eee !important;
        letter-spacing: 1px !important;
        margin-bottom: 6px !important;
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
            _save_prefs(username=st.session_state.username)
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
        st.dataframe(df.style.map(color_signal, subset=["signal"]),
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
            df.style.map(_color_total, subset=["Total /40"]),
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


def run_analysis(ticker, trade_date, analysts,
                 quick_model="claude-cli", deep_model="claude-cli",
                 output_language="English", depth_cfg=None):
    depth_cfg = depth_cfg or {"max_debate_rounds": 1, "max_risk_discuss_rounds": 1}

    def _progress_cb(node_name: str):
        label = _NODE_LABELS.get(node_name, node_name)
        with _RUN_LOCK:
            _RUN["progress"].append(label)

    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG.copy()
        config.update({
            "selected_analysts": analysts,
            "quick_think_llm": quick_model,
            "deep_think_llm": deep_model,
            "output_language": output_language,
            **depth_cfg,
        })
        ta = TradingAgentsGraph(debug=False, config=config)
        final_state, signal = ta.propagate(ticker, str(trade_date), progress_cb=_progress_cb)
        from cli.main import save_report_to_disk, extract_and_save_summary
        for base in [config.get("results_dir_local"), config.get("results_dir")]:
            if base:
                try:
                    p = Path(base) / ticker / str(trade_date)
                    save_report_to_disk(final_state, ticker, p)
                    extract_and_save_summary(final_state, ticker, p)
                except Exception:
                    pass
        try:
            from cli.main import _append_signal_log
            _append_signal_log(config, ticker, str(trade_date), signal)
        except Exception:
            pass
        with _RUN_LOCK:
            _RUN["result"] = {"state": final_state, "signal": signal, "error": None}
            _RUN["done"] = True
    except Exception as e:
        with _RUN_LOCK:
            _RUN["result"] = {"error": str(e), "state": None}
            _RUN["done"] = True


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

    # Greeting — big name display
    st.markdown(
        f"<div style='text-align:center;padding:8px 0 4px;'>"
        f"<div style='font-size:0.75rem;color:#888;letter-spacing:2px;text-transform:uppercase;margin-bottom:2px;'>Welcome back</div>"
        f"<div style='font-size:1.35rem;font-weight:700;color:#36cfc9;'>{st.session_state.username}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button("✏️ Change Name", use_container_width=True, key="change_name_btn"):
        st.session_state.username = ""
        _save_prefs(username="")
        st.rerun()

    # Theme switcher
    theme_choice = sac.segmented(
        items=[
            sac.SegmentedItem(label="🪨 Rock"),
            sac.SegmentedItem(label="☀️ Light"),
            sac.SegmentedItem(label="🏜️ Desert"),
            sac.SegmentedItem(label="🌈 Rainbow"),
        ],
        label=None, size="xs", color="#36cfc9", use_container_width=True,
        index={"rock": 0, "light": 1, "desert": 2, "rainbow": 3}[st.session_state.theme],
    )
    _label_map = {"🪨 Rock": "rock", "☀️ Light": "light", "🏜️ Desert": "desert", "🌈 Rainbow": "rainbow"}
    if theme_choice and _label_map.get(theme_choice, st.session_state.theme) != st.session_state.theme:
        st.session_state.theme = _label_map[theme_choice]
        _save_prefs(theme=st.session_state.theme)
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

    sac.divider(label="Depth", align="center", color="#333")
    depth_choice = sac.segmented(
        items=[
            sac.SegmentedItem(label="⚡ Shallow"),
            sac.SegmentedItem(label="⚖️ Standard"),
            sac.SegmentedItem(label="🔬 Deep"),
        ],
        label=None, size="xs", color="#36cfc9", use_container_width=True,
        index=1,
    )
    _depth_key = depth_choice or "⚖️ Standard"
    selected_depth_cfg = _DEPTH_CFG.get(_depth_key, _DEPTH_CFG["⚖️ Standard"])
    _depth_hint = {"⚡ Shallow": "1 debate · 1 risk round",
                   "⚖️ Standard": "1 debate · 2 risk rounds",
                   "🔬 Deep": "2 debates · 3 risk rounds"}
    st.caption(_depth_hint.get(_depth_key, ""))

    sac.divider(label="Model", align="center", color="#333")

    from tradingagents.llm_clients.model_catalog import get_model_options
    _qopts = get_model_options("claude_cli", "quick")
    _dopts = get_model_options("claude_cli", "deep")
    quick_model = dict(_qopts)[st.selectbox("Quick (analysts)", [l for l,_ in _qopts], index=0)]
    deep_model  = dict(_dopts)[st.selectbox("Deep (PM & research)", [l for l,_ in _dopts], index=0)]

    sac.divider(label="Language", align="center", color="#333")
    lang_choice = sac.segmented(
        items=[
            sac.SegmentedItem(label="🇺🇸 English"),
            sac.SegmentedItem(label="🇨🇳 中文"),
        ],
        label=None, size="xs", color="#36cfc9", use_container_width=True,
        index=0,
    )
    output_language = "Chinese" if lang_choice == "🇨🇳 中文" else "English"

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    run_btn = st.button(
        "🚀  Run Analysis", use_container_width=True, type="primary",
        disabled=not ticker or not selected_analysts or st.session_state.running,
    )
    if not selected_analysts:
        st.warning("Select at least one analyst.")

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.caption("💡 First run ~3–5 min · Results auto-saved to reports/")


# ── MAIN AREA ──────────────────────────────────────────────────────────────────
# Hero banner — theme-aware background
if _logo_b64:
    _banner_bg = {
        "rock":    "linear-gradient(160deg, #050a10 0%, #0c1826 50%, #050a10 100%)",
        "light":   "linear-gradient(160deg, #e8f0fe 0%, #dbeafe 50%, #e8f0fe 100%)",
        "desert":  "linear-gradient(160deg, #2c1a08 0%, #4a2c10 50%, #2c1a08 100%)",
        "rainbow": "linear-gradient(160deg, #0a0010 0%, #100818 40%, #0a100a 100%)",
    }[st.session_state.theme]
    _banner_blend = "multiply" if st.session_state.theme in ("light", "desert") else "screen"
    _banner_glow  = {
        "rock":    "drop-shadow(0 0 40px #36cfc966)",
        "light":   "drop-shadow(0 0 24px #0066cc55)",
        "desert":  "drop-shadow(0 0 40px #c47c2b88)",
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

# ── Kick off analysis ──────────────────────────────────────────────────────────
if run_btn and not st.session_state.running:
    _n_analysts = len(selected_analysts)
    _dr = selected_depth_cfg.get("max_debate_rounds", 1)
    _rr = selected_depth_cfg.get("max_risk_discuss_rounds", 1)
    _total = _n_analysts + 2 * _dr + 1 + 1 + 3 * _rr + 1   # analysts+debate+trader+risk+PM
    with _RUN_LOCK:
        _RUN.update({"active": True, "progress": [], "result": None, "done": False, "error": None})
    st.session_state.result        = None
    st.session_state.running       = True
    st.session_state.nav           = "New Analysis"
    st.session_state._run_ticker   = ticker
    st.session_state._run_date     = str(trade_date)
    st.session_state._run_total    = _total
    st.session_state._run_started  = time.time()
    threading.Thread(
        target=run_analysis,
        args=(ticker, trade_date, selected_analysts, quick_model, deep_model,
              output_language, selected_depth_cfg),
        daemon=True,
    ).start()
    st.rerun()

# ── Poll for completion ─────────────────────────────────────────────────────────
if st.session_state.running:
    with _RUN_LOCK:
        _done   = _RUN["done"]
        _result = _RUN.get("result")
    if _done:
        st.session_state.running = False
        st.session_state.result  = _result
        st.rerun()

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

    if st.session_state.running:
        # ── Live progress display ──────────────────────────────────────────────
        with _RUN_LOCK:
            _prog  = list(_RUN["progress"])
        _total   = st.session_state.get("_run_total", 15)
        _ticker  = st.session_state.get("_run_ticker", "")
        _rdate   = st.session_state.get("_run_date", "")
        _elapsed = int(time.time() - st.session_state.get("_run_started", time.time()))
        _mins, _secs = divmod(_elapsed, 60)

        st.markdown(
            f"<h3 style='margin-bottom:4px;'>⏳ Analyzing <span style='color:#36cfc9'>{_ticker}</span>"
            f" &nbsp;·&nbsp; {_rdate}</h3>"
            f"<div style='color:var(--sl-muted);font-size:0.85rem;margin-bottom:16px;'>"
            f"Elapsed: {_mins:02d}:{_secs:02d} &nbsp;·&nbsp; {len(_prog)}/{_total} steps</div>",
            unsafe_allow_html=True,
        )
        st.progress(min(len(_prog) / max(_total, 1), 0.99))

        if _prog:
            # Completed steps
            _done_html = "".join(
                f"<div style='padding:3px 0;font-size:0.88rem;'>✅ {s}</div>"
                for s in _prog[:-1]
            )
            # Current (last) step — animated
            _done_html += (
                f"<div style='padding:4px 0;font-size:0.92rem;font-weight:600;"
                f"color:#36cfc9;'>⚙️ {_prog[-1]} &nbsp;<span style='opacity:0.6;font-size:0.8rem;'>running…</span></div>"
            )
            st.markdown(
                f"<div style='border:1px solid var(--sl-border);border-radius:10px;"
                f"padding:12px 18px;margin-top:8px;'>{_done_html}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='color:var(--sl-muted);font-size:0.88rem;'>Initializing agents…</div>",
                unsafe_allow_html=True,
            )

        time.sleep(2)
        st.rerun()

    elif result is None:
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
