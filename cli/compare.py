"""AI-powered side-by-side comparison of multiple company analysis reports."""

from __future__ import annotations

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

import questionary
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()


# ---------------------------------------------------------------------------
# Report discovery
# ---------------------------------------------------------------------------

def _find_reports(reports_dir: Path) -> dict[str, Path]:
    """Return {TICKER: latest_date_dir} for all tickers that have a complete_report.md."""
    available: dict[str, Path] = {}
    if not reports_dir.exists():
        return available
    for ticker_dir in sorted(reports_dir.iterdir()):
        if not ticker_dir.is_dir() or ticker_dir.name.startswith("."):
            continue
        date_dirs = sorted(
            [d for d in ticker_dir.iterdir()
             if d.is_dir() and (d / "complete_report.md").exists()],
            key=lambda d: d.name,
            reverse=True,
        )
        if date_dirs:
            available[ticker_dir.name] = date_dirs[0]
    return available


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_compare(reports_dir: Path) -> None:
    """Interactively compare 2–5 company reports with AI analysis."""

    available = _find_reports(reports_dir)

    if len(available) < 2:
        console.print(
            "[red]Need at least 2 companies with completed reports to compare.\n"
            f"Reports directory: {reports_dir.resolve()}[/red]"
        )
        return

    # ── Select companies ──────────────────────────────────────────────────────
    choices = [
        questionary.Choice(f"{ticker}  (analysed {path.name})", value=ticker)
        for ticker, path in available.items()
    ]
    selected: list[str] | None = questionary.checkbox(
        "Select companies to compare (2–5):",
        choices=choices,
    ).ask()

    if not selected or len(selected) < 2:
        console.print("[yellow]Please select at least 2 companies.[/yellow]")
        return
    if len(selected) > 5:
        console.print("[yellow]More than 5 selected — using first 5.[/yellow]")
        selected = selected[:5]

    # ── Language ──────────────────────────────────────────────────────────────
    language: str = questionary.select(
        "Output language:",
        choices=[
            questionary.Choice("English", "English"),
            questionary.Choice("Chinese (中文)", "Chinese"),
        ],
    ).ask() or "English"

    # ── Read reports ──────────────────────────────────────────────────────────
    console.print(f"\n[cyan]Loading reports for {', '.join(selected)}…[/cyan]")
    sections: list[str] = []
    for ticker in selected:
        report_path = available[ticker] / "complete_report.md"
        try:
            content = report_path.read_text(encoding="utf-8")
            sections.append(
                f"### {ticker}  (analysed {available[ticker].name})\n\n{content}"
            )
        except Exception as exc:
            console.print(f"[red]Cannot read {ticker} report: {exc}[/red]")
            return

    # ── Build prompt ──────────────────────────────────────────────────────────
    lang_tag = f" Respond entirely in {language}." if language != "English" else ""
    joined = "\n\n---\n\n".join(sections)

    prompt = f"""You are a senior portfolio analyst comparing investment reports for \
{len(selected)} stocks: {", ".join(selected)}.{lang_tag}

{joined}

---

Using only the reports above, produce a structured comparison:

**1. Overall Ranking** (most attractive → least for buying now)
Rank each stock with a 2–3 sentence justification.

**2. Per-Stock Action Plan**
For each stock:
- Signal: BUY / HOLD / AVOID
- Entry: suggested price level or condition
- Timeframe: short-term trade vs long-term hold
- Key catalyst to watch

**3. Risk & Reward Comparison**
- Which has the lowest downside risk?
- Which has the highest upside potential?
- Best pair to hold together in a portfolio (if any)?

**4. Final Recommendation**
- If you could buy only ONE, which and why?
- Suggested capital allocation across all selected stocks (must sum to 100%).

Be specific. Reference actual figures and data points from the reports."""

    # ── Call Claude CLI ───────────────────────────────────────────────────────
    from tradingagents.llm_clients.claude_cli_client import find_claude_exe

    claude_exe = find_claude_exe()
    env = os.environ.copy()
    home = os.path.expanduser("~")
    env["PATH"] = os.pathsep.join([
        os.path.join(home, ".local", "bin"),
        os.path.join(home, "AppData", "Roaming", "npm"),
        os.path.join(home, "AppData", "Local", "Programs", "claude"),
    ]) + os.pathsep + env.get("PATH", "")

    extra: dict = {"env": env}
    if sys.platform == "win32":
        extra["creationflags"] = subprocess.CREATE_NO_WINDOW

    console.print("[cyan]Running AI comparison (30–90 s)…[/cyan]\n")

    try:
        proc = subprocess.Popen(
            [
                claude_exe, "--output-format", "text",
                "--dangerously-skip-permissions", "-p", prompt,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            encoding="utf-8",
            errors="replace",
            **extra,
        )
        stdout, stderr = proc.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        console.print("[red]Comparison timed out after 5 minutes.[/red]")
        return
    except FileNotFoundError:
        console.print(
            f"[red]Claude CLI not found at '{claude_exe}'. "
            "Run 'npm install -g @anthropic-ai/claude-code' and log in.[/red]"
        )
        return

    if proc.returncode != 0:
        console.print(
            f"[red]Claude CLI error (exit {proc.returncode}):\n{stderr.strip()[:400]}[/red]"
        )
        return

    result = stdout.strip()
    if not result:
        console.print("[red]Empty response from Claude CLI.[/red]")
        return

    # ── Display ───────────────────────────────────────────────────────────────
    title = " vs ".join(selected)
    console.print(
        Panel(
            Markdown(result),
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # ── Save ──────────────────────────────────────────────────────────────────
    if questionary.confirm("Save comparison report to reports folder?", default=True).ask():
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        fname = f"comparison_{'_vs_'.join(selected)}_{stamp}.md"
        out_path = reports_dir / fname
        out_path.write_text(
            f"# Comparison: {title}\n"
            f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n"
            f"{result}",
            encoding="utf-8",
        )
        console.print(f"[green]✓ Saved → {out_path.resolve()}[/green]")
