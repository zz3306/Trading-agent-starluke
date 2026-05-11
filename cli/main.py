from typing import Optional
import datetime
import typer
import questionary
from pathlib import Path
from functools import wraps
from rich.console import Console
from dotenv import find_dotenv, load_dotenv

# Search starts from the user's CWD so the installed `tradingagents`
# console script picks up the project's .env instead of walking up from
# site-packages.
load_dotenv(find_dotenv(usecwd=True))
load_dotenv(find_dotenv(".env.enterprise", usecwd=True), override=False)
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live
from rich.columns import Columns
from rich.markdown import Markdown
from rich.layout import Layout
from rich.text import Text
from rich.table import Table
from collections import deque
import time
from rich.tree import Tree
from rich import box
from rich.align import Align
from rich.rule import Rule
from rich.console import Group as RichGroup

import sys, io, os

# Force UTF-8 on Windows so emoji / CJK in help text don't crash cp1252.
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from cli.models import AnalystType
from cli.utils import *  # includes select_claude_cli_models
from cli.announcements import fetch_announcements, display_announcements
from cli.stats_handler import StatsCallbackHandler

# Use force_terminal=True so rich renders properly; no_color fallback for
# environments that still can't handle Unicode.
try:
    console = Console(force_terminal=True)
    # Quick probe: try encoding a known emoji
    "★".encode(console.file.encoding if hasattr(console.file, "encoding") else "utf-8")
except (UnicodeEncodeError, Exception):
    console = Console(no_color=True, highlight=False)

app = typer.Typer(
    name="STARLUKE",
    help="STARLUKE: Multi-Agents LLM Financial Trading Framework",
    add_completion=True,  # Enable shell completion
)

_RAINBOW_COLORS = ["red", "yellow", "green", "cyan", "blue", "magenta"]


def make_rainbow_text(text: str) -> Text:
    """Color each non-space character with a cycling rainbow palette."""
    rich_text = Text()
    color_idx = 0
    for char in text:
        if char == "\n":
            rich_text.append("\n")
        elif char == " ":
            rich_text.append(" ")
        else:
            rich_text.append(char, style=_RAINBOW_COLORS[color_idx % len(_RAINBOW_COLORS)])
            color_idx += 1
    return rich_text


# Create a deque to store recent messages with a maximum length
class MessageBuffer:
    # Fixed teams that always run (not user-selectable)
    FIXED_AGENTS = {
        "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
        "Trading Team": ["Trader"],
        "Risk Management": ["Aggressive Analyst", "Neutral Analyst", "Conservative Analyst"],
        "Portfolio Management": ["Portfolio Manager"],
    }

    # Analyst name mapping
    ANALYST_MAPPING = {
        "market": "Market Analyst",
        "social": "Social Analyst",
        "news": "News Analyst",
        "fundamentals": "Fundamentals Analyst",
    }

    # Report section mapping: section -> (analyst_key for filtering, finalizing_agent)
    # analyst_key: which analyst selection controls this section (None = always included)
    # finalizing_agent: which agent must be "completed" for this report to count as done
    REPORT_SECTIONS = {
        "market_report": ("market", "Market Analyst"),
        "sentiment_report": ("social", "Social Analyst"),
        "news_report": ("news", "News Analyst"),
        "fundamentals_report": ("fundamentals", "Fundamentals Analyst"),
        "investment_plan": (None, "Research Manager"),
        "trader_investment_plan": (None, "Trader"),
        "final_trade_decision": (None, "Portfolio Manager"),
    }

    def __init__(self, max_length=100):
        self.messages = deque(maxlen=max_length)
        self.tool_calls = deque(maxlen=max_length)
        self.current_report = None
        self.final_report = None  # Store the complete final report
        self.agent_status = {}
        self.current_agent = None
        self.report_sections = {}
        self.selected_analysts = []
        self._processed_message_ids = set()

    def init_for_analysis(self, selected_analysts):
        """Initialize agent status and report sections based on selected analysts.

        Args:
            selected_analysts: List of analyst type strings (e.g., ["market", "news"])
        """
        self.selected_analysts = [a.lower() for a in selected_analysts]

        # Build agent_status dynamically
        self.agent_status = {}

        # Add selected analysts
        for analyst_key in self.selected_analysts:
            if analyst_key in self.ANALYST_MAPPING:
                self.agent_status[self.ANALYST_MAPPING[analyst_key]] = "pending"

        # Add fixed teams
        for team_agents in self.FIXED_AGENTS.values():
            for agent in team_agents:
                self.agent_status[agent] = "pending"

        # Build report_sections dynamically
        self.report_sections = {}
        for section, (analyst_key, _) in self.REPORT_SECTIONS.items():
            if analyst_key is None or analyst_key in self.selected_analysts:
                self.report_sections[section] = None

        # Reset other state
        self.current_report = None
        self.final_report = None
        self.current_agent = None
        self.messages.clear()
        self.tool_calls.clear()
        self._processed_message_ids.clear()

    def get_completed_reports_count(self):
        """Count reports that are finalized (their finalizing agent is completed).

        A report is considered complete when:
        1. The report section has content (not None), AND
        2. The agent responsible for finalizing that report has status "completed"

        This prevents interim updates (like debate rounds) from counting as completed.
        """
        count = 0
        for section in self.report_sections:
            if section not in self.REPORT_SECTIONS:
                continue
            _, finalizing_agent = self.REPORT_SECTIONS[section]
            # Report is complete if it has content AND its finalizing agent is done
            has_content = self.report_sections.get(section) is not None
            agent_done = self.agent_status.get(finalizing_agent) == "completed"
            if has_content and agent_done:
                count += 1
        return count

    def add_message(self, message_type, content):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.messages.append((timestamp, message_type, content))

    def add_tool_call(self, tool_name, args):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.tool_calls.append((timestamp, tool_name, args))

    def update_agent_status(self, agent, status):
        if agent in self.agent_status:
            self.agent_status[agent] = status
            self.current_agent = agent

    def update_report_section(self, section_name, content):
        if section_name in self.report_sections:
            self.report_sections[section_name] = content
            self._update_current_report()

    def _update_current_report(self):
        # For the panel display, only show the most recently updated section
        latest_section = None
        latest_content = None

        # Find the most recently updated section
        for section, content in self.report_sections.items():
            if content is not None:
                latest_section = section
                latest_content = content
               
        if latest_section and latest_content:
            # Format the current section for display
            section_titles = {
                "market_report": "Market Analysis",
                "sentiment_report": "Social Sentiment",
                "news_report": "News Analysis",
                "fundamentals_report": "Fundamentals Analysis",
                "investment_plan": "Research Team Decision",
                "trader_investment_plan": "Trading Team Plan",
                "final_trade_decision": "Portfolio Management Decision",
            }
            self.current_report = (
                f"### {section_titles[latest_section]}\n{latest_content}"
            )

        # Update the final complete report
        self._update_final_report()

    def _update_final_report(self):
        report_parts = []

        # Analyst Team Reports - use .get() to handle missing sections
        analyst_sections = ["market_report", "sentiment_report", "news_report", "fundamentals_report"]
        if any(self.report_sections.get(section) for section in analyst_sections):
            report_parts.append("## Analyst Team Reports")
            if self.report_sections.get("market_report"):
                report_parts.append(
                    f"### Market Analysis\n{self.report_sections['market_report']}"
                )
            if self.report_sections.get("sentiment_report"):
                report_parts.append(
                    f"### Social Sentiment\n{self.report_sections['sentiment_report']}"
                )
            if self.report_sections.get("news_report"):
                report_parts.append(
                    f"### News Analysis\n{self.report_sections['news_report']}"
                )
            if self.report_sections.get("fundamentals_report"):
                report_parts.append(
                    f"### Fundamentals Analysis\n{self.report_sections['fundamentals_report']}"
                )

        # Research Team Reports
        if self.report_sections.get("investment_plan"):
            report_parts.append("## Research Team Decision")
            report_parts.append(f"{self.report_sections['investment_plan']}")

        # Trading Team Reports
        if self.report_sections.get("trader_investment_plan"):
            report_parts.append("## Trading Team Plan")
            report_parts.append(f"{self.report_sections['trader_investment_plan']}")

        # Portfolio Management Decision
        if self.report_sections.get("final_trade_decision"):
            report_parts.append("## Portfolio Management Decision")
            report_parts.append(f"{self.report_sections['final_trade_decision']}")

        self.final_report = "\n\n".join(report_parts) if report_parts else None


message_buffer = MessageBuffer()


def create_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    layout["main"].split_column(
        Layout(name="upper", ratio=3), Layout(name="analysis", ratio=5)
    )
    layout["upper"].split_row(
        Layout(name="progress", ratio=2), Layout(name="messages", ratio=3)
    )
    return layout


def format_tokens(n):
    """Format token count for display."""
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def update_display(layout, spinner_text=None, stats_handler=None, start_time=None):
    # Header with welcome message
    layout["header"].update(
        Panel(
            "[bold green]STARLUKE — Multi-Agents LLM Financial Trading Framework[/bold green]\n"
            "[dim]Fork of [TauricResearch/TradingAgents](https://github.com/TauricResearch)[/dim]",
            title="STARLUKE",
            border_style="green",
            padding=(1, 2),
            expand=True,
        )
    )

    # Progress panel showing agent status
    progress_table = Table(
        show_header=True,
        header_style="bold magenta",
        show_footer=False,
        box=box.SIMPLE_HEAD,  # Use simple header with horizontal lines
        title=None,  # Remove the redundant Progress title
        padding=(0, 2),  # Add horizontal padding
        expand=True,  # Make table expand to fill available space
    )
    progress_table.add_column("Team", style="cyan", justify="center", width=20)
    progress_table.add_column("Agent", style="green", justify="center", width=20)
    progress_table.add_column("Status", style="yellow", justify="center", width=20)

    # Group agents by team - filter to only include agents in agent_status
    all_teams = {
        "Analyst Team": [
            "Market Analyst",
            "Social Analyst",
            "News Analyst",
            "Fundamentals Analyst",
        ],
        "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
        "Trading Team": ["Trader"],
        "Risk Management": ["Aggressive Analyst", "Neutral Analyst", "Conservative Analyst"],
        "Portfolio Management": ["Portfolio Manager"],
    }

    # Filter teams to only include agents that are in agent_status
    teams = {}
    for team, agents in all_teams.items():
        active_agents = [a for a in agents if a in message_buffer.agent_status]
        if active_agents:
            teams[team] = active_agents

    for team, agents in teams.items():
        # Add first agent with team name
        first_agent = agents[0]
        status = message_buffer.agent_status.get(first_agent, "pending")
        if status == "in_progress":
            spinner = Spinner(
                "dots", text="[blue]in_progress[/blue]", style="bold cyan"
            )
            status_cell = spinner
        else:
            status_color = {
                "pending": "yellow",
                "completed": "green",
                "error": "red",
            }.get(status, "white")
            status_cell = f"[{status_color}]{status}[/{status_color}]"
        progress_table.add_row(team, first_agent, status_cell)

        # Add remaining agents in team
        for agent in agents[1:]:
            status = message_buffer.agent_status.get(agent, "pending")
            if status == "in_progress":
                spinner = Spinner(
                    "dots", text="[blue]in_progress[/blue]", style="bold cyan"
                )
                status_cell = spinner
            else:
                status_color = {
                    "pending": "yellow",
                    "completed": "green",
                    "error": "red",
                }.get(status, "white")
                status_cell = f"[{status_color}]{status}[/{status_color}]"
            progress_table.add_row("", agent, status_cell)

        # Add horizontal line after each team
        progress_table.add_row("─" * 20, "─" * 20, "─" * 20, style="dim")

    layout["progress"].update(
        Panel(progress_table, title="Progress", border_style="cyan", padding=(1, 2))
    )

    # Messages panel showing recent messages and tool calls
    messages_table = Table(
        show_header=True,
        header_style="bold magenta",
        show_footer=False,
        expand=True,  # Make table expand to fill available space
        box=box.MINIMAL,  # Use minimal box style for a lighter look
        show_lines=True,  # Keep horizontal lines
        padding=(0, 1),  # Add some padding between columns
    )
    messages_table.add_column("Time", style="cyan", width=8, justify="center")
    messages_table.add_column("Type", style="green", width=10, justify="center")
    messages_table.add_column(
        "Content", style="white", no_wrap=False, ratio=1
    )  # Make content column expand

    # Combine tool calls and messages
    all_messages = []

    # Add tool calls
    for timestamp, tool_name, args in message_buffer.tool_calls:
        formatted_args = format_tool_args(args)
        all_messages.append((timestamp, "Tool", f"{tool_name}: {formatted_args}"))

    # Add regular messages
    for timestamp, msg_type, content in message_buffer.messages:
        content_str = str(content) if content else ""
        if len(content_str) > 200:
            content_str = content_str[:197] + "..."
        all_messages.append((timestamp, msg_type, content_str))

    # Sort by timestamp descending (newest first)
    all_messages.sort(key=lambda x: x[0], reverse=True)

    # Calculate how many messages we can show based on available space
    max_messages = 12

    # Get the first N messages (newest ones)
    recent_messages = all_messages[:max_messages]

    # Add messages to table (already in newest-first order)
    for timestamp, msg_type, content in recent_messages:
        # Format content with word wrapping
        wrapped_content = Text(content, overflow="fold")
        messages_table.add_row(timestamp, msg_type, wrapped_content)

    layout["messages"].update(
        Panel(
            messages_table,
            title="Messages & Tools",
            border_style="blue",
            padding=(1, 2),
        )
    )

    # Analysis panel showing current report
    if message_buffer.current_report:
        layout["analysis"].update(
            Panel(
                Markdown(message_buffer.current_report),
                title="Current Report",
                border_style="green",
                padding=(1, 2),
            )
        )
    else:
        layout["analysis"].update(
            Panel(
                "[italic]Waiting for analysis report...[/italic]",
                title="Current Report",
                border_style="green",
                padding=(1, 2),
            )
        )

    # Footer with statistics
    # Agent progress - derived from agent_status dict
    agents_completed = sum(
        1 for status in message_buffer.agent_status.values() if status == "completed"
    )
    agents_total = len(message_buffer.agent_status)

    # Report progress - based on agent completion (not just content existence)
    reports_completed = message_buffer.get_completed_reports_count()
    reports_total = len(message_buffer.report_sections)

    # Build stats parts
    stats_parts = [f"Agents: {agents_completed}/{agents_total}"]

    # LLM and tool stats from callback handler
    if stats_handler:
        stats = stats_handler.get_stats()
        stats_parts.append(f"LLM: {stats['llm_calls']}")
        stats_parts.append(f"Tools: {stats['tool_calls']}")

        # Token display with graceful fallback
        if stats["tokens_in"] > 0 or stats["tokens_out"] > 0:
            tokens_str = f"Tokens: {format_tokens(stats['tokens_in'])}\u2191 {format_tokens(stats['tokens_out'])}\u2193"
        else:
            tokens_str = "Tokens: --"
        stats_parts.append(tokens_str)

    stats_parts.append(f"Reports: {reports_completed}/{reports_total}")

    # Elapsed time
    if start_time:
        elapsed = time.time() - start_time
        elapsed_str = f"\u23f1 {int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
        stats_parts.append(elapsed_str)

    stats_table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    stats_table.add_column("Stats", justify="center")
    stats_table.add_row(" | ".join(stats_parts))

    layout["footer"].update(Panel(stats_table, border_style="grey50"))


def get_user_selections():
    """Get all user selections before starting the analysis display."""
    # Display ASCII art welcome message
    with open(Path(__file__).parent / "static" / "welcome.txt", "r", encoding="utf-8") as f:
        welcome_ascii = f.read()

    # Create welcome box content with rainbow ASCII art
    body = Text.from_markup(
        "\n[bold green]STARLUKE: Multi-Agents LLM Financial Trading Framework - CLI[/bold green]\n\n"
        "[bold]Workflow Steps:[/bold]\n"
        "I. Analyst Team → II. Research Team → III. Trader → IV. Risk Management → V. Portfolio Management\n\n"
        "[dim]Fork of [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents)[/dim]"
    )

    # Create and center the welcome box
    welcome_box = Panel(
        RichGroup(make_rainbow_text(welcome_ascii), body),
        border_style="green",
        padding=(1, 2),
        title="Welcome to STARLUKE",
        subtitle="Multi-Agents LLM Financial Trading Framework",
    )
    console.print(Align.center(welcome_box))
    console.print()
    console.print()  # Add vertical space before announcements

    # Fetch and display announcements (silent on failure)
    announcements = fetch_announcements()
    display_announcements(console, announcements)

    # Create a boxed questionnaire for each step
    def create_question_box(title, prompt, default=None):
        box_content = f"[bold]{title}[/bold]\n"
        box_content += f"[dim]{prompt}[/dim]"
        if default:
            box_content += f"\n[dim]Default: {default}[/dim]"
        return Panel(box_content, border_style="blue", padding=(1, 2))

    # Step 1: Ticker symbol
    console.print(
        create_question_box(
            "Step 1: Ticker Symbol",
            "Enter the exact ticker symbol to analyze, including exchange suffix when needed (examples: SPY, CNC.TO, 7203.T, 0700.HK)",
            "SPY",
        )
    )
    selected_ticker = get_ticker()

    # Step 2: Analysis date
    default_date = datetime.datetime.now().strftime("%Y-%m-%d")
    console.print(
        create_question_box(
            "Step 2: Analysis Date",
            "Enter the analysis date (YYYY-MM-DD)",
            default_date,
        )
    )
    analysis_date = get_analysis_date()

    # Step 3: Output language
    console.print(
        create_question_box(
            "Step 3: Output Language",
            "Select the language for analyst reports and final decision"
        )
    )
    output_language = ask_output_language()

    # Step 4: Select analysts
    console.print(
        create_question_box(
            "Step 4: Analysts Team", "Select your LLM analyst agents for the analysis"
        )
    )
    selected_analysts = select_analysts()
    console.print(
        f"[green]Selected analysts:[/green] {', '.join(analyst.value for analyst in selected_analysts)}"
    )

    # Step 5: Research depth
    console.print(
        create_question_box(
            "Step 5: Research Depth", "Select your research depth level"
        )
    )
    selected_research_depth = select_research_depth()

    # Step 6: LLM Provider
    console.print(
        create_question_box(
            "Step 6: LLM Provider", "Select your LLM provider"
        )
    )
    selected_llm_provider, backend_url = select_llm_provider()

    # Step 7 & 8: Skip for claude_cli — no model selection or thinking config needed
    thinking_level = None
    reasoning_effort = None
    anthropic_effort = None
    provider_lower = selected_llm_provider.lower()

    if provider_lower == "claude_cli":
        console.print(
            create_question_box(
                "Step 7: Claude Model Selection",
                "Choose which Claude models to use (no API key needed — uses your local Claude CLI session)"
            )
        )
        selected_shallow_thinker, selected_deep_thinker = select_claude_cli_models()
        console.print(
            f"[green]✓ Quick model:[/green] {selected_shallow_thinker}  "
            f"[green]✓ Deep model:[/green] {selected_deep_thinker}"
        )
    else:
        console.print(
            create_question_box(
                "Step 7: Thinking Agents", "Select your thinking agents for analysis"
            )
        )
        selected_shallow_thinker = select_shallow_thinking_agent(selected_llm_provider)
        selected_deep_thinker = select_deep_thinking_agent(selected_llm_provider)

        if provider_lower == "google":
            console.print(
                create_question_box(
                    "Step 8: Thinking Mode",
                    "Configure Gemini thinking mode"
                )
            )
            thinking_level = ask_gemini_thinking_config()
        elif provider_lower == "openai":
            console.print(
                create_question_box(
                    "Step 8: Reasoning Effort",
                    "Configure OpenAI reasoning effort level"
                )
            )
            reasoning_effort = ask_openai_reasoning_effort()
        elif provider_lower == "anthropic":
            console.print(
                create_question_box(
                    "Step 8: Effort Level",
                    "Configure Claude effort level"
                )
            )
            anthropic_effort = ask_anthropic_effort()

    return {
        "ticker": selected_ticker,
        "analysis_date": analysis_date,
        "analysts": selected_analysts,
        "research_depth": selected_research_depth,
        "llm_provider": selected_llm_provider.lower(),
        "backend_url": backend_url,
        "shallow_thinker": selected_shallow_thinker,
        "deep_thinker": selected_deep_thinker,
        "google_thinking_level": thinking_level,
        "openai_reasoning_effort": reasoning_effort,
        "anthropic_effort": anthropic_effort,
        "output_language": output_language,
    }


def get_ticker():
    """Get ticker symbol from user input, preserving exchange suffixes."""
    # typer.prompt strips trailing dot-suffixes on some shells (e.g. 000404.SH
    # collapses to 000404). questionary.text reads the raw line.
    ticker = questionary.text(
        "",
        validate=lambda value: (
            not value.strip()
            or (
                all(ch.isalnum() or ch in "._-^" for ch in value.strip())
                and len(value.strip()) <= 32
            )
        )
        or "Please enter a valid ticker symbol, e.g. AAPL, 000404.SZ, 0700.HK.",
    ).ask()

    if ticker is None:
        console.print("\n[red]No ticker symbol provided. Exiting...[/red]")
        raise typer.Exit(1)

    return (ticker.strip() or "SPY").upper()


def get_analysis_date():
    """Get the analysis date from user input."""
    while True:
        date_str = typer.prompt(
            "", default=datetime.datetime.now().strftime("%Y-%m-%d")
        )
        try:
            # Validate date format and ensure it's not in the future
            analysis_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            if analysis_date.date() > datetime.datetime.now().date():
                console.print("[red]Error: Analysis date cannot be in the future[/red]")
                continue
            return date_str
        except ValueError:
            console.print(
                "[red]Error: Invalid date format. Please use YYYY-MM-DD[/red]"
            )


def _append_signal_log(config: dict, ticker: str, analysis_date: str, signal: str) -> None:
    """Append one row to the signal tracking CSV."""
    import csv
    import yfinance as yf

    log_path = Path(config.get("results_dir_local") or config["results_dir"]) / "signal_log.csv"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Try to get the closing price for the analysis date
    price = ""
    try:
        from datetime import datetime, timedelta
        dt = datetime.strptime(analysis_date, "%Y-%m-%d")
        end = (dt + timedelta(days=3)).strftime("%Y-%m-%d")
        hist = yf.Ticker(ticker).history(start=analysis_date, end=end)
        if not hist.empty:
            price = f"{hist['Close'].iloc[0]:.2f}"
    except Exception:
        pass

    write_header = not log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["analyzed_at", "ticker", "analysis_date", "signal", "price_at_date"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            ticker,
            analysis_date,
            signal,
            price,
        ])


def _snippet(text: str, n: int = 300) -> str:
    """Return first n chars of text, stripped of leading markdown noise."""
    if not text:
        return ""
    # skip leading whitespace / heading lines
    lines = [l for l in text.strip().splitlines() if l.strip()]
    joined = " ".join(lines)
    return joined[:n].rstrip() + ("…" if len(joined) > n else "")


def extract_and_save_summary(final_state: dict, ticker: str, save_path: Path) -> None:
    """Extract key data points and write summary.json (< 3 KB) alongside full reports.

    This is the only file read during historical comparison — never the full markdowns.
    """
    import json as _json
    from datetime import datetime as _dt

    debate = final_state.get("investment_debate_state") or {}
    risk   = final_state.get("risk_debate_state") or {}

    # Derive signal
    decision_text = risk.get("judge_decision", "")
    upper = decision_text.upper()
    if any(w in upper for w in ("STRONG BUY", "BUY")):
        signal = "BUY"
    elif any(w in upper for w in ("STRONG SELL", "SELL")):
        signal = "SELL"
    else:
        signal = "HOLD"

    summary = {
        "ticker":       ticker,
        "date":         str(final_state.get("trade_date", "")),
        "signal":       signal,
        "generated_at": _dt.now().strftime("%Y-%m-%d %H:%M"),
        "analysts": {
            "market":       _snippet(final_state.get("market_report", "")),
            "news":         _snippet(final_state.get("news_report", "")),
            "fundamentals": _snippet(final_state.get("fundamentals_report", "")),
            "valuation":    _snippet(final_state.get("valuation_report", "")),
            "macro":        _snippet(final_state.get("macro_report", "")),
            "sentiment":    _snippet(final_state.get("sentiment_report", "")),
            "options":      _snippet(final_state.get("options_report", "")),
        },
        "bull_thesis":       _snippet(debate.get("bull_history", ""), 400),
        "bear_thesis":       _snippet(debate.get("bear_history", ""), 400),
        "research_plan":     _snippet(debate.get("judge_decision", ""), 400),
        "trader_plan":       _snippet(final_state.get("trader_investment_plan", ""), 400),
        "risk_aggressive":   _snippet(risk.get("aggressive_history", ""), 200),
        "risk_conservative": _snippet(risk.get("conservative_history", ""), 200),
        "risk_neutral":      _snippet(risk.get("neutral_history", ""), 200),
        "final_decision":    _snippet(decision_text, 600),
    }

    save_path.mkdir(parents=True, exist_ok=True)
    with open(save_path / "summary.json", "w", encoding="utf-8") as f:
        _json.dump(summary, f, indent=2, ensure_ascii=False)


def save_report_to_disk(final_state, ticker: str, save_path: Path):
    """Save complete analysis report to disk with organized subfolders."""
    save_path.mkdir(parents=True, exist_ok=True)
    sections = []

    # 1. Analysts
    analysts_dir = save_path / "1_analysts"
    analyst_parts = []
    if final_state.get("market_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "market.md").write_text(final_state["market_report"], encoding="utf-8")
        analyst_parts.append(("Market Analyst", final_state["market_report"]))
    if final_state.get("sentiment_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "sentiment.md").write_text(final_state["sentiment_report"], encoding="utf-8")
        analyst_parts.append(("Social Analyst", final_state["sentiment_report"]))
    if final_state.get("news_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "news.md").write_text(final_state["news_report"], encoding="utf-8")
        analyst_parts.append(("News Analyst", final_state["news_report"]))
    if final_state.get("fundamentals_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "fundamentals.md").write_text(final_state["fundamentals_report"], encoding="utf-8")
        analyst_parts.append(("Fundamentals Analyst", final_state["fundamentals_report"]))
    if final_state.get("valuation_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "valuation.md").write_text(final_state["valuation_report"], encoding="utf-8")
        analyst_parts.append(("Valuation Analyst", final_state["valuation_report"]))
    if final_state.get("macro_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "macro.md").write_text(final_state["macro_report"], encoding="utf-8")
        analyst_parts.append(("Macro Analyst", final_state["macro_report"]))
    if final_state.get("options_report"):
        analysts_dir.mkdir(exist_ok=True)
        (analysts_dir / "options.md").write_text(final_state["options_report"], encoding="utf-8")
        analyst_parts.append(("Options Analyst", final_state["options_report"]))
    if analyst_parts:
        content = "\n\n".join(f"### {name}\n{text}" for name, text in analyst_parts)
        sections.append(f"## I. Analyst Team Reports\n\n{content}")

    # 2. Research
    if final_state.get("investment_debate_state"):
        research_dir = save_path / "2_research"
        debate = final_state["investment_debate_state"]
        research_parts = []
        if debate.get("bull_history"):
            research_dir.mkdir(exist_ok=True)
            (research_dir / "bull.md").write_text(debate["bull_history"], encoding="utf-8")
            research_parts.append(("Bull Researcher", debate["bull_history"]))
        if debate.get("bear_history"):
            research_dir.mkdir(exist_ok=True)
            (research_dir / "bear.md").write_text(debate["bear_history"], encoding="utf-8")
            research_parts.append(("Bear Researcher", debate["bear_history"]))
        if debate.get("judge_decision"):
            research_dir.mkdir(exist_ok=True)
            (research_dir / "manager.md").write_text(debate["judge_decision"], encoding="utf-8")
            research_parts.append(("Research Manager", debate["judge_decision"]))
        if research_parts:
            content = "\n\n".join(f"### {name}\n{text}" for name, text in research_parts)
            sections.append(f"## II. Research Team Decision\n\n{content}")

    # 3. Trading
    if final_state.get("trader_investment_plan"):
        trading_dir = save_path / "3_trading"
        trading_dir.mkdir(exist_ok=True)
        (trading_dir / "trader.md").write_text(final_state["trader_investment_plan"], encoding="utf-8")
        sections.append(f"## III. Trading Team Plan\n\n### Trader\n{final_state['trader_investment_plan']}")

    # 4. Risk Management
    if final_state.get("risk_debate_state"):
        risk_dir = save_path / "4_risk"
        risk = final_state["risk_debate_state"]
        risk_parts = []
        if risk.get("aggressive_history"):
            risk_dir.mkdir(exist_ok=True)
            (risk_dir / "aggressive.md").write_text(risk["aggressive_history"], encoding="utf-8")
            risk_parts.append(("Aggressive Analyst", risk["aggressive_history"]))
        if risk.get("conservative_history"):
            risk_dir.mkdir(exist_ok=True)
            (risk_dir / "conservative.md").write_text(risk["conservative_history"], encoding="utf-8")
            risk_parts.append(("Conservative Analyst", risk["conservative_history"]))
        if risk.get("neutral_history"):
            risk_dir.mkdir(exist_ok=True)
            (risk_dir / "neutral.md").write_text(risk["neutral_history"], encoding="utf-8")
            risk_parts.append(("Neutral Analyst", risk["neutral_history"]))
        if risk_parts:
            content = "\n\n".join(f"### {name}\n{text}" for name, text in risk_parts)
            sections.append(f"## IV. Risk Management Team Decision\n\n{content}")

        # 5. Portfolio Manager
        if risk.get("judge_decision"):
            portfolio_dir = save_path / "5_portfolio"
            portfolio_dir.mkdir(exist_ok=True)
            (portfolio_dir / "decision.md").write_text(risk["judge_decision"], encoding="utf-8")
            sections.append(f"## V. Portfolio Manager Decision\n\n### Portfolio Manager\n{risk['judge_decision']}")

    # Write consolidated report
    header = f"# Trading Analysis Report: {ticker}\n\nGenerated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    (save_path / "complete_report.md").write_text(header + "\n\n".join(sections), encoding="utf-8")

    # Write lightweight summary for historical comparison
    extract_and_save_summary(final_state, ticker, save_path)

    return save_path / "complete_report.md"


def display_complete_report(final_state):
    """Display the complete analysis report sequentially (avoids truncation)."""
    console.print()
    console.print(Rule("Complete Analysis Report", style="bold green"))

    # I. Analyst Team Reports
    analysts = []
    if final_state.get("market_report"):
        analysts.append(("Market Analyst", final_state["market_report"]))
    if final_state.get("sentiment_report"):
        analysts.append(("Social Analyst", final_state["sentiment_report"]))
    if final_state.get("news_report"):
        analysts.append(("News Analyst", final_state["news_report"]))
    if final_state.get("fundamentals_report"):
        analysts.append(("Fundamentals Analyst", final_state["fundamentals_report"]))
    if final_state.get("valuation_report"):
        analysts.append(("Valuation Analyst", final_state["valuation_report"]))
    if final_state.get("macro_report"):
        analysts.append(("Macro Analyst", final_state["macro_report"]))
    if analysts:
        console.print(Panel("[bold]I. Analyst Team Reports[/bold]", border_style="cyan"))
        for title, content in analysts:
            console.print(Panel(Markdown(content), title=title, border_style="blue", padding=(1, 2)))

    # II. Research Team Reports
    if final_state.get("investment_debate_state"):
        debate = final_state["investment_debate_state"]
        research = []
        if debate.get("bull_history"):
            research.append(("Bull Researcher", debate["bull_history"]))
        if debate.get("bear_history"):
            research.append(("Bear Researcher", debate["bear_history"]))
        if debate.get("judge_decision"):
            research.append(("Research Manager", debate["judge_decision"]))
        if research:
            console.print(Panel("[bold]II. Research Team Decision[/bold]", border_style="magenta"))
            for title, content in research:
                console.print(Panel(Markdown(content), title=title, border_style="blue", padding=(1, 2)))

    # III. Trading Team
    if final_state.get("trader_investment_plan"):
        console.print(Panel("[bold]III. Trading Team Plan[/bold]", border_style="yellow"))
        console.print(Panel(Markdown(final_state["trader_investment_plan"]), title="Trader", border_style="blue", padding=(1, 2)))

    # IV. Risk Management Team
    if final_state.get("risk_debate_state"):
        risk = final_state["risk_debate_state"]
        risk_reports = []
        if risk.get("aggressive_history"):
            risk_reports.append(("Aggressive Analyst", risk["aggressive_history"]))
        if risk.get("conservative_history"):
            risk_reports.append(("Conservative Analyst", risk["conservative_history"]))
        if risk.get("neutral_history"):
            risk_reports.append(("Neutral Analyst", risk["neutral_history"]))
        if risk_reports:
            console.print(Panel("[bold]IV. Risk Management Team Decision[/bold]", border_style="red"))
            for title, content in risk_reports:
                console.print(Panel(Markdown(content), title=title, border_style="blue", padding=(1, 2)))

        # V. Portfolio Manager Decision
        if risk.get("judge_decision"):
            console.print(Panel("[bold]V. Portfolio Manager Decision[/bold]", border_style="green"))
            console.print(Panel(Markdown(risk["judge_decision"]), title="Portfolio Manager", border_style="blue", padding=(1, 2)))


def update_research_team_status(status):
    """Update status for research team members (not Trader)."""
    research_team = ["Bull Researcher", "Bear Researcher", "Research Manager"]
    for agent in research_team:
        message_buffer.update_agent_status(agent, status)


# Ordered list of analysts for status transitions
ANALYST_ORDER = ["market", "social", "news", "fundamentals"]
ANALYST_AGENT_NAMES = {
    "market": "Market Analyst",
    "social": "Social Analyst",
    "news": "News Analyst",
    "fundamentals": "Fundamentals Analyst",
}
ANALYST_REPORT_MAP = {
    "market": "market_report",
    "social": "sentiment_report",
    "news": "news_report",
    "fundamentals": "fundamentals_report",
}


def update_analyst_statuses(message_buffer, chunk):
    """Update analyst statuses based on accumulated report state.

    Logic:
    - Store new report content from the current chunk if present
    - Check accumulated report_sections (not just current chunk) for status
    - Analysts with reports = completed
    - First analyst without report = in_progress
    - Remaining analysts without reports = pending
    - When all analysts done, set Bull Researcher to in_progress
    """
    selected = message_buffer.selected_analysts
    found_active = False

    for analyst_key in ANALYST_ORDER:
        if analyst_key not in selected:
            continue

        agent_name = ANALYST_AGENT_NAMES[analyst_key]
        report_key = ANALYST_REPORT_MAP[analyst_key]

        # Capture new report content from current chunk
        if chunk.get(report_key):
            message_buffer.update_report_section(report_key, chunk[report_key])

        # Determine status from accumulated sections, not just current chunk
        has_report = bool(message_buffer.report_sections.get(report_key))

        if has_report:
            message_buffer.update_agent_status(agent_name, "completed")
        elif not found_active:
            message_buffer.update_agent_status(agent_name, "in_progress")
            found_active = True
        else:
            message_buffer.update_agent_status(agent_name, "pending")

    # When all analysts complete, transition research team to in_progress
    if not found_active and selected:
        if message_buffer.agent_status.get("Bull Researcher") == "pending":
            message_buffer.update_agent_status("Bull Researcher", "in_progress")

def extract_content_string(content):
    """Extract string content from various message formats.
    Returns None if no meaningful text content is found.
    """
    import ast

    def is_empty(val):
        """Check if value is empty using Python's truthiness."""
        if val is None or val == '':
            return True
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return True
            try:
                return not bool(ast.literal_eval(s))
            except (ValueError, SyntaxError):
                return False  # Can't parse = real text
        return not bool(val)

    if is_empty(content):
        return None

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, dict):
        text = content.get('text', '')
        return text.strip() if not is_empty(text) else None

    if isinstance(content, list):
        text_parts = [
            item.get('text', '').strip() if isinstance(item, dict) and item.get('type') == 'text'
            else (item.strip() if isinstance(item, str) else '')
            for item in content
        ]
        result = ' '.join(t for t in text_parts if t and not is_empty(t))
        return result if result else None

    return str(content).strip() if not is_empty(content) else None


def classify_message_type(message) -> tuple[str, str | None]:
    """Classify LangChain message into display type and extract content.

    Returns:
        (type, content) - type is one of: User, Agent, Data, Control
                        - content is extracted string or None
    """
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    content = extract_content_string(getattr(message, 'content', None))

    if isinstance(message, HumanMessage):
        if content and content.strip() == "Continue":
            return ("Control", content)
        return ("User", content)

    if isinstance(message, ToolMessage):
        return ("Data", content)

    if isinstance(message, AIMessage):
        return ("Agent", content)

    # Fallback for unknown types
    return ("System", content)


def format_tool_args(args, max_length=80) -> str:
    """Format tool arguments for terminal display."""
    result = str(args)
    if len(result) > max_length:
        return result[:max_length - 3] + "..."
    return result

def run_analysis(checkpoint: bool = False):
    # First get all user selections
    selections = get_user_selections()

    # Create config with selected research depth
    config = DEFAULT_CONFIG.copy()
    config["max_debate_rounds"] = selections["research_depth"]
    config["max_risk_discuss_rounds"] = selections["research_depth"]
    config["quick_think_llm"] = selections["shallow_thinker"]
    config["deep_think_llm"] = selections["deep_thinker"]
    config["backend_url"] = selections["backend_url"]
    config["llm_provider"] = selections["llm_provider"].lower()
    # Provider-specific thinking configuration
    config["google_thinking_level"] = selections.get("google_thinking_level")
    config["openai_reasoning_effort"] = selections.get("openai_reasoning_effort")
    config["anthropic_effort"] = selections.get("anthropic_effort")
    config["output_language"] = selections.get("output_language", "English")
    config["checkpoint_enabled"] = checkpoint

    # Create stats callback handler for tracking LLM/tool calls
    stats_handler = StatsCallbackHandler()

    # Normalize analyst selection to predefined order (selection is a 'set', order is fixed)
    selected_set = {analyst.value for analyst in selections["analysts"]}
    selected_analyst_keys = [a for a in ANALYST_ORDER if a in selected_set]

    # Initialize the graph with callbacks bound to LLMs
    graph = TradingAgentsGraph(
        selected_analyst_keys,
        config=config,
        debug=True,
        callbacks=[stats_handler],
    )

    # Initialize message buffer with selected analysts
    message_buffer.init_for_analysis(selected_analyst_keys)

    # Track start time for elapsed display
    start_time = time.time()

    # Create result directory
    results_dir = Path(config["results_dir"]) / selections["ticker"] / selections["analysis_date"]
    results_dir.mkdir(parents=True, exist_ok=True)
    report_dir = results_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    log_file = results_dir / "message_tool.log"
    log_file.touch(exist_ok=True)

    def save_message_decorator(obj, func_name):
        func = getattr(obj, func_name)
        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            timestamp, message_type, content = obj.messages[-1]
            content = content.replace("\n", " ")  # Replace newlines with spaces
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} [{message_type}] {content}\n")
        return wrapper
    
    def save_tool_call_decorator(obj, func_name):
        func = getattr(obj, func_name)
        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            timestamp, tool_name, args = obj.tool_calls[-1]
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} [Tool Call] {tool_name}({args_str})\n")
        return wrapper

    def save_report_section_decorator(obj, func_name):
        func = getattr(obj, func_name)
        @wraps(func)
        def wrapper(section_name, content):
            func(section_name, content)
            if section_name in obj.report_sections and obj.report_sections[section_name] is not None:
                content = obj.report_sections[section_name]
                if content:
                    file_name = f"{section_name}.md"
                    text = "\n".join(str(item) for item in content) if isinstance(content, list) else content
                    with open(report_dir / file_name, "w", encoding="utf-8") as f:
                        f.write(text)
        return wrapper

    message_buffer.add_message = save_message_decorator(message_buffer, "add_message")
    message_buffer.add_tool_call = save_tool_call_decorator(message_buffer, "add_tool_call")
    message_buffer.update_report_section = save_report_section_decorator(message_buffer, "update_report_section")

    # Now start the display layout
    layout = create_layout()

    with Live(layout, refresh_per_second=4) as live:
        # Initial display
        update_display(layout, stats_handler=stats_handler, start_time=start_time)

        # Add initial messages
        message_buffer.add_message("System", f"Selected ticker: {selections['ticker']}")
        message_buffer.add_message(
            "System", f"Analysis date: {selections['analysis_date']}"
        )
        message_buffer.add_message(
            "System",
            f"Selected analysts: {', '.join(analyst.value for analyst in selections['analysts'])}",
        )
        update_display(layout, stats_handler=stats_handler, start_time=start_time)

        # Update agent status to in_progress for the first analyst
        first_analyst = f"{selections['analysts'][0].value.capitalize()} Analyst"
        message_buffer.update_agent_status(first_analyst, "in_progress")
        update_display(layout, stats_handler=stats_handler, start_time=start_time)

        # Create spinner text
        spinner_text = (
            f"Analyzing {selections['ticker']} on {selections['analysis_date']}..."
        )
        update_display(layout, spinner_text, stats_handler=stats_handler, start_time=start_time)

        # Initialize state and get graph args with callbacks
        init_agent_state = graph.propagator.create_initial_state(
            selections["ticker"], selections["analysis_date"]
        )
        # Pass callbacks to graph config for tool execution tracking
        # (LLM tracking is handled separately via LLM constructor)
        args = graph.propagator.get_graph_args(callbacks=[stats_handler])

        # Stream the analysis
        trace = []
        for chunk in graph.graph.stream(init_agent_state, **args):
            # Process all messages in chunk, deduplicating by message ID
            for message in chunk.get("messages", []):
                msg_id = getattr(message, "id", None)
                if msg_id is not None:
                    if msg_id in message_buffer._processed_message_ids:
                        continue
                    message_buffer._processed_message_ids.add(msg_id)

                msg_type, content = classify_message_type(message)
                if content and content.strip():
                    message_buffer.add_message(msg_type, content)

                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tool_call in message.tool_calls:
                        if isinstance(tool_call, dict):
                            message_buffer.add_tool_call(tool_call["name"], tool_call["args"])
                        else:
                            message_buffer.add_tool_call(tool_call.name, tool_call.args)

            # Update analyst statuses based on report state (runs on every chunk)
            update_analyst_statuses(message_buffer, chunk)

            # Research Team - Handle Investment Debate State
            if chunk.get("investment_debate_state"):
                debate_state = chunk["investment_debate_state"]
                bull_hist = debate_state.get("bull_history", "").strip()
                bear_hist = debate_state.get("bear_history", "").strip()
                judge = debate_state.get("judge_decision", "").strip()

                # Only update status when there's actual content
                if bull_hist or bear_hist:
                    update_research_team_status("in_progress")
                if bull_hist:
                    message_buffer.update_report_section(
                        "investment_plan", f"### Bull Researcher Analysis\n{bull_hist}"
                    )
                if bear_hist:
                    message_buffer.update_report_section(
                        "investment_plan", f"### Bear Researcher Analysis\n{bear_hist}"
                    )
                if judge:
                    message_buffer.update_report_section(
                        "investment_plan", f"### Research Manager Decision\n{judge}"
                    )
                    update_research_team_status("completed")
                    message_buffer.update_agent_status("Trader", "in_progress")

            # Trading Team
            if chunk.get("trader_investment_plan"):
                message_buffer.update_report_section(
                    "trader_investment_plan", chunk["trader_investment_plan"]
                )
                if message_buffer.agent_status.get("Trader") != "completed":
                    message_buffer.update_agent_status("Trader", "completed")
                    message_buffer.update_agent_status("Aggressive Analyst", "in_progress")

            # Risk Management Team - Handle Risk Debate State
            if chunk.get("risk_debate_state"):
                risk_state = chunk["risk_debate_state"]
                agg_hist = risk_state.get("aggressive_history", "").strip()
                con_hist = risk_state.get("conservative_history", "").strip()
                neu_hist = risk_state.get("neutral_history", "").strip()
                judge = risk_state.get("judge_decision", "").strip()

                if agg_hist:
                    if message_buffer.agent_status.get("Aggressive Analyst") != "completed":
                        message_buffer.update_agent_status("Aggressive Analyst", "in_progress")
                    message_buffer.update_report_section(
                        "final_trade_decision", f"### Aggressive Analyst Analysis\n{agg_hist}"
                    )
                if con_hist:
                    if message_buffer.agent_status.get("Conservative Analyst") != "completed":
                        message_buffer.update_agent_status("Conservative Analyst", "in_progress")
                    message_buffer.update_report_section(
                        "final_trade_decision", f"### Conservative Analyst Analysis\n{con_hist}"
                    )
                if neu_hist:
                    if message_buffer.agent_status.get("Neutral Analyst") != "completed":
                        message_buffer.update_agent_status("Neutral Analyst", "in_progress")
                    message_buffer.update_report_section(
                        "final_trade_decision", f"### Neutral Analyst Analysis\n{neu_hist}"
                    )
                if judge:
                    if message_buffer.agent_status.get("Portfolio Manager") != "completed":
                        message_buffer.update_agent_status("Portfolio Manager", "in_progress")
                        message_buffer.update_report_section(
                            "final_trade_decision", f"### Portfolio Manager Decision\n{judge}"
                        )
                        message_buffer.update_agent_status("Aggressive Analyst", "completed")
                        message_buffer.update_agent_status("Conservative Analyst", "completed")
                        message_buffer.update_agent_status("Neutral Analyst", "completed")
                        message_buffer.update_agent_status("Portfolio Manager", "completed")

            # Update the display
            update_display(layout, stats_handler=stats_handler, start_time=start_time)

            trace.append(chunk)

        # Streamed chunks are per-node deltas, not full state. Merge them
        # so every report field populated across the run is present.
        final_state = {}
        for chunk in trace:
            final_state.update(chunk)
        decision = graph.process_signal(final_state["final_trade_decision"])

        # Update all agent statuses to completed
        for agent in message_buffer.agent_status:
            message_buffer.update_agent_status(agent, "completed")

        message_buffer.add_message(
            "System", f"Completed analysis for {selections['analysis_date']}"
        )

        # Update final report sections
        for section in message_buffer.report_sections.keys():
            if section in final_state:
                message_buffer.update_report_section(section, final_state[section])

        update_display(layout, stats_handler=stats_handler, start_time=start_time)

    # Post-analysis prompts (outside Live context for clean interaction)
    console.print("\n[bold cyan]Analysis Complete![/bold cyan]\n")

    # Signal tracking — append to signal_log.csv
    _append_signal_log(config, selections["ticker"], selections["analysis_date"], decision)

    # Auto-save to local project reports/ folder (always, no prompt)
    local_reports_dir = config.get("results_dir_local")
    if local_reports_dir:
        local_path = Path(local_reports_dir) / selections["ticker"] / selections["analysis_date"]
        try:
            save_report_to_disk(final_state, selections["ticker"], local_path)
            console.print(f"[green]✓ Auto-saved to:[/green] {local_path.resolve()}")
        except Exception as e:
            console.print(f"[yellow]Auto-save failed: {e}[/yellow]")

    # Also save to ~/.tradingagents (original location, always)
    home_path = Path(config["results_dir"]) / selections["ticker"] / selections["analysis_date"]
    try:
        save_report_to_disk(final_state, selections["ticker"], home_path)
        console.print(f"[green]✓ Also saved to:[/green] {home_path.resolve()}")
    except Exception as e:
        console.print(f"[yellow]Home-dir save failed: {e}[/yellow]")

    # Prompt to display full report
    display_choice = typer.prompt("\nDisplay full report on screen?", default="Y").strip().upper()
    if display_choice in ("Y", "YES", ""):
        display_complete_report(final_state)


@app.command()
def analyze(
    checkpoint: bool = typer.Option(
        False,
        "--checkpoint",
        help="Enable checkpoint/resume: save state after each node so a crashed run can resume.",
    ),
    clear_checkpoints: bool = typer.Option(
        False,
        "--clear-checkpoints",
        help="Delete all saved checkpoints before running (force fresh start).",
    ),
):
    if clear_checkpoints:
        from tradingagents.graph.checkpointer import clear_all_checkpoints
        n = clear_all_checkpoints(DEFAULT_CONFIG["data_cache_dir"])
        console.print(f"[yellow]Cleared {n} checkpoint(s).[/yellow]")
    run_analysis(checkpoint=checkpoint)


@app.command(name="saas-finder")
def saas_finder_cmd(
    n: int = typer.Option(5, "--count", "-n", help="Number of companies to find (1–20)"),
    sector: str = typer.Option("", "--sector", "-s", help="Optional sector filter, e.g. 'Fintech'"),
    model: str = typer.Option("claude-sonnet-4-6", "--model", "-m", help="Claude model to use"),
    no_save: bool = typer.Option(False, "--no-save", help="Skip saving results to disk"),
):
    """Find top SaaS companies by Four-Dimension Moat score (Distribution / Data / Integration / Regulatory)."""
    from tradingagents.saas_finder import run_saas_finder

    rainbow_title = make_rainbow_text("  ★  STARLUKE SaaS Finder  ★  ")
    console.print(Panel(rainbow_title, border_style="cyan", expand=False))
    console.print(
        f"[cyan]Scanning for top [bold]{n}[/bold] SaaS moat candidates"
        + (f" in [bold]{sector}[/bold]" if sector else "")
        + "…[/cyan]\n"
    )

    messages = []

    def _cb(msg: str):
        messages.append(msg)
        console.print(f"  [dim]› {msg}[/dim]")

    try:
        results = run_saas_finder(
            n=n,
            sector_hint=sector,
            model=model,
            progress_cb=_cb,
            save=not no_save,
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    if not results:
        console.print("[yellow]No results returned.[/yellow]")
        return

    # Summary table
    table = Table(
        title=f"Top {len(results)} SaaS Moat Companies",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Ticker",       style="bold white",  width=8)
    table.add_column("Company",      style="white",       width=28)
    table.add_column("Sector",       style="dim white",   width=14)
    table.add_column("Distrib",      justify="center",    width=8)
    table.add_column("Data",         justify="center",    width=6)
    table.add_column("Integr",       justify="center",    width=7)
    table.add_column("Reg",          justify="center",    width=5)
    table.add_column("Total",        justify="center",    width=7)
    table.add_column("AI Stance",    style="dim",         width=10)

    for r in results:
        total = r.get("moat_total", 0)
        total_style = "green bold" if total >= 30 else ("yellow" if total >= 22 else "red")
        table.add_row(
            r.get("ticker", "?"),
            r.get("company", "?")[:27],
            r.get("sector", "?")[:13],
            str(r.get("moat_distribution", "?")),
            str(r.get("moat_data", "?")),
            str(r.get("moat_integration", "?")),
            str(r.get("moat_regulatory", "?")),
            f"[{total_style}]{total}/40[/{total_style}]",
            r.get("ai_stance", "?"),
        )

    console.print(table)
    console.print()

    # Detail panels
    for r in results:
        ticker = r.get("ticker", "?")
        company = r.get("company", "?")
        thesis = r.get("core_thesis", "N/A")
        risk = r.get("key_risk", "N/A")
        ai_data = r.get("ai_data_advantage", "N/A")
        ai_threat = r.get("ai_threat", "N/A")

        detail = (
            f"[bold cyan]Thesis:[/bold cyan] {thesis}\n"
            f"[bold yellow]Risk:[/bold yellow] {risk}\n"
            f"[dim]AI Data Advantage: {ai_data}  |  AI Threat: {ai_threat}[/dim]"
        )
        console.print(Panel(detail, title=f"[bold]{ticker}[/bold] — {company}", border_style="dim"))

    if not no_save:
        console.print("\n[green]✓ Results saved to reports/saas_finder/[/green]")


@app.command(name="report")
def report_cmd(
    ticker: Optional[str] = typer.Argument(None, help="Stock ticker (e.g. AAPL). Omit for interactive selection."),
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Report date YYYY-MM-DD. Omit for interactive selection."),
):
    """Browse and view saved analysis reports in the terminal."""
    import json as _json

    from tradingagents.default_config import DEFAULT_CONFIG
    results_dir = Path(DEFAULT_CONFIG["results_dir"])

    if not results_dir.exists():
        console.print("[yellow]No reports directory found. Run 'analyze' first.[/yellow]")
        raise typer.Exit(0)

    # ── Pick ticker ────────────────────────────────────────────────────────────
    tickers = sorted([
        p.name for p in results_dir.iterdir()
        if p.is_dir() and p.name not in ("signal_log.csv", "saas_finder")
    ])
    if not tickers:
        console.print("[yellow]No reports found yet. Run 'analyze' first.[/yellow]")
        raise typer.Exit(0)

    if ticker is None:
        ticker = questionary.select("Select ticker:", choices=tickers).ask()
        if ticker is None:
            raise typer.Exit(0)
    elif ticker.upper() not in tickers:
        console.print(f"[red]Ticker '{ticker}' not found. Available: {', '.join(tickers)}[/red]")
        raise typer.Exit(1)
    else:
        ticker = ticker.upper()

    ticker_dir = results_dir / ticker

    # ── Pick date ──────────────────────────────────────────────────────────────
    dates = sorted([
        p.name for p in ticker_dir.iterdir()
        if p.is_dir() and p.name not in ("TradingAgentsStrategy_logs",)
    ], reverse=True)
    if not dates:
        console.print(f"[yellow]No dated reports for {ticker}.[/yellow]")
        raise typer.Exit(0)

    if date is None:
        date = questionary.select(f"Select date for {ticker}:", choices=dates).ask()
        if date is None:
            raise typer.Exit(0)
    elif date not in dates:
        console.print(f"[red]Date '{date}' not found for {ticker}. Available: {', '.join(dates)}[/red]")
        raise typer.Exit(1)

    report_dir = ticker_dir / date

    # ── Load summary ───────────────────────────────────────────────────────────
    summary_path = report_dir / "summary.json"
    summary: dict = {}
    if summary_path.exists():
        try:
            summary = _json.loads(summary_path.read_bytes().decode("utf-8"))
        except Exception:
            pass

    # ── Header ─────────────────────────────────────────────────────────────────
    signal = summary.get("signal", "?")
    sig_color = {"BUY": "green", "SELL": "red", "HOLD": "yellow"}.get(signal, "white")
    generated = summary.get("generated_at", "")

    console.print()
    console.print(Rule(f"[bold]{ticker}[/bold]  ·  {date}  ·  [{sig_color}]● {signal}[/{sig_color}]", style="cyan"))
    if generated:
        console.print(f"[dim]Generated: {generated}[/dim]")
    console.print()

    # ── Try complete_report.md first (richest content) ─────────────────────────
    md_path = report_dir / "complete_report.md"
    if md_path.exists():
        try:
            md_text = md_path.read_bytes().decode("utf-8")
            console.print(Markdown(md_text))
            raise typer.Exit(0)
        except typer.Exit:
            raise
        except Exception:
            pass  # fall through to summary display

    # ── Fallback: render from summary.json fields ──────────────────────────────
    _SECTIONS = [
        ("analysts",         "📊 Analyst Reports"),
        ("bull_thesis",      "🟢 Bull Case"),
        ("bear_thesis",      "🔴 Bear Case"),
        ("research_plan",    "👔 Research Decision"),
        ("trader_plan",      "🤝 Trader Plan"),
        ("risk_aggressive",  "🔴 Risk · Aggressive"),
        ("risk_conservative","🟢 Risk · Conservative"),
        ("risk_neutral",     "🟡 Risk · Neutral"),
        ("final_decision",   "🏆 Portfolio Manager"),
    ]

    # interactive section pick
    available = [label for key, label in _SECTIONS if summary.get(key)]
    section_choice = questionary.select(
        "View section:",
        choices=["[All sections]"] + available,
    ).ask()
    if section_choice is None:
        raise typer.Exit(0)

    def _print_section(key: str, label: str):
        val = summary.get(key)
        if not val:
            return
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                console.print(Panel(
                    Markdown(str(sub_val)),
                    title=f"[bold]{label} · {sub_key}[/bold]",
                    border_style="dim",
                    padding=(1, 2),
                ))
        else:
            console.print(Panel(
                Markdown(str(val)),
                title=f"[bold]{label}[/bold]",
                border_style="dim",
                padding=(1, 2),
            ))

    if section_choice == "[All sections]":
        for key, label in _SECTIONS:
            _print_section(key, label)
    else:
        for key, label in _SECTIONS:
            if label == section_choice:
                _print_section(key, label)
                break


def key_for_label(sections, label):
    for k, l in sections:
        if l == label:
            return k
    return ""


if __name__ == "__main__":
    app()
