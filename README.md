# STARLUKE

<p align="center">
  <img src="assets/Starluke.png" alt="STARLUKE" width="640" />
</p>

**Multi-Agent LLM Stock Analysis — Zero API Cost**

Run a full institutional-grade stock analysis pipeline entirely through your local [Claude Code](https://claude.ai/code) session. No Anthropic API key. No OpenAI key. Just your existing Claude login.

---

## What it does

STARLUKE deploys a team of specialized AI agents that mirror a real trading firm:

```
Analyst Team  →  Research Team  →  Trader  →  Risk Management  →  Portfolio Manager
```

Each agent has a defined role and debates with the others before the Portfolio Manager issues a final BUY / HOLD / SELL verdict.

### Agents

| Team | Agent | Role |
|------|-------|------|
| Analyst | Market Analyst | RSI, MACD, Bollinger Bands, price action |
| Analyst | News Analyst | Macro events, earnings, regulatory news |
| Analyst | Fundamentals Analyst | P/E, revenue, margins, balance sheet |
| Analyst | Valuation Analyst | Peer comparison, EV/EBITDA, stock personality |
| Research | Bull Researcher | Makes the bullish case |
| Research | Bear Researcher | Makes the bearish case |
| Research | Research Manager | Weighs bull vs bear, issues investment plan |
| Trading | Trader | Converts research into a specific trade proposal |
| Risk | Aggressive Analyst | Argues for high-reward approach |
| Risk | Neutral Analyst | Balances risk and reward |
| Risk | Conservative Analyst | Argues for capital preservation |
| Portfolio | Portfolio Manager | Final BUY / HOLD / SELL decision |

---

## Key features

- **No API key required** — all LLM calls route through the local `claude` CLI subprocess
- **Free market data** — yfinance (OHLCV, fundamentals, news)
- **Valuation Analyst** — fetches 3-4 peer companies and produces a comparison table with P/E, P/S, EV/EBITDA, ROE, Debt/Equity
- **Multi-language output** — reports can be generated in English, Chinese, Japanese, Korean, and more
- **CLI interface** — rich live dashboard with agent progress, tool calls, and streaming reports
- **Streamlit web UI** — browser-based interface for the same analysis (`app.py`)
- **Auto-save** — results saved to `reports/<TICKER>/<DATE>/` as markdown files

---

## Requirements

- [Claude Code CLI](https://claude.ai/code) installed and logged in (`claude --version` should work)
- Python 3.11+
- Windows / macOS / Linux

---

## Installation

```bash
git clone https://github.com/zz3306/Trading-agent-starluke.git
cd Trading-agent-starluke
pip install -e .
```

---

## Usage

### CLI (recommended)

```bash
tradingagents analyze
```

Follow the prompts to select ticker, date, analysts, research depth, and model.

### Streamlit web UI

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### Python API

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "claude_cli"
config["selected_analysts"] = ["market", "news", "fundamentals", "valuation"]

ta = TradingAgentsGraph(debug=False, config=config)
final_state, signal = ta.propagate("AAPL", "2025-01-15")
print(signal)  # BUY / HOLD / SELL
```

---

## How the Claude CLI bridge works

Instead of calling the Anthropic REST API, STARLUKE shells out to the `claude` CLI:

```python
subprocess.Popen(
    ["claude", "--output-format", "text", "--dangerously-skip-permissions", "-p", prompt],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
)
```

Tool calls are simulated via prompt engineering — Claude outputs a `TOOL_CALL: {"name": ..., "args": ...}` sentinel line, which the framework intercepts and executes as a real Python function call.

---

## Model selection

In the CLI (Step 7) or web UI sidebar you can select which Claude model to use:

| Slot | Recommended | Used by |
|------|-------------|---------|
| Quick | claude-sonnet-4-6 | All analysts, Trader, Risk team |
| Deep | claude-opus-4-5 | Research Manager, Portfolio Manager |

Any model available in your Claude Code subscription can be used.

---

## Output

Results are saved to `reports/<TICKER>/<DATE>/`:

```
reports/AAPL/2025-01-15/
├── complete_report.md
├── 1_analysts/
│   ├── market.md
│   ├── news.md
│   ├── fundamentals.md
│   ├── valuation.md
│   └── sentiment.md
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

## Credits

Built on top of [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache 2.0).

See [CHANGES.md](CHANGES.md) for a full list of modifications made in this fork.

---

## Disclaimer

For research and educational purposes only. Not financial advice.
