# TradingAgents — Usage Guide

> AI-powered stock analysis framework that runs entirely through your local Claude Code CLI session. No API key required.

---

## Prerequisites

### 1. Install Claude Code CLI
**Mac / Linux**
```bash
npm install -g @anthropic-ai/claude-code
claude login          # follow the browser prompt to authenticate
```

**Windows**
Download and run the installer from [claude.ai/code](https://claude.ai/code), then:
```powershell
claude login
```

### 2. Install Python dependencies
Requires Python ≥ 3.10.

```bash
cd TradingAgents
pip install -e .
```

If you also want the Streamlit report viewer:
```bash
pip install streamlit streamlit-antd-components
```

### 3. Verify setup
```bash
claude --version          # should print a version number
tradingagents --help      # should show available commands
```

---

## Running an Analysis

```bash
tradingagents analyze
```

The CLI will walk you through each step interactively:

| Step | What to choose |
|------|---------------|
| Ticker | e.g. `AAPL`, `NVDA`, `0700.HK` |
| Date | defaults to today |
| LLM provider | choose **Claude CLI** (no key needed) |
| Analyst team | pick from market / fundamentals / valuation / news / social / macro / options |
| Research depth | 1 = fast, 3 = thorough |
| Output language | English or Chinese (中文) |

The analysis runs in ~5–20 minutes depending on how many analysts you select.

### After the run
- Full report is auto-saved to `reports/<TICKER>/<DATE>/`
- You are prompted:
  1. **Display report on screen?** — pretty-prints the full report in the terminal
  2. **Launch Streamlit UI?** — opens the report browser at `http://localhost:8501`

---

## Comparing Multiple Companies

After running analyses for 2 or more companies, compare them:

```bash
tradingagents compare
```

1. A checklist shows all companies with existing reports — select 2–5
2. Choose output language (English / Chinese)
3. AI produces a side-by-side comparison with:
   - Overall ranking (most → least attractive)
   - Per-stock action plan (BUY / HOLD / AVOID + entry, timeframe, catalyst)
   - Risk & reward comparison
   - Final allocation recommendation
4. Optionally save the comparison as a Markdown file in `reports/`

---

## Launching the Report Viewer

```bash
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

The UI lets you browse all previously generated reports, compare key metrics, and view the complete analysis for each company.

---

## File Structure

```
TradingAgents/
├── app.py                  # Streamlit report viewer
├── cli/
│   ├── main.py             # CLI entry point  (tradingagents analyze / compare)
│   └── compare.py          # Compare command
├── tradingagents/
│   ├── agents/             # Analyst & researcher agents
│   ├── dataflows/          # Data fetching (yfinance, Alpha Vantage)
│   ├── graph/              # LangGraph workflow
│   └── llm_clients/        # Claude CLI adapter
└── reports/                # Auto-generated reports (gitignored)
```

---

## Configuration

All defaults live in `tradingagents/default_config.py`.

| Key | Default | Notes |
|-----|---------|-------|
| `llm_provider` | `claude_cli` | Uses local Claude Code session |
| `output_language` | `English` | Overridden per run |
| `max_debate_rounds` | `1` | Increase for deeper bull/bear debate |
| `max_risk_discuss_rounds` | `1` | Increase for deeper risk discussion |
| `data_vendors` | `yfinance` | Free, no key required |

---

## Troubleshooting

### `claude command not found`
- Make sure Claude Code CLI is installed: `npm install -g @anthropic-ai/claude-code`
- On Windows, re-open the terminal after installation so PATH updates take effect
- Run `claude --version` to confirm

### Analysis produces `[ERROR]` sections
- Your Claude login session may have expired — run `claude login` again
- If errors appear only in some agents but not all, it is usually a transient Claude CLI issue; re-run the analysis and the analyst cache will skip already-completed sections

### Valuation / Macro / Options not appearing in output
- Make sure you selected them in the analyst team step
- These three analysts were added after the initial release — older cached runs will not include them

### Streamlit won't start
```bash
pip install streamlit streamlit-antd-components
streamlit run app.py
```

---

## For Contributors / New Team Members

1. Clone the repo and follow the **Prerequisites** section above
2. Each person uses their **own** Claude Code login — no shared API key needed
3. `reports/`, `.tradingagents/`, and `signal_log.csv` are gitignored (personal data)
4. Run tests: `pytest tests/`

---

## 中文快速指南

```bash
# 安装依赖
pip install -e .

# 运行分析
tradingagents analyze
# → 按提示选择股票代码、日期、分析师团队、输出语言（中文）

# 对比多家公司
tradingagents compare
# → 选择 2–5 家已分析的公司，选择中文输出

# 启动报告浏览器
streamlit run app.py
# → 打开 http://localhost:8501
```

分析报告自动保存到 `reports/<股票代码>/<日期>/` 目录。每次分析结束后会询问是否启动 Streamlit 界面。
