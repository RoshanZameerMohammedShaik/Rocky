"""Main agent for Rocky.AI."""

from typing import Generator
from rich.console import Console
from rocky.llm.engine import LlamaCppEngine, ChatMessage
from rocky.llm.models import ModelManager
from rocky.llm.prompts import SYSTEM_PROMPT
from rocky.session.memory import ConversationMemory
from rocky.tools.base import ToolResult, get_tool_registry
from rocky.tools.files import (
    ReadFileTool, WriteFileTool, EditFileTool,
    ListDirectoryTool, SearchFilesTool,
)
from rocky.tools.shell import RunCommandTool
from rocky.tools.web import WebSearchTool, WebFetchTool
from rocky.tools.media import DescribeImageTool, TranscribeAudioTool, ProcessVideoTool
from rocky.tools.git import GitStatusTool, GitDiffTool, GitLogTool, GitCommitTool
from rocky.tools.knowledge import IndexFilesTool, SearchKnowledgeTool
from rocky.ui.animations import (
    ICONS, show_write_lines, show_edit_diff, show_read_shimmer,
)
from rocky.utils.logging import get_logger
from rocky.config import get_config

logger = get_logger(__name__)

# Tool names for special visual handling
FILE_WRITE_TOOLS = {"write_file"}
FILE_EDIT_TOOLS = {"edit_file"}
FILE_READ_TOOLS = {"read_file"}


class Agent:
    """The main Rocky.AI agent."""

    def __init__(self, console: Console):
        self.console = console
        self.config = get_config()
        self.engine = LlamaCppEngine()
        self.model_manager = ModelManager(self.engine, console)
        self.memory = ConversationMemory()
        self.memory.set_system_prompt(SYSTEM_PROMPT)
        self._register_tools()

    def _register_tools(self):
        """Register all available tools."""
        registry = get_tool_registry()
        tools = [
            ReadFileTool(), WriteFileTool(), EditFileTool(),
            ListDirectoryTool(), SearchFilesTool(),
            RunCommandTool(self.console),
            WebSearchTool(), WebFetchTool(),
            DescribeImageTool(), TranscribeAudioTool(), ProcessVideoTool(),
            GitStatusTool(), GitDiffTool(), GitLogTool(),
            GitCommitTool(self.console),
            IndexFilesTool(), SearchKnowledgeTool(),
        ]
        for tool in tools:
            registry.register(tool)

    def initialize(self) -> bool:
        """Initialize the agent - download and load the model."""
        try:
            import llama_cpp  # noqa: F401
        except ImportError:
            self.console.print("[red]Error: llama-cpp-python not installed.[/red]")
            self.console.print(
                "Install with: [bold]pip install llama-cpp-python[/bold]"
            )
            return False

        if not self.model_manager.ensure_model("text"):
            self.console.print("[red]Error: Failed to load model.[/red]")
            return False
        return True

    def process_message(self, user_input: str) -> Generator[str, None, None]:
        """Process a user message and yield response chunks."""
        self.memory.add_user_message(user_input)
        messages = self.memory.get_messages()

        registry = get_tool_registry()
        tools = registry.get_schemas()

        full_response = ""
        tool_calls = []

        # Collect full response first to detect tool calls
        for response in self.engine.chat(
            messages,
            tools=tools,
            temperature=self.config.model.temperature,
            max_tokens=self.config.model.max_tokens,
            stream=False,
        ):
            full_response += response.content
            tool_calls.extend(response.tool_calls)

        # If no native tool calls, parse from text
        if not tool_calls:
            tool_calls = self.engine._parse_tool_calls(full_response)

        # Yield clean text (strip tool call markup)
        if tool_calls:
            import re
            clean = re.sub(
                r'<tool_call>[\s\S]*?</tool_call>', '', full_response
            ).strip()
            if clean:
                yield clean
        else:
            yield full_response

        # Handle tool calls with visual feedback
        if tool_calls:
            for tc in tool_calls:
                yield "\n"
                self.console.print(
                    f"  {ICONS['processing']} [bold]Using:[/bold] {tc.name}"
                )

                result = self._execute_tool(tc.name, tc.arguments)
                self._show_tool_result(tc.name, tc.arguments, result)
                self.memory.add_tool_result(
                    tc.name, result.output or result.error or ""
                )

                # Get follow-up response
                yield from self._get_followup_response(tc.name, result)

        self.memory.add_assistant_message(full_response, tool_calls=[
            {"name": tc.name, "arguments": tc.arguments} for tc in tool_calls
        ])

    def _show_tool_result(self, name: str, args: dict, result: ToolResult):
        """Show tool results with appropriate visual animation."""
        if not result.success:
            self.console.print(
                f"  {ICONS['error']} [red]{result.error}[/red]"
            )
            return

        filepath = args.get("path", "file")

        # File write: green +lines
        if name in FILE_WRITE_TOOLS:
            content = args.get("content", "")
            if content:
                show_write_lines(self.console, filepath, content)
            else:
                self.console.print(
                    f"  {ICONS['success']} [green]{result.output}[/green]"
                )

        # File edit: red -lines then green +lines
        elif name in FILE_EDIT_TOOLS:
            old_str = args.get("old_str", "")
            new_str = args.get("new_str", "")
            show_edit_diff(self.console, filepath, old_str, new_str)

        # File read: shimmer animation
        elif name in FILE_READ_TOOLS:
            content = result.output or ""
            if content and len(content) > 0:
                show_read_shimmer(self.console, filepath, content)
            else:
                self.console.print(
                    f"  {ICONS['success']} {result.output[:300]}"
                )

        # Other tools: plain output
        else:
            output = result.output[:500] if result.output else ""
            if output:
                self.console.print(
                    f"  {ICONS['success']} [green]{output}[/green]"
                )

    def _get_followup_response(
        self, tool_name: str, result: ToolResult
    ) -> Generator[str, None, None]:
        """Get a follow-up response after tool execution."""
        followup_messages = self.memory.get_messages()
        followup_messages.append(ChatMessage(
            role="tool",
            content=f"Tool '{tool_name}' result: {result.output or result.error}",
            tool_call_id=f"result_{tool_name}",
        ))
        yield "\n"
        for response in self.engine.chat(
            followup_messages,
            temperature=self.config.model.temperature,
            max_tokens=self.config.model.max_tokens,
            stream=True,
        ):
            if response.content:
                yield response.content

    def _execute_tool(self, name: str, arguments: dict) -> ToolResult:
        """Execute a tool by name."""
        registry = get_tool_registry()
        tool = registry.get(name)
        if not tool:
            return ToolResult.fail(f"Unknown tool: {name}")
        try:
            return tool.execute(**arguments)
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return ToolResult.fail(str(e))

    def clear_memory(self):
        """Clear conversation memory."""
        self.memory.clear()
        self.memory.set_system_prompt(SYSTEM_PROMPT)

    def get_memory(self) -> ConversationMemory:
        return self.memory

    def set_memory(self, memory: ConversationMemory):
        self.memory = memory
        if not self.memory.system_prompt:
            self.memory.set_system_prompt(SYSTEM_PROMPT)
