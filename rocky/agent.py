"""Main agent for Rocky.AI."""

from typing import Generator
from rich.console import Console
from rocky.llm.engine import LlamaCppEngine, ChatMessage
from rocky.llm.models import ModelManager
from rocky.llm.prompts import SYSTEM_PROMPT
from rocky.session.memory import ConversationMemory
from rocky.tools.base import ToolResult, get_tool_registry
from rocky.tools.files import ReadFileTool, WriteFileTool, EditFileTool, ListDirectoryTool, SearchFilesTool
from rocky.tools.shell import RunCommandTool
from rocky.tools.web import WebSearchTool, WebFetchTool
from rocky.tools.media import DescribeImageTool, TranscribeAudioTool, ProcessVideoTool
from rocky.tools.git import GitStatusTool, GitDiffTool, GitLogTool, GitCommitTool
from rocky.tools.knowledge import IndexFilesTool, SearchKnowledgeTool
from rocky.ui.animations import ICONS
from rocky.ui.diff import show_file_change
from rocky.utils.logging import get_logger
from rocky.config import get_config
from pathlib import Path

logger = get_logger(__name__)


class Agent:
    """The main Rocky.AI agent."""

    def __init__(self, console: Console):
        self.console = console
        self.config = get_config()
        self.engine = LlamaCppEngine()
        self.model_manager = ModelManager(self.engine, console)
        self.memory = ConversationMemory()
        self.memory.set_system_prompt(SYSTEM_PROMPT)

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register all available tools."""
        registry = get_tool_registry()

        tools = [
            # File operations
            ReadFileTool(),
            WriteFileTool(),
            EditFileTool(),
            ListDirectoryTool(),
            SearchFilesTool(),
            # Shell
            RunCommandTool(self.console),
            # Web
            WebSearchTool(),
            WebFetchTool(),
            # Media
            DescribeImageTool(),
            TranscribeAudioTool(),
            ProcessVideoTool(),
            # Git
            GitStatusTool(),
            GitDiffTool(),
            GitLogTool(),
            GitCommitTool(self.console),
            # Knowledge
            IndexFilesTool(),
            SearchKnowledgeTool(),
        ]

        for tool in tools:
            registry.register(tool)

    def initialize(self) -> bool:
        """Initialize the agent — download and load the model."""
        try:
            # Check if llama-cpp-python is installed
            import llama_cpp  # noqa: F401
        except ImportError:
            self.console.print("[red]Error: llama-cpp-python not installed.[/red]")
            self.console.print("Install with: [bold]pip install llama-cpp-python[/bold]")
            return False

        # Ensure text model is available (downloads if needed)
        if not self.model_manager.ensure_model("text"):
            self.console.print("[red]Error: Failed to load model.[/red]")
            return False

        return True

    def process_message(self, user_input: str) -> Generator[str, None, None]:
        """Process a user message and yield response chunks."""

        # Add to memory
        self.memory.add_user_message(user_input)

        # Get messages for LLM
        messages = self.memory.get_messages()

        # Get tool schemas
        registry = get_tool_registry()
        tools = registry.get_schemas()

        # Stream response from LLM
        full_response = ""
        tool_calls = []

        for response in self.engine.chat(
            messages,
            tools=tools,
            temperature=self.config.model.temperature,
            max_tokens=self.config.model.max_tokens,
            stream=True,
        ):
            if response.content:
                full_response += response.content
                yield response.content

            if response.tool_calls:
                tool_calls.extend(response.tool_calls)

        # Handle tool calls
        if tool_calls:
            for tc in tool_calls:
                yield f"\n\n{ICONS['processing']} Using tool: {tc.name}...\n"

                result = self._execute_tool(tc.name, tc.arguments)

                if result.success:
                    yield f"{ICONS['success']} {result.output[:500]}\n"

                    # Show diff for file operations
                    if result.data and "old_content" in result.data and "new_content" in result.data:
                        show_file_change(
                            self.console,
                            Path(result.data.get("path", "file")),
                            result.data["old_content"],
                            result.data["new_content"],
                            result.data.get("action", "modified")
                        )
                else:
                    yield f"{ICONS['error']} Error: {result.error}\n"

                # Add tool result to memory
                self.memory.add_tool_result(tc.name, result.output or result.error or "")

                # Get follow-up response after tool use
                yield from self._get_followup_response(tc.name, result)

        # Add assistant response to memory
        self.memory.add_assistant_message(full_response, tool_calls=[
            {"name": tc.name, "arguments": tc.arguments} for tc in tool_calls
        ])

    def _get_followup_response(self, tool_name: str, result: ToolResult) -> Generator[str, None, None]:
        """Get a follow-up response after tool execution."""
        # Add tool result as a message and get model's interpretation
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
        """Get the conversation memory."""
        return self.memory

    def set_memory(self, memory: ConversationMemory):
        """Set the conversation memory."""
        self.memory = memory
        if not self.memory.system_prompt:
            self.memory.set_system_prompt(SYSTEM_PROMPT)
