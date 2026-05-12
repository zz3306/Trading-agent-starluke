<p align="center">
  <img src="assets/Starluke.png" alt="STARLUKE" width="620" />
</p>

<p align="center">
  <strong>Multi-Agent LLM Stock Analysis — Zero API Cost</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude_CLI-No_API_Key-blueviolet?style=flat-square&logo=anthropic" />
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python" />
  <img src="https://img.shields.io/badge/Platform-Win%20%7C%20Mac%20%7C%20Linux-lightgrey?style=flat-square" />
  <img src="https://img.shields.io/badge/Data-yfinance%20%28free%29-green?style=flat-square" />
  <img src="https://img.shields.io/badge/Output-EN%20%7C%20中文%20%7C%20日本語-orange?style=flat-square" />
</p>

<p align="center">
  <img src="assets/rainbow.png" alt="" width="480" />
</p>

<p align="center">
  <a href="https://htmlpreview.github.io/?https://raw.githubusercontent.com/zz3306/Trading-agent-starluke/main/sample_output.html"><strong>📄 View sample output →</strong></a>
  <br/>
  <sub>Condensed excerpt from real DIS &amp; GOOG analysis runs — shows report structure and bilingual EN/中文 toggle</sub>
</p>

---

Run a full institutional-grade stock analysis pipeline entirely through your local [Claude Code](https://claude.ai/code) session. No Anthropic API key. No OpenAI key. Just your existing Claude login.

---

## What it does

STARLUKE deploys a team of specialized AI agents that mirror a real trading firm's workflow:

```
Analyst Team  →  Research Debate  →  Trader  →  Risk Debate  →  Portfolio Manager
```

Each agent has a defined role. They debate, challenge each other's assumptions, and the Portfolio Manager issues a final **BUY / HOLD / SELL** verdict with a full written rationale.

### Agent roster

| Team | Agent | What it analyses |
|------|-------|-----------------|
| Analyst | **Market Analyst** | RSI, MACD, Bollinger Bands, support/resistance, volume |
| Analyst | **Fundamentals Analyst** | Revenue, margins, cash flow, balance sheet, key ratios |
| Analyst | **Valuation Analyst** | 3–4 peer comparison table, P/E, EV/Revenue, stock personality classification |
| Analyst | **News Analyst** | Earnings events, macro news, regulatory & competitive developments |
| Analyst | **Social Media Analyst** | Market sentiment from news sources |
| Analyst | **Macro Analyst** | Interest rates, VIX, yield curve, sector rotation |
| Analyst | **Options Analyst** | LEAP vs outright stock recommendation, IV analysis |
| Research | **Bull Researcher** | Builds the bullish investment case |
| Research | **Bear Researcher** | Builds the bearish counter-case |
| Research | **Research Manager** | Weighs both sides, produces an investment plan |
| Trading | **Trader** | Converts research into a specific trade proposal |
| Risk | **Aggressive Analyst** | Advocates for the high-reward path |
| Risk | **Neutral Analyst** | Balances risk and reward |
| Risk | **Conservative Analyst** | Argues for capital preservation |
| Portfolio | **Portfolio Manager** | Final BUY / HOLD / SELL with position sizing |

---

## Sample output

[View a live demo →](https://htmlpreview.github.io/?https://raw.githubusercontent.com/zz3306/Trading-agent-starluke/main/sample_output.html) — condensed excerpt from real DIS & GOOG runs. Shows report structure and bilingual EN / 中文 toggle.

---

## Key features

| Feature | Detail |
|---------|--------|
| 🔑 **No API key** | All LLM calls route through the local `claude` CLI subprocess — your subscription covers it |
| 📊 **Free market data** | yfinance (OHLCV, fundamentals, options chain, news) — no data vendor key needed |
| 🌏 **Multi-language output** | Reports in English, 中文, 日本語, 한국어, Español, Français, Deutsch and more |
| ⚖️ **AI stock comparison** | Compare 2–5 already-analysed companies — get a ranked buy list and allocation recommendation |
| 💾 **Smart analyst cache** | Re-running the same ticker on the same date skips completed analysts instantly — language-aware |
| 📂 **Auto-save reports** | Every run saved to `reports/<TICKER>/<DATE>/` as structured Markdown files |
| 🖥️ **Rich CLI dashboard** | Live agent progress, tool-call log, streaming report display |
| 🌐 **Streamlit report browser** | Browse, read, and navigate all past reports in a web UI |
| 🔁 **Streamlit launch prompt** | After each analysis the CLI asks if you want to open the report browser immediately |
| 🧠 **Memory log** | Past decisions and outcomes are injected into the Portfolio Manager for self-improving context |

---

## Installation

Requires Python ≥ 3.10 and [Claude Code CLI](https://claude.ai/code).

```bash
# 1. Install Claude Code CLI (if not already done)
#    Mac/Linux:
npm install -g @anthropic-ai/claude-code
#    Windows: download the installer from https://claude.ai/code

# 2. Log in to Claude
claude login

# 3. Clone and install
git clone https://github.com/zz3306/Trading-agent-starluke.git
cd Trading-agent-starluke
pip install -e .

# Optional: Streamlit report browser
pip install streamlit streamlit-antd-components
```

---

## Usage

### Run a single-company analysis

```bash
tradingagents analyze
```

The CLI guides you through each step:

| Prompt | What to pick |
|--------|-------------|
| Ticker | `AAPL`, `NVDA`, `0700.HK`, etc. |
| Date | defaults to today |
| LLM provider | **Claude CLI** (no key needed) |
| Analyst team | any combination of the 7 analysts |
| Research depth | 1 = fast, 3 = thorough |
| Output language | English, 中文, or 10+ others |

After the run you are asked:
1. **Display full report?** — pretty-prints the report in the terminal
2. **Launch Streamlit UI?** — starts the report browser at `http://localhost:8501`

---

### Compare multiple companies

After running analyses for 2 or more tickers:

```bash
tradingagents compare
```

Select 2–5 companies, choose your language, and the AI produces:

- **Overall ranking** — most to least attractive right now
- **Per-stock plan** — BUY / HOLD / AVOID, entry level, timeframe, key catalyst
- **Risk & reward comparison** — lowest downside, highest upside, best portfolio pair
- **Final allocation** — suggested capital split across the selected stocks

The comparison report can be saved to `reports/comparison_A_vs_B_<date>.md`.

---

### Streamlit report browser

```bash
streamlit run app.py
# → open http://localhost:8501
```

Browse all past reports, view individual analyst sections, and navigate between tickers and dates.

---

### Python API

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "claude_cli"
config["output_language"] = "Chinese"
config["selected_analysts"] = ["market", "fundamentals", "valuation", "news"]

ta = TradingAgentsGraph(debug=False, config=config)
final_state, signal = ta.propagate("AAPL", "2025-01-15")
print(signal)  # BUY / HOLD / SELL
```

---

## Output structure

```
reports/AAPL/2025-01-15/
├── complete_report.md        ← full combined report
├── summary.json              ← machine-readable signal + snippets
├── 1_analysts/
│   ├── market.md
│   ├── fundamentals.md
│   ├── valuation.md          ← peer table + stock personality
│   ├── news.md
│   ├── sentiment.md
│   ├── macro.md
│   └── options.md            ← LEAP vs stock recommendation
├── 2_research/
│   ├── bull.md
│   ├── bear.md
│   └── manager.md
├── 3_trading/
│   └── trader.md
├── 4_risk/
│   ├── aggressive.md
│   ├── conservative.md
│   └── neutral.md
└── 5_portfolio/
    └── decision.md
```

---

## How the Claude CLI bridge works

Instead of calling the Anthropic REST API directly, STARLUKE shells out to the `claude` CLI subprocess — the same process that powers Claude Code:

```python
subprocess.Popen(
    ["claude", "--output-format", "text", "--dangerously-skip-permissions", "-p", prompt],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
)
```

Data tools (stock prices, financials, news) are pre-fetched in Python and injected into the prompt as context blocks, so no custom tool-calling protocol is needed.

---

## Model selection

In the CLI (Step 7) or web UI sidebar you can choose which Claude model to use:

| Slot | Suggestion | Used by |
|------|-----------|---------|
| Quick | `claude-sonnet-4-6` | All analysts, Trader, Risk team |
| Deep | `claude-opus-4-5` | Research Manager, Portfolio Manager |

Any model available in your Claude Code plan works.

---

## Troubleshooting

**`claude command not found`** — Install Claude Code CLI and re-open your terminal.

**Analysis produces `[ERROR]` in some sections** — Claude login session expired; run `claude login` again. The analyst cache will skip already-completed analysts on re-run.

**Valuation / Macro / Options missing from output** — Make sure you selected them in the analyst team step. They must be explicitly chosen each run.

**Streamlit won't start** — `pip install streamlit streamlit-antd-components` then `streamlit run app.py`.

---

## Credits

Built on top of [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache 2.0).

See [CHANGES.md](CHANGES.md) for a full list of modifications and additions in this fork.

---

## Disclaimer

For research and educational purposes only. Not financial advice.
