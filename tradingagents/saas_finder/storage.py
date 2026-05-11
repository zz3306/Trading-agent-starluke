"""SaaS Finder storage — save results to reports/saas_finder/YYYY-MM-DD/."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def _get_save_dir() -> Path:
    try:
        from tradingagents.default_config import DEFAULT_CONFIG
        base = DEFAULT_CONFIG.get("results_dir", "reports")
    except Exception:
        base = "reports"
    return Path(base) / "saas_finder"


def save_results(
    results: List[Dict[str, Any]],
    n: int = 5,
    sector_hint: str = "",
) -> Path:
    """Save SaaS Finder results as JSON and markdown.

    Returns the directory path where files were saved.
    """
    today = datetime.today().strftime("%Y-%m-%d")
    slug = sector_hint.lower().replace(" ", "_") if sector_hint else "all"
    save_dir = _get_save_dir() / today
    save_dir.mkdir(parents=True, exist_ok=True)

    fname_base = f"saas_finder_{slug}_top{n}"

    # JSON
    json_path = save_dir / f"{fname_base}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Markdown
    md_path = save_dir / f"{fname_base}.md"
    lines = [
        f"# SaaS Finder — Top {n}{' · ' + sector_hint if sector_hint else ''}\n",
        f"*Generated: {today}*\n",
        "",
        "| Ticker | Company | Sector | Distrib | Data | Integr | Reg | **Total** | AI Stance | Core Thesis |",
        "|--------|---------|--------|---------|------|--------|-----|-----------|-----------|-------------|",
    ]
    for r in results:
        lines.append(
            f"| {r.get('ticker','?')} "
            f"| {r.get('company','?')} "
            f"| {r.get('sector','?')} "
            f"| {r.get('moat_distribution','?')} "
            f"| {r.get('moat_data','?')} "
            f"| {r.get('moat_integration','?')} "
            f"| {r.get('moat_regulatory','?')} "
            f"| **{r.get('moat_total','?')}** "
            f"| {r.get('ai_stance','?')} "
            f"| {r.get('core_thesis','?')} |"
        )

    lines += ["", "## Detailed Analysis", ""]
    for r in results:
        lines += [
            f"### {r.get('ticker','?')} — {r.get('company','?')}",
            f"**Sector:** {r.get('sector','?')}  |  **AI Stance:** {r.get('ai_stance','?')}",
            "",
            f"| Dimension | Score |",
            f"|-----------|-------|",
            f"| Distribution | {r.get('moat_distribution','?')}/10 |",
            f"| Proprietary Data | {r.get('moat_data','?')}/10 |",
            f"| Integration Depth | {r.get('moat_integration','?')}/10 |",
            f"| Regulatory/Compliance | {r.get('moat_regulatory','?')}/10 |",
            f"| **Total** | **{r.get('moat_total','?')}/40** |",
            "",
            f"**AI Data Advantage:** {r.get('ai_data_advantage','?')}",
            f"**AI Threat:** {r.get('ai_threat','?')}",
            "",
            f"**Core Thesis:** {r.get('core_thesis','?')}",
            f"**Key Risk:** {r.get('key_risk','?')}",
            "",
        ]

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return save_dir
