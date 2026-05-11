"""SaaS Finder runner — calls Claude CLI and parses the JSON response."""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Callable, Dict, List, Optional

from .prompt import SAAS_FINDER_SYSTEM, build_saas_finder_prompt
from .storage import save_results
from tradingagents.llm_clients.claude_cli_client import find_claude_exe


def _extract_json_array(text: str) -> List[Dict]:
    """Extract the first JSON array from raw LLM output (handles stray text)."""
    # Try direct parse first
    stripped = text.strip()
    if stripped.startswith("["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass

    # Find the first [...] block
    match = re.search(r"\[.*\]", stripped, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON array found in LLM output:\n{text[:500]}")


def run_saas_finder(
    n: int = 5,
    sector_hint: str = "",
    model: str = "claude-sonnet-4-6",
    timeout: int = 300,
    progress_cb: Optional[Callable[[str], None]] = None,
    save: bool = True,
) -> List[Dict[str, Any]]:
    """Run the SaaS Finder and return a list of company dicts.

    Args:
        n: Number of companies to find (1–20)
        sector_hint: Optional sector filter (e.g. "Fintech", "HR-Tech")
        model: Claude model to use
        timeout: Subprocess timeout in seconds
        progress_cb: Optional callback for status messages
        save: Whether to save results to disk

    Returns:
        List of dicts with moat scores and analysis
    """
    n = max(1, min(20, n))

    user_prompt = build_saas_finder_prompt(n, sector_hint)
    full_prompt = f"{SAAS_FINDER_SYSTEM}\n\n{user_prompt}"

    if progress_cb:
        progress_cb(f"Asking Claude to identify top {n} SaaS moat candidates…")

    cmd = [
        find_claude_exe(),
        "--output-format", "text",
        "--dangerously-skip-permissions",
        "-p", full_prompt,
    ]
    if model:
        cmd += ["--model", model]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            encoding="utf-8",
            errors="replace",
        )
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise RuntimeError(f"SaaS Finder timed out after {timeout}s")

    if proc.returncode != 0:
        raise RuntimeError(f"Claude CLI error: {stderr.strip()}")

    if progress_cb:
        progress_cb("Parsing results…")

    results = _extract_json_array(stdout)

    # Compute moat_total if missing
    dims = ["moat_distribution", "moat_data", "moat_integration", "moat_regulatory"]
    for r in results:
        if "moat_total" not in r or not r["moat_total"]:
            r["moat_total"] = sum(r.get(d, 0) for d in dims)

    # Sort by total descending
    results.sort(key=lambda x: x.get("moat_total", 0), reverse=True)

    if save:
        save_results(results, n=n, sector_hint=sector_hint)

    if progress_cb:
        progress_cb(f"Done — found {len(results)} companies.")

    return results
