# STARLUKE — 开发笔记

## 项目结构

```
TradingAgents/
├── app.py                          # Streamlit web UI
├── cli/
│   ├── main.py                     # CLI 入口，Live dashboard，保存报告
│   ├── utils.py                    # 交互式提示（questionary）
│   ├── models.py                   # AnalystType enum
│   └── static/welcome.txt          # STARLUKE ASCII art
├── tradingagents/
│   ├── default_config.py           # 所有配置默认值
│   ├── agents/
│   │   ├── analysts/
│   │   │   ├── market_analyst.py
│   │   │   ├── news_analyst.py
│   │   │   ├── fundamentals_analyst.py
│   │   │   ├── valuation_analyst.py   ← 我们加的
│   │   │   ├── macro_analyst.py       ← 我们加的
│   │   │   └── social_media_analyst.py
│   │   ├── researchers/
│   │   │   ├── bull_researcher.py
│   │   │   └── bear_researcher.py
│   │   ├── managers/
│   │   │   ├── research_manager.py
│   │   │   └── portfolio_manager.py
│   │   ├── trader/trader.py
│   │   ├── risk_mgmt/
│   │   │   ├── aggressive_debator.py
│   │   │   ├── conservative_debator.py
│   │   │   └── neutral_debator.py
│   │   ├── schemas.py              # Pydantic 结构化输出定义
│   │   └── utils/
│   │       ├── agent_states.py     # LangGraph AgentState TypedDict
│   │       └── agent_utils.py      # get_language_instruction() 等工具函数
│   ├── dataflows/
│   │   ├── y_finance.py            # yfinance 数据拉取
│   │   ├── cache.py                ← 我们加的（文件缓存层）
│   │   └── macro_data_tools.py     ← 我们加的（宏观数据工具）
│   ├── graph/
│   │   ├── trading_graph.py        # TradingAgentsGraph 主入口
│   │   ├── setup.py                # 建图、节点注册
│   │   ├── conditional_logic.py    # LangGraph 路由条件
│   │   └── propagation.py          # stream/propagate 逻辑
│   └── llm_clients/
│       ├── claude_cli_client.py    ← 我们加的（Claude CLI bridge）
│       ├── factory.py              # 按 provider 创建 LLM 实例
│       └── model_catalog.py        # 所有 provider 的可选模型列表
├── reports/                        # 分析结果保存目录
│   ├── signal_log.csv              ← 我们加的（信号追踪）
│   └── <TICKER>/<DATE>/
│       ├── complete_report.md
│       ├── 1_analysts/
│       ├── 2_research/
│       ├── 3_trading/
│       ├── 4_risk/
│       └── 5_portfolio/
├── data_cache/                     ← 我们加的（yfinance 缓存）
│   └── <TICKER>/
│       └── <DATE>_<type>.json
├── CHANGES.md                      # Apache-2.0 改动说明
└── DEVELOPMENT.md                  # 本文件
```

---

## Agent 流程

```
[选填 Analysts]
  Market → News → Fundamentals → Valuation → Macro → Social
       ↓
  Bull Researcher  ←→  Bear Researcher
       ↓
  Research Manager (structured output → investment_plan)
       ↓
  Trader (structured output → trader_investment_plan)
       ↓
  Aggressive ←→ Neutral ←→ Conservative
       ↓
  Portfolio Manager (structured output → final_trade_decision)
```

每个 Agent 通过 `AgentState` 共享数据，state 是一个 TypedDict，定义在 `agent_states.py`。

---

## 添加新 Agent（快速参考）

1. 新建 `tradingagents/agents/analysts/xxx_analyst.py`，返回 `{"messages": [...], "xxx_report": report}`
2. 在 `agent_states.py` 加字段 `xxx_report: Annotated[str, "..."]`
3. 在 `agents/__init__.py` export
4. 在 `graph/conditional_logic.py` 加路由方法 `should_continue_xxx`
5. 在 `graph/setup.py` 注册节点和工具节点
6. 在 `graph/trading_graph.py` 加 tool node（如有工具调用）
7. 在 `cli/models.py` 加 `XXX = "xxx"` 到 AnalystType
8. 在 `cli/utils.py` 加到 `ANALYST_ORDER`
9. 在 `app.py` 加 checkbox 和结果 tab

---

## Claude CLI Bridge 原理

所有 LLM 调用走本地 `claude` CLI 子进程，不需要 API key：

```python
subprocess.Popen(
    ["claude", "--output-format", "text", "--dangerously-skip-permissions", "-p", prompt],
    stdout=PIPE, stderr=PIPE, stdin=DEVNULL,
)
```

工具调用靠 prompt engineering 模拟：Claude 输出 `TOOL_CALL: {"name": "...", "args": {...}}`，框架拦截后执行真正的 Python 函数。

配置项（`default_config.py`）：
- `claude_cli_timeout`: 600 秒
- `claude_cli_skip_permissions`: True

---

## 缓存策略

- 历史日期数据（非今天）：永久缓存，存 `data_cache/<TICKER>/<DATE>_<type>.json`
- 宏观数据：缓存 7 天（Fed/CPI/利率不需要每次都拉）
- 今天的数据：不缓存（盘中数据在变）

---

## 信号追踪

每次分析完自动追加到 `reports/signal_log.csv`：

| analyzed_at | ticker | analysis_date | signal | price |
|-------------|--------|---------------|--------|-------|
| 2026-05-11 | AAPL | 2025-01-15 | BUY | 182.3 |

---

## 常用命令

```bash
# CLI 分析
tradingagents analyze

# Streamlit web UI
streamlit run app.py

# 推到自己的 GitHub
git add -A && git commit -m "..." && git push starluke main --force
```

---

## 待做 / 想法

- [ ] 历史回测：给定时间段跑多个日期，统计信号准确率
- [ ] Portfolio 分配：多只票 BUY 信号 → 给出仓位建议
- [ ] 定时任务：每天收盘后自动跑一批股票
