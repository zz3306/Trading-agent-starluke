# CHANGES

This project is a fork of [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents), licensed under the Apache License 2.0.

Original copyright: © Tauric Research

---

## Modifications made in this fork (STARLUKE)

### LLM Backend — Claude CLI Bridge

- **New file: `tradingagents/llm_clients/claude_cli_client.py`**
  Routes all LLM calls through the local `claude` CLI subprocess instead of the Anthropic REST API. No API key required; uses the user's existing Claude Code login session. Implements `ClaudeCLIChatModel` (LangChain `BaseChatModel` subclass), tool-call simulation via prompt engineering, structured-output parsing, and a `ClaudeCLIClient` adapter that plugs into the existing provider factory.

- **New file: `tradingagents/llm_clients/base_client.py`**
  Abstract base class `BaseLLMClient` shared by all provider adapters.

- **Modified: `tradingagents/llm_clients/model_catalog.py`**
  Added `claude_cli` provider entry listing available Claude model IDs (Sonnet 4.6, Haiku 4.5, Opus 4.5) for both quick-thinking and deep-thinking slots.

- **Modified: `tradingagents/default_config.py`**
  Added `claude_cli_skip_permissions` (default `True`) and `claude_cli_timeout` (default `600` s) configuration keys. Added `llm_provider: "claude_cli"` as default provider. Added `results_dir_local` for auto-saving reports to the project directory.

- **Modified: `tradingagents/graph/trading_graph.py`**
  Wired `claude_cli` provider into `_get_provider_kwargs()`. Added `valuation` tool node (`get_fundamentals`, `get_income_statement`). Extended `_log_state()` to include `valuation_report`.

### Valuation Analyst (new agent)

- **New file: `tradingagents/agents/analysts/valuation_analyst.py`**
  Peer-comparison valuation agent. Identifies 3–4 comparable peers, fetches their fundamentals and income statements, produces: Stock Personality Classification, Peer Comparison Table (P/E, P/S, EV/EBITDA, ROE, Debt/Equity), Valuation Assessment, and Key Risks. Conditionally skips target-company data fetch when `fundamentals_report` is already present in state.

- **Modified: `tradingagents/agents/utils/agent_states.py`**
  Added `valuation_report` field to `AgentState`.

- **Modified: `tradingagents/agents/__init__.py`**
  Exported `create_valuation_analyst`.

- **Modified: `tradingagents/graph/conditional_logic.py`**
  Added `should_continue_valuation()` routing method.

- **Modified: `tradingagents/graph/setup.py`**
  Wired valuation analyst into graph. Enforced ordering: valuation always runs after fundamentals when both are selected.

- **Modified: `cli/models.py`**
  Added `VALUATION = "valuation"` to `AnalystType` enum.

- **Modified: `cli/utils.py`**
  Added Valuation Analyst to `ANALYST_ORDER`. Refactored `select_claude_cli_models()` to read options from `model_catalog` instead of hardcoded list. Added `select_claude_cli_models()`, `ask_output_language()`, `ask_openai_reasoning_effort()`, `ask_anthropic_effort()`, `ask_gemini_thinking_config()`, `select_openrouter_model()`.

### Bug fixes & robustness improvements

- **Modified: `tradingagents/agents/risk_mgmt/aggressive_debator.py`**
  Changed `state["key"]` to `state.get("key") or "Not available."` for all report fields. Added `try/except` around `llm.invoke()` with a fallback message to prevent pipeline crashes when the LLM call fails.

- **Modified: `tradingagents/agents/risk_mgmt/conservative_debator.py`**
  Same fixes as `aggressive_debator.py`.

- **Modified: `tradingagents/agents/risk_mgmt/neutral_debator.py`**
  Complete rewrite: added safe `.get()` access, `try/except`, logging, and language instruction support.

- **Modified: `tradingagents/agents/managers/research_manager.py`**
  Added `get_language_instruction()` call so the output language setting is honoured.

- **Modified: `tradingagents/agents/trader/trader.py`**
  Added `get_language_instruction()` call so the output language setting is honoured.

- **Modified: `tradingagents/agents/schemas.py`**
  Removed hard-coded "Two to four sentences" length limits from `TraderProposal.reasoning` and `PortfolioDecision.executive_summary` field descriptions. Replaced with instructions asking for comprehensive, data-driven detail.

- **Fixed dead code in `claude_cli_client.py`**: Removed temp-file code that was written but whose file handle was never passed to `Popen` (the `-p prompt` path was used directly regardless).

### Claude CLI tool-approval fix

- Added `--dangerously-skip-permissions` flag (configurable via `claude_cli_skip_permissions`) to prevent the CLI from blocking on tool-approval prompts when running as a non-interactive subprocess.
- Added `CRITICAL` instruction to the tool-call prompt block explicitly forbidding the sub-Claude from using built-in tools (Bash, Read, WebSearch, etc.), directing all data retrieval through the `TOOL_CALL:` sentinel instead.

### UI — CLI

- **Modified: `cli/main.py`**
  Renamed banner from "TradingAgents" to "STARLUKE". Applied rainbow coloring (red→yellow→green→cyan→blue→magenta cycling per character) to the ASCII art welcome screen using Rich `Text`. Added `select_claude_cli_models()` model-selection flow for `claude_cli` provider. Added output-language prompt (Step 3). Updated all Panel titles and header text to reflect STARLUKE branding.

- **Modified: `cli/static/welcome.txt`**
  Replaced TradingAgents ASCII art with STARLUKE ASCII art.

### UI — Streamlit web app

- **Modified: `app.py`**
  Model selection reads from `model_catalog.get_model_options()` instead of hardcoded lists. Added Valuation & Peers analyst checkbox (default on). Added `"📉 Valuation & Peers"` results tab. Added help text to Social checkbox explaining it uses the same data source as News. All selected-analyst ordering matches the graph's expected dependency order (fundamentals before valuation).

---

*All original source files not listed above are unmodified from the upstream repository.*
