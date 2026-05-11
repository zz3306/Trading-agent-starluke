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
import re
import subprocess
import uuid
from typing import Any, Iterator, List, Optional, Sequence

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
# Prompt templates
# ---------------------------------------------------------------------------

_TOOL_BLOCK_TEMPLATE = """\
=== AVAILABLE TOOLS ===
You may call ONE tool per reply by outputting EXACTLY this line (and nothing else on that line):
TOOL_CALL: {{"name": "<tool_name>", "args": {{<json arguments>}}}}

Rules:
- Output the TOOL_CALL line only when you need to call a tool.
- Do NOT add any text on the same line as TOOL_CALL.
- After receiving a tool result you may call another tool or write your final answer.
- If you do not need a tool, just respond normally — no TOOL_CALL line.
- CRITICAL: You are a pure text reasoning engine. Do NOT execute Python code, run shell
  commands, or use any built-in Claude tools (Bash, Read, Write, WebSearch, etc.).
  Do NOT attempt to fetch data yourself. ALL data retrieval must go through the
  TOOL_CALL format above — the calling system will execute the actual function.
  If you cannot call a tool, say so in plain text; never attempt direct code execution.

Tools:
{tool_descriptions}
=== END TOOLS ===

"""

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
    timeout: int = Field(default=600)
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
        prompt = self._build_prompt(messages)
        raw = self._call_cli(prompt)
        message = self._parse_response(raw)
        return ChatResult(generations=[ChatGeneration(message=message)])

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_prompt(self, messages: List[BaseMessage]) -> str:
        parts: List[str] = []

        # Prepend tool block if tools are bound
        if self._tools:
            parts.append(_TOOL_BLOCK_TEMPLATE.format(
                tool_descriptions=self._describe_tools()
            ))

        # Prepend structured output instruction if schema set
        if self._output_schema:
            parts.append(_STRUCTURED_OUTPUT_TEMPLATE.format(
                schema=json.dumps(self._output_schema, ensure_ascii=False, indent=2)
            ))

        # Convert message history
        for msg in messages:
            parts.append(self._render_message(msg))

        return "\n\n".join(p for p in parts if p)

    def _render_message(self, msg: BaseMessage) -> str:
        if isinstance(msg, SystemMessage):
            return f"[SYSTEM]\n{msg.content}"

        if isinstance(msg, HumanMessage):
            return f"[USER]\n{msg.content}"

        if isinstance(msg, AIMessage):
            content = msg.content or ""
            # Re-render any tool calls the assistant previously made
            for tc in (msg.tool_calls or []):
                content += (
                    f"\nTOOL_CALL: {json.dumps({'name': tc['name'], 'args': tc['args']}, ensure_ascii=False)}"
                )
            return f"[ASSISTANT]\n{content}"

        if isinstance(msg, ToolMessage):
            tool_name = getattr(msg, "name", "tool")
            return f"[TOOL RESULT — {tool_name}]\n{msg.content}"

        # Fallback for any other message type
        return f"[MESSAGE]\n{msg.content}"

    def _describe_tools(self) -> str:
        lines = []
        for tool in self._tools:
            name = getattr(tool, "name", str(tool))
            description = getattr(tool, "description", "")
            # Try to get argument descriptions from the pydantic schema
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
        import sys

        # Build base command.
        cmd = ["claude", "--output-format", "text"]
        if self.skip_permissions:
            cmd.append("--dangerously-skip-permissions")
        if self.model_name and self.model_name != "claude-cli":
            cmd += ["--model", self.model_name]

        try:
            proc = subprocess.Popen(
                cmd + ["-p", prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,  # prevent any tty blocking
                encoding="utf-8",
                errors="replace",
                **( {"creationflags": subprocess.CREATE_NO_WINDOW}
                    if sys.platform == "win32" else {} ),
            )
            stdout, stderr = proc.communicate(timeout=self.timeout)

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return "[ERROR] Claude CLI timed out"
        except FileNotFoundError:
            return "[ERROR] 'claude' command not found — make sure Claude Code CLI is installed and in PATH"

        if proc.returncode != 0:
            return f"[ERROR] Claude CLI exit {proc.returncode}: {stderr.strip()}"

        return stdout.strip()

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, raw: str) -> AIMessage:
        # Check for structured output mode first
        if self._output_schema and not self._tools:
            return AIMessage(content=self._extract_json(raw))

        # Check for tool call
        tool_call, text_before = self._extract_tool_call(raw)
        if tool_call:
            return AIMessage(
                content=text_before,
                tool_calls=[{
                    "name": tool_call["name"],
                    "args": tool_call.get("args", {}),
                    "id": f"call_{uuid.uuid4().hex[:12]}",
                    "type": "tool_call",
                }],
            )

        return AIMessage(content=raw)

    def _extract_tool_call(self, text: str):
        """Return (tool_call_dict, text_before) or (None, text)."""
        # Match TOOL_CALL: followed by a JSON object (possibly multi-line)
        pattern = r"TOOL_CALL:\s*(\{.*?\})\s*$"
        match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
        if match:
            try:
                data = json.loads(match.group(1))
                before = text[: match.start()].strip()
                return data, before
            except json.JSONDecodeError:
                pass
        return None, text

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
            timeout=self.kwargs.get("claude_cli_timeout", 600),
            skip_permissions=self.kwargs.get("claude_cli_skip_permissions", True),
        )

    def validate_model(self) -> bool:
        return True  # Any model name is accepted; CLI picks the active model
