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

# Index-based depth config (0=Shallow, 1=Standard, 2=Deep)
_DEPTH_CFG = [
    {"max_debate_rounds": 1, "max_risk_discuss_rounds": 1},
    {"max_debate_rounds": 1, "max_risk_discuss_rounds": 2},
    {"max_debate_rounds": 2, "max_risk_discuss_rounds": 3},
]

# ── UI Translations ────────────────────────────────────────────────────────────
_T = {
    "en": {
        # Welcome screen
        "wc_sub":              "Multi-Agent Stock Analysis",
        "wc_name_label":       "What's your name?",
        "wc_name_placeholder": "Enter your name…",
        "wc_enter":            "Enter →",
        # Sidebar
        "logo_sub":            "Powered by Claude CLI",
        "welcome_back":        "Welcome back",
        "change_name":         "✏️ Change Name",
        "div_ui_lang":         "UI Language",
        "nav_new":             "New Analysis",
        "nav_saas":            "SaaS Finder",
        "nav_browse":          "Browse Reports",
        "nav_log":             "Signal Log",
        "div_config":          "Configuration",
        "ticker_label":        "Stock Ticker",
        "ticker_placeholder":  "e.g. NVDA, TSLA, 0700.HK",
        "date_label":          "Analysis Date",
        "div_analysts":        "Analysts",
        "cb_market":           "Market (Technical)",
        "cb_news":             "News",
        "cb_fundamentals":     "Fundamentals",
        "cb_valuation":        "Valuation & Peers",
        "cb_valuation_help":   "Peer P/E, EV/EBITDA comparison",
        "cb_macro":            "Macro (Fed/CPI/Yield)",
        "cb_macro_help":       "Cached 7 days — very fast on repeats",
        "cb_social":           "Social (= News data)",
        "cb_social_help":      "yfinance doesn't have Reddit/Twitter data",
        "cb_options":          "Options (LEAP vs Stock)",
        "cb_options_help":     "Fetches yfinance options chain, recommends LEAP vs buying stock",
        "div_depth":           "Depth",
        "depth_0":             "⚡ Shallow",
        "depth_1":             "⚖️ Standard",
        "depth_2":             "🔬 Deep",
        "depth_hint_0":        "1 debate · 1 risk round",
        "depth_hint_1":        "1 debate · 2 risk rounds",
        "depth_hint_2":        "2 debates · 3 risk rounds",
        "div_model":           "Model",
        "model_quick":         "Quick (analysts)",
        "model_deep":          "Deep (PM & research)",
        "div_lang":            "Language",
        "run_btn":             "🚀  Run Analysis",
        "no_analyst_warn":     "Select at least one analyst.",
        "run_hint":            "💡 First run ~3–5 min · Results auto-saved to reports/",
        # New Analysis landing
        "landing_info":        "Configure your analysis in the sidebar and click **Run Analysis**.",
        "how_it_works":        "#### How it works",
        "how_steps":           "1. **Analysts** pull live market data\n2. **Bull & Bear** debate the thesis\n3. **Trader** builds a trade proposal\n4. **Risk team** stress-tests sizing\n5. **Portfolio Manager** → BUY / HOLD / SELL",
        "agent_pipeline":      "#### Agent pipeline",
        # Running
        "analyzing":           "Analyzing",
        "elapsed":             "Elapsed",
        "steps":               "steps",
        "initializing":        "Initializing agents…",
        # Result
        "analysis_date":       "Analysis date:",
        "analysis_failed":     "Analysis failed:",
        "completed_cap":       "Completed: **{ticker}** · {date} · Change ticker/date in sidebar to rerun.",
        # Result tabs
        "tab_final":           "Final Decision",
        "tab_trader":          "Trader Plan",
        "tab_research":        "Research Manager",
        "tab_market":          "Market",
        "tab_news":            "News",
        "tab_fundamentals":    "Fundamentals",
        "tab_valuation":       "Valuation",
        "tab_macro":           "Macro",
        "tab_options":         "Options",
        "tab_sentiment":       "Sentiment",
        "tab_risk":            "Risk Debate",
        "no_final":            "_No final decision recorded._",
        "no_market":           "_Market analyst not selected._",
        "no_news":             "_News analyst not selected._",
        "no_fund":             "_Fundamentals analyst not selected._",
        "no_val":              "_Valuation analyst not selected._",
        "no_macro":            "_Macro analyst not selected._",
        "no_opt":              "_Options analyst not selected. Enable 'Options (LEAP vs Stock)' in the sidebar._",
        "no_sent":             "_Sentiment analyst not selected._",
        # Browse Reports
        "browse_title":        "### 📂 Browse Reports",
        "no_reports":          "No reports saved yet. Run an analysis first.",
        "no_reports2":         "No reports saved yet.",
        "mode_view":           "📄 View Report",
        "mode_compare":        "📊 Compare Dates",
        "mode_delete":         "🗑️ Delete",
        "del_warn":            "Select a report to permanently delete it.",
        "del_ticker_lbl":      "Ticker",
        "del_date_lbl":        "Date",
        "del_will":            "**Will delete:**",
        "del_confirm":         "🗑️ Confirm Delete",
        "del_success":         "Deleted {ticker} / {date}",
        "no_ticker_dates":     "No reports for this ticker.",
        "cmp_need2":           "Need at least 2 saved dates for the same ticker to compare.",
        "cmp_select":          "Select dates to compare",
        "signal_timeline":     "#### Signal Timeline",
        "key_points":          "#### Key Points by Date",
        "field_compare":       "Field to compare",
        "ai_compare":          "#### 🤖 AI Comparison",
        "ai_compare_cap":      "Sends only the extracted summaries (~2 KB) — not the full reports.",
        "compare_btn":         "Compare with Claude",
        "comparing":           "Comparing with Claude…",
        "no_summary":          "No summary.json — re-run analysis to generate",
        "overwrite_notice":    "💡 Re-running **{ticker}** on **{date}** will overwrite this report. Use a different date to keep both.",
        "no_data_label":       "No data for {label}.",
        "no_files":            "No files saved for this section.",
        "no_ticker_reports":   "No reports for {ticker}.",
        # Section / sub-tab labels
        "sec_analysts":        "I · Analysts",
        "sec_research":        "II · Research",
        "sec_trading":         "III · Trading",
        "sec_risk":            "IV · Risk",
        "sec_portfolio":       "V · Portfolio",
        "sub_market":          "📈 Market",
        "sub_news":            "📰 News",
        "sub_fundamentals":    "🏢 Fundamentals",
        "sub_valuation":       "🔢 Valuation",
        "sub_macro":           "🌐 Macro",
        "sub_sentiment":       "💬 Sentiment",
        "sub_options":         "💵 Options",
        "sub_bull":            "🟢 Bull",
        "sub_bear":            "🔴 Bear",
        "sub_manager":         "👔 Research Mgr",
        "sub_trader":          "🤝 Trader",
        "sub_aggressive":      "🔴 Aggressive",
        "sub_conservative":    "🟢 Conservative",
        "sub_neutral":         "🟡 Neutral",
        "sub_decision":        "🏆 Final Decision",
        # Signal Log
        "log_title":           "### 📊 Signal Log",
        "no_signals":          "No signals logged yet. Signal log is created after your first analysis.",
        "log_empty":           "Signal log is empty.",
        "log_total":           "Total",
        "log_error":           "Could not read signal log:",
        # SaaS Finder
        "saas_title":          "### 🔍 SaaS Finder — 护城河四维度 Moat Scanner",
        "saas_caption":        "Uses Claude to identify publicly-traded SaaS companies with the strongest moats across four dimensions: Distribution · Proprietary Data · Integration · Regulatory.",
        "saas_how_title":      "📖 How to interpret scores",
        "saas_explanation":    """\
**Four-Dimension Moat Framework — each dimension scored 1–10, total out of 40**

| Dimension | What it measures |
|-----------|-----------------|
| **Distribution** | Switching cost, workflow integration depth, viral or enterprise distribution strength |
| **Proprietary Data** | Whether the product gets smarter with usage; unique datasets competitors cannot replicate |
| **Integration Depth** | Number of mission-critical integrations (ERP, CRM); replacement complexity; bundle lock-in |
| **Regulatory / Compliance** | SOC 2, HIPAA, FedRAMP certifications as entry barriers; regulated-industry dominance |

**Total Score Interpretation (/40)**
- 🟢 **30–40** — Strong moat: highly defensible business with compounding advantages
- 🟡 **22–29** — Moderate moat: meaningful advantages but exposed to competitive pressure
- 🔴 **< 22** — Weak moat: limited defensibility; elevated AI disruption risk

**AI Stance**
- **Builder** — develops proprietary AI on top of their data; stronger moat over time
- **Buyer** — uses third-party AI; moat depends on data and distribution, not AI itself""",
        "saas_n_label":        "Number of companies",
        "saas_sector_label":   "Sector filter (optional)",
        "saas_sector_ph":      "e.g. Fintech, HR-Tech, DevOps, Healthcare",
        "saas_submit":         "🔍 Find SaaS Moats",
        "saas_spinner":        "Running SaaS Finder analysis… (may take 1–2 min)",
        "saas_error":          "SaaS Finder error:",
        "saas_results_title":  "#### Top {n} Companies by Moat Score",
        "saas_legend":         "🟢 ≥ 30 Strong moat  ·  🟡 22–29 Moderate  ·  🔴 < 22 Weak",
        "saas_detail_title":   "#### Detailed Analysis",
        "saas_sector_lbl":     "**Sector:**",
        "saas_ai_stance_lbl":  "**AI Stance:**",
        "saas_ai_data_adv":    "**AI Data Advantage:**",
        "saas_ai_threat":      "**AI Threat:**",
        "saas_core_thesis":    "**Core Thesis:**",
        "saas_key_risk":       "**Key Risk:**",
        "dist_label":          "Distribution",
        "data_label":          "Data",
        "integ_label":         "Integration",
        "reg_label":           "Regulatory",
    },
    "zh": {
        # Welcome screen
        "wc_sub":              "多智能体股票分析系统",
        "wc_name_label":       "你叫什么名字？",
        "wc_name_placeholder": "输入你的名字…",
        "wc_enter":            "进入 →",
        # Sidebar
        "logo_sub":            "由 Claude CLI 驱动",
        "welcome_back":        "欢迎回来",
        "change_name":         "✏️ 修改名字",
        "div_ui_lang":         "界面语言",
        "nav_new":             "新分析",
        "nav_saas":            "SaaS 筛选",
        "nav_browse":          "浏览报告",
        "nav_log":             "信号记录",
        "div_config":          "配置",
        "ticker_label":        "股票代码",
        "ticker_placeholder":  "例如 NVDA、TSLA、0700.HK",
        "date_label":          "分析日期",
        "div_analysts":        "分析师",
        "cb_market":           "市场（技术面）",
        "cb_news":             "新闻",
        "cb_fundamentals":     "基本面",
        "cb_valuation":        "估值与同行",
        "cb_valuation_help":   "同行市盈率、EV/EBITDA 对比",
        "cb_macro":            "宏观（美联储/CPI/收益率）",
        "cb_macro_help":       "缓存7天，重复运行极快",
        "cb_social":           "社交（= 新闻数据）",
        "cb_social_help":      "yfinance 无 Reddit/Twitter 数据",
        "cb_options":          "期权（LEAP vs 正股）",
        "cb_options_help":     "获取期权链，建议 LEAP vs 正股",
        "div_depth":           "分析深度",
        "depth_0":             "⚡ 浅析",
        "depth_1":             "⚖️ 标准",
        "depth_2":             "🔬 深度",
        "depth_hint_0":        "1轮辩论 · 1轮风险",
        "depth_hint_1":        "1轮辩论 · 2轮风险",
        "depth_hint_2":        "2轮辩论 · 3轮风险",
        "div_model":           "模型",
        "model_quick":         "快速（分析师）",
        "model_deep":          "深度（PM & 研究）",
        "div_lang":            "输出语言",
        "run_btn":             "🚀  开始分析",
        "no_analyst_warn":     "请至少选择一个分析师。",
        "run_hint":            "💡 首次运行约3-5分钟 · 结果自动保存至 reports/",
        # New Analysis landing
        "landing_info":        "在侧边栏配置分析参数，点击**开始分析**。",
        "how_it_works":        "#### 工作原理",
        "how_steps":           "1. **分析师**拉取实时市场数据\n2. **多空**双方辩论投资逻辑\n3. **交易员**制定交易方案\n4. **风险团队**压力测试仓位\n5. **投资组合经理** → 买入 / 持有 / 卖出",
        "agent_pipeline":      "#### 智能体流程",
        # Running
        "analyzing":           "正在分析",
        "elapsed":             "已用时",
        "steps":               "步骤",
        "initializing":        "正在初始化智能体…",
        # Result
        "analysis_date":       "分析日期：",
        "analysis_failed":     "分析失败：",
        "completed_cap":       "完成：**{ticker}** · {date} · 在侧边栏修改代码/日期可重新运行。",
        # Result tabs
        "tab_final":           "最终决策",
        "tab_trader":          "交易方案",
        "tab_research":        "研究经理",
        "tab_market":          "市场",
        "tab_news":            "新闻",
        "tab_fundamentals":    "基本面",
        "tab_valuation":       "估值",
        "tab_macro":           "宏观",
        "tab_options":         "期权",
        "tab_sentiment":       "情绪",
        "tab_risk":            "风险辩论",
        "no_final":            "_无最终决策记录。_",
        "no_market":           "_市场分析师未启用。_",
        "no_news":             "_新闻分析师未启用。_",
        "no_fund":             "_基本面分析师未启用。_",
        "no_val":              "_估值分析师未启用。_",
        "no_macro":            "_宏观分析师未启用。_",
        "no_opt":              "_期权分析师未启用。请在侧边栏启用「期权（LEAP vs 正股）」。_",
        "no_sent":             "_情绪分析师未启用。_",
        # Browse Reports
        "browse_title":        "### 📂 浏览报告",
        "no_reports":          "暂无报告，请先运行分析。",
        "no_reports2":         "暂无报告。",
        "mode_view":           "📄 查看报告",
        "mode_compare":        "📊 对比日期",
        "mode_delete":         "🗑️ 删除",
        "del_warn":            "选择要永久删除的报告。",
        "del_ticker_lbl":      "股票代码",
        "del_date_lbl":        "日期",
        "del_will":            "**将删除：**",
        "del_confirm":         "🗑️ 确认删除",
        "del_success":         "已删除 {ticker} / {date}",
        "no_ticker_dates":     "此股票暂无报告。",
        "cmp_need2":           "需要至少2个日期才能对比。",
        "cmp_select":          "选择要对比的日期",
        "signal_timeline":     "#### 信号时间线",
        "key_points":          "#### 各日期关键点",
        "field_compare":       "对比字段",
        "ai_compare":          "#### 🤖 AI 对比分析",
        "ai_compare_cap":      "仅发送提取的摘要（约2KB），不发送完整报告。",
        "compare_btn":         "用 Claude 对比",
        "comparing":           "正在用 Claude 对比…",
        "no_summary":          "无 summary.json — 重新运行分析以生成",
        "overwrite_notice":    "💡 在 **{date}** 重新运行 **{ticker}** 将覆盖此报告。使用不同日期可保留两份。",
        "no_data_label":       "{label} 无数据。",
        "no_files":            "本节无保存文件。",
        "no_ticker_reports":   "{ticker} 无报告。",
        # Section / sub-tab labels
        "sec_analysts":        "I · 分析师",
        "sec_research":        "II · 研究",
        "sec_trading":         "III · 交易",
        "sec_risk":            "IV · 风险",
        "sec_portfolio":       "V · 投资组合",
        "sub_market":          "📈 市场",
        "sub_news":            "📰 新闻",
        "sub_fundamentals":    "🏢 基本面",
        "sub_valuation":       "🔢 估值",
        "sub_macro":           "🌐 宏观",
        "sub_sentiment":       "💬 情绪",
        "sub_options":         "💵 期权",
        "sub_bull":            "🟢 多方",
        "sub_bear":            "🔴 空方",
        "sub_manager":         "👔 研究经理",
        "sub_trader":          "🤝 交易员",
        "sub_aggressive":      "🔴 激进",
        "sub_conservative":    "🟢 保守",
        "sub_neutral":         "🟡 中性",
        "sub_decision":        "🏆 最终决策",
        # Signal Log
        "log_title":           "### 📊 信号记录",
        "no_signals":          "暂无信号记录。运行第一次分析后将自动创建。",
        "log_empty":           "信号记录为空。",
        "log_total":           "总计",
        "log_error":           "无法读取信号记录：",
        # SaaS Finder
        "saas_title":          "### 🔍 SaaS 筛选器 — 护城河四维度扫描",
        "saas_caption":        "使用 Claude 识别护城河最强的上市 SaaS 公司，评分维度：分销 · 专有数据 · 集成深度 · 合规壁垒。",
        "saas_how_title":      "📖 如何解读评分",
        "saas_explanation":    """\
**护城河四维度框架 — 每个维度评分 1–10，总分满分 40**

| 维度 | 评估内容 |
|------|---------|
| **分销护城河** | 客户切换成本、工作流集成深度、病毒式传播或企业合同覆盖 |
| **专有数据护城河** | 产品是否随使用越来越智能；竞争对手无法复制的独特数据集 |
| **集成深度护城河** | 关键业务集成数量（ERP/CRM）；替换复杂度；多产品套件锁定 |
| **合规护城河** | SOC 2、HIPAA、FedRAMP 认证形成的壁垒；受监管行业主导地位 |

**总分解读（/40）**
- 🟢 **30–40** — 强护城河：高度可防御的业务，优势持续复利增长
- 🟡 **22–29** — 中等护城河：有实质性优势，但面临竞争压力
- 🔴 **< 22** — 弱护城河：防御力有限，AI 颠覆风险较高

**AI 立场说明**
- **Builder（构建者）** — 在自有数据上开发专有AI；护城河随时间加深
- **Buyer（使用者）** — 使用第三方AI；护城河依赖数据与分销，而非AI本身""",
        "saas_n_label":        "公司数量",
        "saas_sector_label":   "行业筛选（可选）",
        "saas_sector_ph":      "例如 Fintech、HR-Tech、DevOps、Healthcare",
        "saas_submit":         "🔍 寻找 SaaS 护城河",
        "saas_spinner":        "正在运行 SaaS 筛选分析…（约需1-2分钟）",
        "saas_error":          "SaaS 筛选错误：",
        "saas_results_title":  "#### 护城河评分 Top {n} 公司",
        "saas_legend":         "🟢 ≥ 30 强护城河  ·  🟡 22–29 中等  ·  🔴 < 22 弱",
        "saas_detail_title":   "#### 详细分析",
        "saas_sector_lbl":     "**行业：**",
        "saas_ai_stance_lbl":  "**AI 立场：**",
        "saas_ai_data_adv":    "**AI 数据优势：**",
        "saas_ai_threat":      "**AI 威胁：**",
        "saas_core_thesis":    "**核心逻辑：**",
        "saas_key_risk":       "**主要风险：**",
        "dist_label":          "分销",
        "data_label":          "数据",
        "integ_label":         "集成",
        "reg_label":           "合规",
    },
}


def t(key: str, **kwargs) -> str:
    lang = st.session_state.get("ui_lang", "en")
    val = _T.get(lang, _T["en"]).get(key) or _T["en"].get(key, key)
    return val.format(**kwargs) if kwargs else val


# ── Sections structure (uses translation keys for labels) ──────────────────────
_SECTIONS = [
    ("sec_analysts",  "1_analysts",  "bar-chart", [
        ("market",       "sub_market"),
        ("news",         "sub_news"),
        ("fundamentals", "sub_fundamentals"),
        ("valuation",    "sub_valuation"),
        ("macro",        "sub_macro"),
        ("sentiment",    "sub_sentiment"),
        ("options",      "sub_options"),
    ]),
    ("sec_research",  "2_research",  "people", [
        ("bull",    "sub_bull"),
        ("bear",    "sub_bear"),
        ("manager", "sub_manager"),
    ]),
    ("sec_trading",   "3_trading",   "graph-up-arrow", [
        ("trader",  "sub_trader"),
    ]),
    ("sec_risk",      "4_risk",      "shield-exclamation", [
        ("aggressive",   "sub_aggressive"),
        ("conservative", "sub_conservative"),
        ("neutral",      "sub_neutral"),
    ]),
    ("sec_portfolio", "5_portfolio", "clipboard-check", [
        ("decision", "sub_decision"),
    ]),
]


def _img_b64(name: str) -> str:
    p = Path(__file__).parent / "assets" / name
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""

_logo_b64        = _img_b64("Starluke.png")
_desert_bg_b64   = _img_b64("Cominc3.png")
_rock_bg_b64     = _img_b64("comic7.png")
_light_bg_b64    = _img_b64("微信图片_20260424015903_165_2.jpg")
_rainbow_bg_b64  = _img_b64("rainbow.png")
_illus_b64       = _img_b64("1.png")

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
if "theme"        not in st.session_state: st.session_state.theme        = _prefs.get("theme", "rock")
if "ui_lang"      not in st.session_state: st.session_state.ui_lang      = _prefs.get("ui_lang", "en")
if "result"       not in st.session_state: st.session_state.result       = None
if "running"      not in st.session_state: st.session_state.running      = False
if "nav"          not in st.session_state: st.session_state.nav          = "New Analysis"
if "username"     not in st.session_state: st.session_state.username     = _prefs.get("username", "")
if "saas_results" not in st.session_state: st.session_state.saas_results = None
if "saas_running" not in st.session_state: st.session_state.saas_running = False

# Inject active theme
_css_map = {"rock": ROCK_CSS, "light": LIGHT_CSS, "desert": DESERT_CSS, "rainbow": RAINBOW_CSS}
st.markdown(f"<style>{_css_map[st.session_state.theme]}</style>", unsafe_allow_html=True)

# Per-theme background image
_theme_bg = {
    "rock":    (_rock_bg_b64,   "image/png",  "0.45"),
    "light":   (_light_bg_b64,  "image/jpeg", "0.35"),
    "desert":  (_desert_bg_b64, "image/png",  "0.40"),
    "rainbow": (_rainbow_bg_b64, "image/png",  "0.45"),
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
    html, body, [data-testid="stAppViewContainer"] {{
        background-image: {_wc_bg_url} !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
        min-height: 100vh !important;
    }}
    [data-testid="stAppViewContainer"]::after {{
        content: "";
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.35);
        pointer-events: none;
        z-index: 0;
    }}
    [data-testid="stMain"],
    [data-testid="stMain"] > div {{ background: transparent !important; }}
    [data-testid="block-container"] {{
        padding-top: 10vh !important;
        max-width: 500px !important;
        position: relative;
        z-index: 1;
    }}
    [data-testid="block-container"] > div:first-child {{
        background: rgba(8, 12, 20, 0.55) !important;
        border: 1px solid rgba(255,255,255,0.13) !important;
        border-radius: 20px !important;
        padding: 36px 40px 32px !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        box-shadow: 0 8px 48px rgba(0,0,0,0.5) !important;
    }}
    .wc-logo {{ display: block; width: 100%; max-width: 460px; margin: 0 auto 6px; filter: drop-shadow(0 0 32px #36cfc977); }}
    .wc-sub {{ text-align: center; font-size: 1.05rem; letter-spacing: 4px; text-transform: uppercase; color: #ddd; margin-bottom: 24px; font-weight: 500; }}
    [data-testid="stTextInput"] label p {{ font-size: 1.25rem !important; font-weight: 600 !important; color: #eee !important; letter-spacing: 1px !important; margin-bottom: 6px !important; }}
    </style>
    """, unsafe_allow_html=True)

    if _logo_b64:
        st.markdown(f'<img class="wc-logo" src="data:image/png;base64,{_logo_b64}" alt="STARLUKE">', unsafe_allow_html=True)
    st.markdown(f'<div class="wc-sub">{t("wc_sub")}</div>', unsafe_allow_html=True)
    name_input = st.text_input(t("wc_name_label"), placeholder=t("wc_name_placeholder"), label_visibility="visible")
    if st.button(t("wc_enter"), use_container_width=True, type="primary"):
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

def _read_signal_from_folder(base: Path) -> str:
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
        st.info(t("no_reports"))
        return
    tickers = sorted([p.name for p in reports_dir.iterdir()
                      if p.is_dir() and p.name not in ("signal_log.csv", "saas_finder")])
    if not tickers:
        st.info(t("no_reports2"))
        return

    _mode_labels = [t("mode_view"), t("mode_compare"), t("mode_delete")]
    mode = sac.segmented(
        items=[sac.SegmentedItem(label=l) for l in _mode_labels],
        label=None, size="xs", color="#36cfc9",
    )

    # ══ Delete ════════════════════════════════════════════════════════════════
    if mode == t("mode_delete"):
        st.warning(t("del_warn"))
        c1, c2 = st.columns([1, 1])
        with c1:
            del_ticker = st.selectbox(t("del_ticker_lbl"), tickers, key="del_tick")
        ticker_dir = reports_dir / del_ticker
        dates = sorted([p.name for p in ticker_dir.iterdir() if p.is_dir()], reverse=True)
        if not dates:
            st.info(t("no_ticker_dates"))
            return
        with c2:
            del_date = st.selectbox(t("del_date_lbl"), dates, key="del_date")
        target = ticker_dir / del_date
        st.markdown(f"{t('del_will')} `{target}`")
        if st.button(t("del_confirm"), type="primary"):
            shutil.rmtree(target, ignore_errors=True)
            remaining = [p for p in ticker_dir.iterdir() if p.is_dir()]
            if not remaining:
                ticker_dir.rmdir()
            st.success(t("del_success", ticker=del_ticker, date=del_date))
            st.rerun()
        return

    # ══ Compare Dates ══════════════════════════════════════════════════════════
    if mode == t("mode_compare"):
        import json as _json, subprocess as _sp

        c1, c2 = st.columns([1, 2])
        with c1:
            cmp_ticker = st.selectbox(t("del_ticker_lbl"), tickers, key="cmp_tick")
        ticker_dir = reports_dir / cmp_ticker
        dates = sorted([p.name for p in ticker_dir.iterdir() if p.is_dir()], reverse=True)
        if len(dates) < 2:
            st.info(t("cmp_need2"))
            return
        with c2:
            cmp_dates = st.multiselect(t("cmp_select"), dates, default=dates[:min(4, len(dates))])
        if not cmp_dates:
            return

        sorted_dates = sorted(cmp_dates)
        summaries = {}
        for d in sorted_dates:
            sj = ticker_dir / d / "summary.json"
            if sj.exists():
                summaries[d] = _json.loads(sj.read_text(encoding="utf-8"))
            else:
                summaries[d] = {"date": d, "signal": _read_signal_from_folder(ticker_dir / d), "_no_summary": True}

        st.markdown(t("signal_timeline"))
        sig_cols = st.columns(len(sorted_dates))
        _sig_icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
        for i, d in enumerate(sorted_dates):
            sig = summaries[d].get("signal", "—")
            sig_cols[i].metric(d, f"{_sig_icon.get(sig, '')} {sig}")

        st.divider()
        st.markdown(t("key_points"))
        _COMPARE_FIELDS = [
            ("bull_thesis",           "🟢 Bull Thesis"),
            ("bear_thesis",           "🔴 Bear Thesis"),
            ("trader_plan",           "🤝 Trader Plan"),
            ("final_decision",        "🏆 PM Decision"),
            ("analysts.market",       "📈 Market"),
            ("analysts.news",         "📰 News"),
            ("analysts.fundamentals", "🏢 Fundamentals"),
        ]
        field_choice = st.selectbox(t("field_compare"), [label for _, label in _COMPARE_FIELDS], key="cmp_field")
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
                    st.caption(t("no_summary"))
                else:
                    val = _get_field(summaries[d], chosen_key)
                    st.markdown(val or "_empty_")

        st.divider()
        st.markdown(t("ai_compare"))
        st.caption(t("ai_compare_cap"))

        if st.button(t("compare_btn"), type="primary"):
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
            with st.spinner(t("comparing")):
                try:
                    from tradingagents.llm_clients.claude_cli_client import find_claude_exe
                    proc = _sp.Popen(
                        [find_claude_exe(), "--output-format", "text", "--dangerously-skip-permissions", "-p", prompt],
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

    # ══ View Report ════════════════════════════════════════════════════════════
    c1, c2 = st.columns([1, 1])
    with c1:
        selected_ticker = st.selectbox(t("del_ticker_lbl"), tickers)
    ticker_dir = reports_dir / selected_ticker
    dates = sorted([p.name for p in ticker_dir.iterdir() if p.is_dir()], reverse=True)
    if not dates:
        st.info(t("no_ticker_reports", ticker=selected_ticker))
        return
    with c2:
        selected_date = st.selectbox(t("del_date_lbl"), dates)

    st.caption(t("overwrite_notice", ticker=selected_ticker, date=selected_date))

    base = ticker_dir / selected_date

    # Build translated section labels
    sec_labels = [t(sk) for sk, _, _, _ in _SECTIONS]
    section_tab = sac.tabs(
        [sac.TabsItem(lbl, icon=icon) for lbl, (_, _, icon, _) in zip(sec_labels, _SECTIONS)],
        color="#36cfc9", size="sm", align="start",
    )
    for (sk, folder, _, files), lbl in zip(_SECTIONS, sec_labels):
        if section_tab != lbl:
            continue
        section_dir = base / folder
        if not section_dir.exists():
            st.info(t("no_data_label", label=lbl))
            break
        available = [(stem, t(tk)) for stem, tk in files if (section_dir / f"{stem}.md").exists()]
        if not available:
            st.info(t("no_files"))
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
        st.info(t("no_signals"))
        return
    try:
        df = pd.read_csv(log_path)
        if df.empty:
            st.info(t("log_empty"))
            return
        def color_signal(val):
            if val == "BUY":  return "color:#00e676;font-weight:bold"
            if val == "SELL": return "color:#ff1744;font-weight:bold"
            return "color:#ffb800;font-weight:bold"
        st.dataframe(df.style.map(color_signal, subset=["signal"]), width="stretch")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t("log_total"), len(df))
        c2.metric("BUY",  int((df.signal == "BUY").sum()))
        c3.metric("SELL", int((df.signal == "SELL").sum()))
        c4.metric("HOLD", int((df.signal == "HOLD").sum()))
    except Exception as e:
        st.error(f"{t('log_error')} {e}")


def _render_saas_finder_page():
    st.markdown(t("saas_title"))
    st.caption(t("saas_caption"))

    with st.expander(t("saas_how_title"), expanded=True):
        st.markdown(t("saas_explanation"))

    with st.form("saas_finder_form"):
        col1, col2 = st.columns([2, 3])
        with col1:
            n = st.slider(t("saas_n_label"), min_value=1, max_value=15, value=5)
        with col2:
            sector_hint = st.text_input(t("saas_sector_label"), placeholder=t("saas_sector_ph"))
        submitted = st.form_submit_button(t("saas_submit"), type="primary", use_container_width=True)

    if submitted and not st.session_state.saas_running:
        st.session_state.saas_results = None
        st.session_state.saas_running = True
        status_box = st.empty()

        def _cb(msg: str):
            status_box.info(msg)

        try:
            from tradingagents.saas_finder import run_saas_finder
            with st.spinner(t("saas_spinner")):
                results = run_saas_finder(n=n, sector_hint=sector_hint.strip(), progress_cb=_cb)
            st.session_state.saas_results = results
        except Exception as e:
            st.error(f"{t('saas_error')} {e}")
        finally:
            st.session_state.saas_running = False
            status_box.empty()

    results = st.session_state.saas_results
    if results:
        import pandas as pd

        st.markdown(t("saas_results_title", n=len(results)))
        st.caption(t("saas_legend"))

        rows = []
        for r in results:
            rows.append({
                "Ticker":          r.get("ticker", "?"),
                "Company":         r.get("company", "?"),
                "Sector":          r.get("sector", "?"),
                t("dist_label"):   r.get("moat_distribution", 0),
                t("data_label"):   r.get("moat_data", 0),
                t("integ_label"):  r.get("moat_integration", 0),
                t("reg_label"):    r.get("moat_regulatory", 0),
                "Total /40":       r.get("moat_total", 0),
                "AI Stance":       r.get("ai_stance", "?"),
            })
        df = pd.DataFrame(rows)

        def _color_total(val):
            if isinstance(val, (int, float)):
                if val >= 30: return "color:#00e676;font-weight:bold"
                if val >= 22: return "color:#ffb800;font-weight:bold"
                return "color:#ff5252"
            return ""

        st.dataframe(df.style.map(_color_total, subset=["Total /40"]), width="stretch")

        st.divider()
        st.markdown(t("saas_detail_title"))
        for r in results:
            with st.expander(f"**{r.get('ticker','?')}** — {r.get('company','?')} (Total: {r.get('moat_total',0)}/40)"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("dist_label"),  f"{r.get('moat_distribution', 0)}/10")
                c2.metric(t("data_label"),  f"{r.get('moat_data', 0)}/10")
                c3.metric(t("integ_label"), f"{r.get('moat_integration', 0)}/10")
                c4.metric(t("reg_label"),   f"{r.get('moat_regulatory', 0)}/10")
                st.markdown(f"{t('saas_sector_lbl')} {r.get('sector','?')}  |  {t('saas_ai_stance_lbl')} {r.get('ai_stance','?')}")
                st.markdown(f"{t('saas_ai_data_adv')} {r.get('ai_data_advantage','?')}  |  {t('saas_ai_threat')} {r.get('ai_threat','?')}")
                st.info(f"{t('saas_core_thesis')} {r.get('core_thesis','?')}")
                st.warning(f"{t('saas_key_risk')} {r.get('key_risk','?')}")


def run_analysis(ticker, trade_date, analysts,
                 quick_model="claude-cli", deep_model="claude-cli",
                 output_language="English", depth_cfg=None):
    depth_cfg = depth_cfg or _DEPTH_CFG[1]

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
        ta = TradingAgentsGraph(selected_analysts=analysts, debug=False, config=config)
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
    if _logo_b64:
        st.markdown(f"""
        <div class="logo-wrap">
            <img src="data:image/png;base64,{_logo_b64}" alt="STARLUKE">
            <div class="logo-sub">{t("logo_sub")}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        f"<div style='text-align:center;padding:8px 0 4px;'>"
        f"<div style='font-size:0.75rem;color:#888;letter-spacing:2px;text-transform:uppercase;margin-bottom:2px;'>{t('welcome_back')}</div>"
        f"<div style='font-size:1.35rem;font-weight:700;color:#36cfc9;'>{st.session_state.username}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button(t("change_name"), use_container_width=True, key="change_name_btn"):
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

    # UI Language toggle
    sac.divider(label=t("div_ui_lang"), align="center", color="#333")
    lang_ui_choice = sac.segmented(
        items=[sac.SegmentedItem(label="🇺🇸 EN"), sac.SegmentedItem(label="🇨🇳 中文")],
        label=None, size="xs", color="#36cfc9", use_container_width=True,
        index=0 if st.session_state.ui_lang == "en" else 1,
    )
    _new_ui_lang = "zh" if lang_ui_choice == "🇨🇳 中文" else "en"
    if _new_ui_lang != st.session_state.ui_lang:
        st.session_state.ui_lang = _new_ui_lang
        _save_prefs(ui_lang=_new_ui_lang)
        st.rerun()

    # Navigation menu
    _NAV_EN    = ["New Analysis", "SaaS Finder", "Browse Reports", "Signal Log"]
    _NAV_ICONS = ["rocket-takeoff", "search", "folder2-open", "bar-chart-line"]
    _nav_labels = [t("nav_new"), t("nav_saas"), t("nav_browse"), t("nav_log")]
    nav = sac.menu([
        sac.MenuItem(lbl, icon=icon)
        for lbl, icon in zip(_nav_labels, _NAV_ICONS)
    ], color="#36cfc9", size="sm", indent=16, open_all=True)
    if nav:
        try:
            st.session_state.nav = _NAV_EN[_nav_labels.index(nav)]
        except ValueError:
            pass

    sac.divider(label=t("div_config"), align="center", color="#333")

    ticker = st.text_input(
        t("ticker_label"), value="AAPL", placeholder=t("ticker_placeholder")
    ).upper().strip()

    # Default to last weekday (skip Saturday → Friday, Sunday → Friday)
    _yesterday = date.today() - timedelta(days=1)
    _default_date = _yesterday - timedelta(days=max(0, _yesterday.weekday() - 4))
    trade_date = st.date_input(
        t("date_label"),
        value=_default_date,
        max_value=date.today(),
    )
    if trade_date.weekday() >= 5:
        st.warning("⚠️ Weekend — markets closed. No price data available. Select a weekday." if st.session_state.ui_lang == "en"
                   else "⚠️ 周末市场休市，无行情数据，请选择工作日。")

    sac.divider(label=t("div_analysts"), align="center", color="#333")

    use_market       = st.checkbox(t("cb_market"),       value=True)
    use_news         = st.checkbox(t("cb_news"),         value=True)
    use_fundamentals = st.checkbox(t("cb_fundamentals"), value=True)
    use_valuation    = st.checkbox(t("cb_valuation"),    value=True,  help=t("cb_valuation_help"))
    use_macro        = st.checkbox(t("cb_macro"),        value=True,  help=t("cb_macro_help"))
    use_social       = st.checkbox(t("cb_social"),       value=False, help=t("cb_social_help"))
    use_options      = st.checkbox(t("cb_options"),      value=False, help=t("cb_options_help"))

    selected_analysts = (
        (["market"]       if use_market       else []) +
        (["news"]         if use_news         else []) +
        (["fundamentals"] if use_fundamentals else []) +
        (["valuation"]    if use_valuation    else []) +
        (["macro"]        if use_macro        else []) +
        (["social"]       if use_social       else []) +
        (["options"]      if use_options      else [])
    )

    sac.divider(label=t("div_depth"), align="center", color="#333")
    _depth_labels = [t("depth_0"), t("depth_1"), t("depth_2")]
    depth_choice = sac.segmented(
        items=[sac.SegmentedItem(label=l) for l in _depth_labels],
        label=None, size="xs", color="#36cfc9", use_container_width=True,
        index=1,
    )
    depth_idx = _depth_labels.index(depth_choice) if depth_choice in _depth_labels else 1
    selected_depth_cfg = _DEPTH_CFG[depth_idx]
    st.caption(t(f"depth_hint_{depth_idx}"))

    sac.divider(label=t("div_model"), align="center", color="#333")

    from tradingagents.llm_clients.model_catalog import get_model_options
    _qopts = get_model_options("claude_cli", "quick")
    _dopts = get_model_options("claude_cli", "deep")
    quick_model = dict(_qopts)[st.selectbox(t("model_quick"), [l for l,_ in _qopts], index=0)]
    deep_model  = dict(_dopts)[st.selectbox(t("model_deep"),  [l for l,_ in _dopts], index=0)]

    sac.divider(label=t("div_lang"), align="center", color="#333")
    lang_choice = sac.segmented(
        items=[sac.SegmentedItem(label="🇺🇸 English"), sac.SegmentedItem(label="🇨🇳 中文")],
        label=None, size="xs", color="#36cfc9", use_container_width=True,
        index=0,
    )
    output_language = "Chinese" if lang_choice == "🇨🇳 中文" else "English"

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    run_btn = st.button(
        t("run_btn"), use_container_width=True, type="primary",
        disabled=not ticker or not selected_analysts or st.session_state.running,
    )
    if not selected_analysts:
        st.warning(t("no_analyst_warn"))

    if st.session_state.running:
        if st.button("⏹ Stop / 强制停止", use_container_width=True):
            with _RUN_LOCK:
                _RUN["done"] = True
                _RUN["result"] = {"error": "Cancelled by user.", "state": None}
            st.session_state.running = False
            st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.caption(t("run_hint"))


# ── MAIN AREA ──────────────────────────────────────────────────────────────────
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
        position: relative; width: 100%; border-radius: 16px; overflow: hidden;
        margin-bottom: 28px; display: flex; align-items: center; justify-content: center;
        min-height: 220px; background: {_banner_bg}; border: 1px solid var(--sl-border);
    }}
    .hero-banner::before {{
        content: ""; position: absolute; inset: 0;
        background-image: url("data:image/png;base64,{_logo_b64}");
        background-size: 55%; background-repeat: no-repeat; background-position: center;
        opacity: 0.07; filter: blur(1px);
    }}
    .hero-banner img {{
        position: relative; z-index: 1; width: 62%; max-width: 740px; min-width: 280px;
        height: auto; mix-blend-mode: {_banner_blend};
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
    _total = _n_analysts + 2 * _dr + 1 + 1 + 3 * _rr + 1

    # Build the expected node order so the UI can show "currently running X"
    # even before any callbacks fire (each analyst takes 10-20 min on first run).
    _analyst_label_map = {
        "market": "📈 Market Analyst", "news": "📰 News Analyst",
        "fundamentals": "🏢 Fundamentals Analyst", "valuation": "🔢 Valuation Analyst",
        "macro": "🌐 Macro Analyst", "social": "💬 Social Analyst",
        "options": "💵 Options Analyst",
    }
    _pipeline = (
        [_analyst_label_map.get(a, a.capitalize()) for a in selected_analysts]
        + ["🟢 Bull Researcher", "🔴 Bear Researcher"] * _dr
        + ["👔 Research Manager", "🤝 Trader"]
        + ["🔴 Risk · Aggressive", "🟢 Risk · Conservative", "🟡 Risk · Neutral"] * _rr
        + ["🏆 Portfolio Manager"]
    )

    with _RUN_LOCK:
        _RUN.update({"active": True, "progress": [], "result": None, "done": False,
                     "error": None, "pipeline": _pipeline})
    st.session_state.result       = None
    st.session_state.running      = True
    st.session_state.nav          = "New Analysis"
    st.session_state._run_ticker  = ticker
    st.session_state._run_date    = str(trade_date)
    st.session_state._run_total   = _total
    st.session_state._run_started = time.time()
    threading.Thread(
        target=run_analysis,
        args=(ticker, trade_date, selected_analysts, quick_model, deep_model,
              output_language, selected_depth_cfg),
        daemon=True,
    ).start()
    st.rerun()

# ── Poll for completion ────────────────────────────────────────────────────────
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
    st.markdown(t("browse_title"))
    _render_browse_reports()

elif page == "Signal Log":
    st.markdown(t("log_title"))
    _render_signal_log()

elif page == "SaaS Finder":
    _render_saas_finder_page()

else:
    # ── New Analysis page ──────────────────────────────────────────────────────
    result = st.session_state.result

    if st.session_state.running:
        with _RUN_LOCK:
            _prog     = list(_RUN["progress"])
            _pipeline = list(_RUN.get("pipeline", []))
        _total   = st.session_state.get("_run_total", 15)
        _ticker  = st.session_state.get("_run_ticker", "")
        _rdate   = st.session_state.get("_run_date", "")
        _elapsed = int(time.time() - st.session_state.get("_run_started", time.time()))
        _mins, _secs = divmod(_elapsed, 60)

        # Which node is currently running = next one after all completed ones
        _n_done = len(_prog)
        _current_node = _pipeline[_n_done] if _n_done < len(_pipeline) else None

        # Wrap all dynamic content in a single st.empty() so Streamlit
        # replaces ONE node on each rerun instead of removing/adding several
        # — prevents the React "removeChild" DOM crash on rapid reruns.
        _prog_slot = st.empty()
        with _prog_slot.container():
            st.markdown(
                f"<h3 style='margin-bottom:4px;'>⏳ {t('analyzing')} <span style='color:#36cfc9'>{_ticker}</span>"
                f" &nbsp;·&nbsp; {_rdate}</h3>"
                f"<div style='color:var(--sl-muted);font-size:0.85rem;margin-bottom:16px;'>"
                f"{t('elapsed')}: {_mins:02d}:{_secs:02d} &nbsp;·&nbsp; {_n_done}/{_total} {t('steps')}</div>",
                unsafe_allow_html=True,
            )
            st.progress(min(_n_done / max(_total, 1), 0.99))

            # Build step list: completed ✅ + current ⚙️ (from pipeline, even before callback fires)
            _rows = "".join(
                f"<div style='padding:3px 0;font-size:0.88rem;'>✅ {s}</div>"
                for s in _prog
            )
            if _current_node:
                _rows += (
                    f"<div style='padding:4px 0;font-size:0.92rem;font-weight:600;"
                    f"color:#36cfc9;'>⚙️ {_current_node}"
                    f" &nbsp;<span style='opacity:0.6;font-size:0.8rem;'>running…</span></div>"
                )
            if _rows:
                st.markdown(
                    f"<div style='border:1px solid var(--sl-border);border-radius:10px;"
                    f"padding:12px 18px;margin-top:8px;'>{_rows}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"<div style='color:var(--sl-muted);font-size:0.88rem;'>{t('initializing')}</div>", unsafe_allow_html=True)

        time.sleep(3)
        st.rerun()

    elif result is None:
        st.info(t("landing_info"))
        col_img, col_how, col_pipe = st.columns([1.5, 1, 1])

        with col_img:
            if _illus_b64:
                st.markdown(f"""
                <img src="data:image/png;base64,{_illus_b64}"
                     style="width:100%; border-radius:12px; margin-top:8px;
                            opacity:0.93; filter:drop-shadow(0 4px 20px #0009);">
                """, unsafe_allow_html=True)

        with col_how:
            st.markdown(t("how_it_works"))
            st.markdown(t("how_steps"))

        with col_pipe:
            st.markdown(t("agent_pipeline"))
            st.markdown("""\
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
```""")

    elif result.get("error"):
        st.error(f"{t('analysis_failed')} {result['error']}")

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
            <div class="sig-sub">{t('analysis_date')} {date_label}</div>
        </div>
        """, unsafe_allow_html=True)

        tab = sac.tabs([
            sac.TabsItem(t("tab_final"),        icon="clipboard-check"),
            sac.TabsItem(t("tab_trader"),        icon="graph-up-arrow"),
            sac.TabsItem(t("tab_research"),      icon="people"),
            sac.TabsItem(t("tab_market"),        icon="bar-chart"),
            sac.TabsItem(t("tab_news"),          icon="newspaper"),
            sac.TabsItem(t("tab_fundamentals"),  icon="building"),
            sac.TabsItem(t("tab_valuation"),     icon="calculator"),
            sac.TabsItem(t("tab_macro"),         icon="globe"),
            sac.TabsItem(t("tab_options"),       icon="currency-dollar"),
            sac.TabsItem(t("tab_sentiment"),     icon="chat-square-text"),
            sac.TabsItem(t("tab_risk"),          icon="shield-exclamation"),
        ], color="#36cfc9", size="sm", align="start")

        def show(key, fallback="_Not available_"):
            txt = state.get(key, "")
            st.markdown(txt if txt else fallback)

        if tab == t("tab_final"):
            show("final_trade_decision", t("no_final"))
        elif tab == t("tab_trader"):
            show("trader_investment_plan")
        elif tab == t("tab_research"):
            ids = state.get("investment_debate_state", {})
            bull_txt = ids.get("bull_history", "") or ids.get("current_response", "")
            bear_txt = ids.get("bear_history", "")
            mgr_txt  = state.get("investment_plan", "")

            c1, c2 = st.columns(2)
            with c1:
                sac.divider(label="🟢 Bull Case", color="#00e676")
                st.markdown((bull_txt[:4000] + ("…" if len(bull_txt) > 4000 else "")) if bull_txt else "_Not available_")
            with c2:
                sac.divider(label="🔴 Bear Case", color="#ff1744")
                st.markdown((bear_txt[:4000] + ("…" if len(bear_txt) > 4000 else "")) if bear_txt else "_Not available_")

            sac.divider(label="👔 Research Manager Decision", color="#36cfc9")
            st.markdown(mgr_txt if mgr_txt else "_Not available_")
        elif tab == t("tab_market"):
            show("market_report", t("no_market"))
        elif tab == t("tab_news"):
            show("news_report", t("no_news"))
        elif tab == t("tab_fundamentals"):
            show("fundamentals_report", t("no_fund"))
        elif tab == t("tab_valuation"):
            show("valuation_report", t("no_val"))
        elif tab == t("tab_macro"):
            show("macro_report", t("no_macro"))
        elif tab == t("tab_options"):
            show("options_report", t("no_opt"))
        elif tab == t("tab_sentiment"):
            show("sentiment_report", t("no_sent"))
        elif tab == t("tab_risk"):
            rds = state.get("risk_debate_state", {})

            # Show full debate histories (fall back to current_* if history empty)
            def _risk_txt(history_key, current_key):
                h = rds.get(history_key, "")
                if h and len(h) > 20:
                    return h
                return rds.get(current_key, "") or "_Not available_"

            c1, c2, c3 = st.columns(3)
            with c1:
                sac.divider(label="🔴 Aggressive", color="#ff1744")
                agg = _risk_txt("aggressive_history", "current_aggressive_response")
                st.markdown(agg[:4000] + ("…" if len(agg) > 4000 else ""))
            with c2:
                sac.divider(label="🟡 Neutral", color="#ffb800")
                neu = _risk_txt("neutral_history", "current_neutral_response")
                st.markdown(neu[:4000] + ("…" if len(neu) > 4000 else ""))
            with c3:
                sac.divider(label="🟢 Conservative", color="#00e676")
                con = _risk_txt("conservative_history", "current_conservative_response")
                st.markdown(con[:4000] + ("…" if len(con) > 4000 else ""))

            judge = rds.get("judge_decision", "")
            if judge:
                sac.divider(label="⚖️ Risk Judge Decision", color="#36cfc9")
                st.markdown(judge)

        st.divider()
        st.caption(t("completed_cap", ticker=ticker_label, date=date_label))
