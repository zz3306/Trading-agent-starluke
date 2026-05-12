"""LangChain-compatible ChatModel that routes through the local Claude CLI.

Instead of calling the Anthropic API directly, this module shells out to the
`claude` CLI (Claude Code) which uses the user's existing login session.
No API key is required.

Tool-calling protocol
---------------------
The Claude CLI only accepts plain text prompts, so we simulate tool use via
prompt engineering:

  1. bind_tools() stores the tool list on the model instance.
  2. _generate() injects a tool-description block into every prompt.
  3. Claude is instructed to signal a tool call with the sentinel line:
       TOOL_CALL: {"name": "...", "args": {...}}
  4. We parse that line and populate AIMessage.tool_calls so LangGraph's
     ToolNode picks it up exactly as if a real API had returned a tool call.
  5. After the ToolNode executes the real Python function and appends a
     ToolMessage, the loop repeats until Claude responds without TOOL_CALL.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import uuid
from typing import Any, Iterator, List, Optional, Sequence

logger = logging.getLogger(__name__)

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from .base_client import BaseLLMClient

# ---------------------------------------------------------------------------
# Claude executable resolution (shared by this module, runner, and app)
# ---------------------------------------------------------------------------

def find_claude_exe() -> str:
    """Return the full path to the claude CLI executable.

    On Windows, Python subprocesses often inherit a narrower PATH than the
    user's interactive shell, so the npm global bin directory (where
    claude.cmd lives) may be absent.  We try four strategies in order:

    1. shutil.which("claude")     — standard PATH lookup (PATHEXT-aware)
    2. shutil.which("claude.cmd") — explicit .cmd variant for npm installs
    3. Hard-coded common Windows install locations
    4. Augment PATH with the npm global bin dir and retry which()

    Returns the resolved path, or bare "claude" as a last-resort fallback
    (Popen will raise FileNotFoundError if it still cannot be found).
    """
    if sys.platform != "win32":
        return shutil.which("claude") or "claude"

    home = os.path.expanduser("~")

    # Strategy 1 — probe known Windows locations first (deterministic, avoids
    # broken PATH entries that shutil.which might pick up before the real exe).
    candidates = [
        os.path.join(home, ".local", "bin", "claude.exe"),
        os.path.join(home, ".local", "bin", "claude.cmd"),
        os.path.join(home, "AppData", "Roaming", "npm", "claude.cmd"),
        os.path.join(home, "AppData", "Local", "Programs", "claude", "claude.exe"),
        os.path.expandvars(r"%APPDATA%\npm\claude.cmd"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\claude\claude.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    # Strategy 2 — shutil.which with existence validation (guards against
    # malformed PATH entries that resolve to non-existent paths).
    for name in ("claude", "claude.cmd"):
        exe = shutil.which(name)
        if exe and os.path.isfile(exe):
            return exe

    # Strategy 3 — augment PATH with common install dirs and retry which()
    npm_bin = os.path.join(home, "AppData", "Roaming", "npm")
    local_bin = os.path.join(home, ".local", "bin")
    augmented = local_bin + os.pathsep + npm_bin + os.pathsep + os.environ.get("PATH", "")
    for name in ("claude", "claude.cmd"):
        exe = shutil.which(name, path=augmented)
        if exe and os.path.isfile(exe):
            return exe

    return "claude"  # fallback; Popen will raise FileNotFoundError if missing


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_STRUCTURED_OUTPUT_TEMPLATE = """\
=== OUTPUT FORMAT ===
Respond with a single JSON object that matches this schema (no markdown fences, no extra text):
{schema}
=== END FORMAT ===

"""


# ---------------------------------------------------------------------------
# Core model
# ---------------------------------------------------------------------------

class ClaudeCLIChatModel(BaseChatModel):
    """Thin LangChain ChatModel wrapper around the `claude` CLI subprocess."""

    model_name: str = Field(default="claude-cli")
    timeout: int = Field(default=1800)
    # When True, pass --dangerously-skip-permissions so the CLI never blocks
    # on tool-approval prompts in non-interactive (subprocess) mode.
    skip_permissions: bool = Field(default=True)
    # Tools bound via .bind_tools(); stored as the raw LangChain tool objects.
    _tools: List[Any] = []
    # Pydantic schema dict injected via .with_structured_output().
    _output_schema: Optional[dict] = None

    model_config = {"arbitrary_types_allowed": True}

    # ------------------------------------------------------------------
    # LangChain interface
    # ------------------------------------------------------------------

    @property
    def _llm_type(self) -> str:
        return "claude-cli"

    def bind_tools(
        self,
        tools: Sequence[Any],
        **kwargs: Any,
    ) -> "ClaudeCLIChatModel":
        clone = ClaudeCLIChatModel(model_name=self.model_name, timeout=self.timeout, skip_permissions=self.skip_permissions)
        clone._tools = list(tools)
        clone._output_schema = self._output_schema
        return clone

    def with_structured_output(self, schema: Any, **kwargs: Any) -> "ClaudeCLIStructuredOutput":
        clone = ClaudeCLIChatModel(model_name=self.model_name, timeout=self.timeout, skip_permissions=self.skip_permissions)
        clone._tools = list(self._tools)
        if hasattr(schema, "model_json_schema"):
            clone._output_schema = schema.model_json_schema()
        elif hasattr(schema, "schema"):
            clone._output_schema = schema.schema()
        elif isinstance(schema, dict):
            clone._output_schema = schema
        else:
            clone._output_schema = {"description": str(schema)}
        return ClaudeCLIStructuredOutput(clone, schema)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        # When tools are bound: pre-execute them in Python and inject results
        # directly into the prompt. This avoids any custom TOOL_CALL text
        # protocol, which Claude Code CLI's safety system flags as prompt
        # injection (it correctly detects attempts to override its native tools).
        if self._tools:
            messages = self._prefetch_tool_results(messages)

        prompt = self._build_prompt(messages)
        raw = self._call_cli(prompt)
        message = self._parse_response(raw)
        return ChatResult(generations=[ChatGeneration(message=message)])

    # ------------------------------------------------------------------
    # Tool pre-fetching (claude_cli-specific agentic strategy)
    # ------------------------------------------------------------------

    def _prefetch_tool_results(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Execute all bound tools in Python and inject results as context.

        Extracts ticker + date from the message content, calls every bound
        tool with those parameters, and appends ToolMessages so Claude
        receives the data and only needs to write the analysis.
        """
        # Pull all text for parameter extraction
        full_text = " ".join(
            str(getattr(m, "content", "") or "") for m in messages
        )

        # Extract YYYY-MM-DD date
        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", full_text)
        curr_date = date_match.group(1) if date_match else ""

        # Extract stock ticker (1-5 uppercase letters, optional .XX suffix)
        ticker_match = re.search(r"\b([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b", full_text)
        ticker = ticker_match.group(1) if ticker_match else ""

        # Common technical indicators to pre-fetch for market analysts
        _INDICATORS = ["rsi", "macd", "sma", "ema", "bbands", "adx", "atr"]

        augmented = list(messages)
        for tool in self._tools:
            try:
                # get_indicators needs an explicit 'indicator' param — fetch each one
                if tool.name == "get_indicators":
                    combined = []
                    for ind in _INDICATORS:
                        try:
                            result = tool.invoke({
                                "symbol": ticker,
                                "indicator": ind,
                                "curr_date": curr_date,
                            })
                            combined.append(f"### {ind.upper()}\n{result}")
                        except Exception as exc:
                            logger.debug("Indicator %s failed: %s", ind, exc)
                    if combined:
                        augmented.append(ToolMessage(
                            content=f"[Technical Indicators for {ticker}]\n" + "\n\n".join(combined),
                            tool_call_id="prefetch_get_indicators",
                            name="get_indicators",
                        ))
                    continue

                args = self._infer_tool_args(tool, curr_date=curr_date, ticker=ticker)
                result = tool.invoke(args)
                augmented.append(
                    ToolMessage(
                        content=f"[Data from {tool.name}]\n{result}",
                        tool_call_id=f"prefetch_{tool.name}",
                        name=tool.name,
                    )
                )
                logger.debug("Pre-fetched tool %s → %d chars", tool.name, len(str(result)))
            except Exception as exc:
                logger.warning("Pre-fetch of %s failed (%s) — skipping", tool.name, exc)

        return augmented

    def _infer_tool_args(self, tool: Any, curr_date: str = "", ticker: str = "") -> dict:
        """Build an args dict for a tool by mapping its parameter names to
        the extracted date/ticker values."""
        schema: dict = {}
        if hasattr(tool, "args_schema") and tool.args_schema is not None:
            try:
                if hasattr(tool.args_schema, "model_json_schema"):
                    schema = tool.args_schema.model_json_schema()
                elif hasattr(tool.args_schema, "schema"):
                    schema = tool.args_schema.schema()
            except Exception:
                pass

        args: dict = {}
        for param_name in schema.get("properties", {}):
            low = param_name.lower()
            if "date" in low:
                args[param_name] = curr_date
            elif low in ("ticker", "symbol", "stock", "company"):
                args[param_name] = ticker
        return args

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_prompt(self, messages: List[BaseMessage]) -> str:
        parts: List[str] = []

        # Structured output instruction (for PM / structured nodes)
        if self._output_schema:
            parts.append(_STRUCTURED_OUTPUT_TEMPLATE.format(
                schema=json.dumps(self._output_schema, ensure_ascii=False, indent=2)
            ))

        # Render conversation — skip empty messages
        for msg in messages:
            content = getattr(msg, "content", "") or ""
            has_tool_calls = bool(getattr(msg, "tool_calls", None))
            if not content.strip() and not has_tool_calls:
                continue
            parts.append(self._render_message(msg))

        return "\n\n".join(p for p in parts if p)

    def _render_message(self, msg: BaseMessage) -> str:
        if isinstance(msg, SystemMessage):
            return f"<system>\n{msg.content}\n</system>"

        if isinstance(msg, HumanMessage):
            return f"<task>\n{msg.content}\n</task>"

        if isinstance(msg, AIMessage):
            return f"<previous_response>\n{msg.content or ''}\n</previous_response>"

        if isinstance(msg, ToolMessage):
            # Pre-fetched data arrives as ToolMessage — present as context
            tool_name = getattr(msg, "name", "data")
            return f"<data source=\"{tool_name}\">\n{msg.content}\n</data>"

        return f"<message>\n{msg.content}\n</message>"

    def _describe_tools_UNUSED(self) -> str:
        """Kept for reference. Not used since we switched to pre-fetch mode."""
        lines = []
        for tool in self._tools:
            name = getattr(tool, "name", str(tool))
            description = getattr(tool, "description", "")
            schema = {}
            if hasattr(tool, "args_schema") and tool.args_schema is not None:
                try:
                    if hasattr(tool.args_schema, "model_json_schema"):
                        schema = tool.args_schema.model_json_schema()
                    elif hasattr(tool.args_schema, "schema"):
                        schema = tool.args_schema.schema()
                except Exception:
                    pass

            props = schema.get("properties", {})
            required = schema.get("required", [])
            arg_parts = []
            for arg_name, arg_info in props.items():
                arg_desc = arg_info.get("description", arg_info.get("type", "any"))
                req_marker = "" if arg_name in required else " (optional)"
                arg_parts.append(f"{arg_name}: {arg_desc}{req_marker}")

            args_str = ", ".join(arg_parts) if arg_parts else "no arguments"
            lines.append(f"  • {name}({args_str})\n    {description}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # CLI invocation
    # ------------------------------------------------------------------

    def _call_cli(self, prompt: str) -> str:
        claude_exe = find_claude_exe()

        # Build a subprocess environment that includes the directories where
        # claude lives, regardless of what the parent process inherited.
        # This is the most reliable fix for Windows, where Python subprocesses
        # often inherit a PATH that's missing npm/local-bin entries.
        env = os.environ.copy()
        home = os.path.expanduser("~")
        _extra_paths = [
            os.path.join(home, ".local", "bin"),
            os.path.join(home, "AppData", "Roaming", "npm"),
            os.path.join(home, "AppData", "Local", "Programs", "claude"),
        ]
        # Prepend extra paths so they take priority over the inherited PATH.
        env["PATH"] = os.pathsep.join(_extra_paths) + os.pathsep + env.get("PATH", "")

        extra_kwargs: dict = {"env": env}
        if sys.platform == "win32":
            extra_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        cmd = [claude_exe, "--output-format", "text"]
        if self.skip_permissions:
            cmd.append("--dangerously-skip-permissions")
        if self.model_name and self.model_name != "claude-cli":
            cmd += ["--model", self.model_name]

        try:
            proc = subprocess.Popen(
                cmd + ["-p", prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                encoding="utf-8",
                errors="replace",
                **extra_kwargs,
            )
            stdout, stderr = proc.communicate(timeout=self.timeout)

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return "[ERROR] Claude CLI timed out"
        except FileNotFoundError:
            return (
                f"[ERROR] 'claude' command not found at '{claude_exe}' — "
                f"make sure Claude Code CLI is installed. "
                f"PATH searched: {env['PATH'][:200]}"
            )

        if proc.returncode != 0:
            return f"[ERROR] Claude CLI exit {proc.returncode}: {stderr.strip()}"

        return stdout.strip()

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, raw: str) -> AIMessage:
        # Structured output: extract JSON object from the response
        if self._output_schema:
            return AIMessage(content=self._extract_json(raw))
        # Plain text analysis response
        return AIMessage(content=raw)

    def _extract_json(self, text: str) -> str:
        """Strip markdown fences and return the first JSON object found."""
        # Remove ```json ... ``` fences
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"```", "", text)
        # Find first { ... } block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0).strip()
        return text.strip()


# ---------------------------------------------------------------------------
# Structured-output wrapper
# ---------------------------------------------------------------------------

class ClaudeCLIStructuredOutput:
    """Wraps ClaudeCLIChatModel so invoke() returns a Pydantic object.

    with_structured_output() injects the JSON schema into the prompt so
    Claude returns a JSON object. This class parses that JSON and
    instantiates the requested Pydantic schema, matching the contract that
    LangChain's real structured-output providers fulfil.
    """

    def __init__(self, base_model: "ClaudeCLIChatModel", schema: Any):
        self._base = base_model
        self._schema = schema

    def invoke(self, prompt: Any, **kwargs: Any) -> Any:
        result = self._base.invoke(prompt, **kwargs)
        raw = result.content if hasattr(result, "content") else str(result)

        # Extract JSON from the response
        json_str = self._base._extract_json(raw)
        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(
                f"ClaudeCLI structured output: could not parse JSON — {exc}\n"
                f"Raw output (first 300 chars): {raw[:300]}"
            ) from exc

        # Instantiate the Pydantic model
        if hasattr(self._schema, "model_validate"):
            return self._schema.model_validate(data)
        return self._schema(**data)


# ---------------------------------------------------------------------------
# BaseLLMClient adapter (plugs into the existing factory pattern)
# ---------------------------------------------------------------------------

class ClaudeCLIClient(BaseLLMClient):
    """Adapter so the factory can instantiate ClaudeCLIChatModel uniformly."""

    def get_llm(self) -> ClaudeCLIChatModel:
        return ClaudeCLIChatModel(
            model_name=self.model or "claude-cli",
            timeout=self.kwargs.get("claude_cli_timeout", 1800),
            skip_permissions=self.kwargs.get("claude_cli_skip_permissions", True),
        )

    def validate_model(self) -> bool:
        return True  # Any model name is accepted; CLI picks the active model
