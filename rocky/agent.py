"""Main agent for Rocky.Ai."""

from typing import Generator
from queue import Queue
from rich.console import Console
from rocky.llm.engine import LlamaCppEngine
from rocky.llm.models import ModelManager
from rocky.llm.prompts import SYSTEM_PROMPT, build_system_prompt
from rocky.session.memory import ConversationMemory
from rocky.tools.base import ToolResult, get_tool_registry
from rocky.tools.files import (
    ReadFileTool, WriteFileTool, EditFileTool,
    ListDirectoryTool, SearchFilesTool,
    GlobFilesTool, SummarizeFileTool,
)
from rocky.tools.shell import RunCommandTool
from rocky.tools.web import WebSearchTool, WebFetchTool
from rocky.tools.media import DescribeImageTool, TranscribeAudioTool, ProcessVideoTool
from rocky.tools.git import GitStatusTool, GitDiffTool, GitLogTool, GitCommitTool
from rocky.tools.knowledge import IndexFilesTool, SearchKnowledgeTool
from rocky.tools.task_plan import TaskPlanTool
from rocky.ui.animations import (
    ICONS, show_write_lines, show_edit_diff, show_read_shimmer,
)
from rocky.ui.permissions import get_permission_manager, PermissionDecision
from rocky.ui.stream import StreamRenderer
from rocky.context import ContextGatherer
from rocky.persona import PersonaManager
from rocky.utils.logging import get_logger
from rocky.config import get_config

logger = get_logger(__name__)

# Tool names for special visual handling
FILE_WRITE_TOOLS = {"write_file"}
FILE_EDIT_TOOLS = {"edit_file"}
FILE_READ_TOOLS = {"read_file"}


class Agent:
    """The main Rocky.Ai agent."""

    def __init__(self, console: Console):
        self.console = console
        self.config = get_config()
        self.engine = LlamaCppEngine()
        self.model_manager = ModelManager(self.engine, console)
        self.memory = ConversationMemory()
        self.memory.set_system_prompt(SYSTEM_PROMPT)
        self.context = ContextGatherer()
        self.persona = PersonaManager()
        self.stream_renderer = StreamRenderer(console)
        self.btw_queue: Queue = Queue()
        self._max_iterations = 100
        self._register_tools()

    def _register_tools(self):
        """Register all available tools."""
        registry = get_tool_registry()
        tools = [
            ReadFileTool(), WriteFileTool(), EditFileTool(),
            ListDirectoryTool(), SearchFilesTool(),
            GlobFilesTool(), SummarizeFileTool(),
            RunCommandTool(self.console),
            WebSearchTool(), WebFetchTool(),
            DescribeImageTool(), TranscribeAudioTool(), ProcessVideoTool(),
            GitStatusTool(), GitDiffTool(), GitLogTool(),
            GitCommitTool(self.console),
            IndexFilesTool(), SearchKnowledgeTool(),
            TaskPlanTool(),
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

        # Gather initial context and learn from environment
        ctx = self.context.gather()
        self.persona.passive_learn_from_environment(ctx.working_dir)

        # Build dynamic system prompt
        system_prompt = build_system_prompt(
            context_block=ctx.render_for_prompt(),
            persona_block=self.persona.render_summary()
        )
        self.memory.set_system_prompt(system_prompt)

        return True

    def process_message(self, user_input: str) -> Generator[str, None, None]:
        """Process a user message with full agentic reasoning loop."""
        self.memory.add_user_message(user_input)

        # Passive persona learning
        self.persona.passive_learn_from_message(user_input)

        registry = get_tool_registry()
        tools = registry.get_schemas()
        permission_manager = get_permission_manager()

        iteration = 0
        consecutive_errors = 0
        recent_calls: list[tuple[str, str]] = []  # (tool_name, args_hash) for loop detection

        while iteration < self._max_iterations:
            iteration += 1

            # Check for /btw injections
            while not self.btw_queue.empty():
                btw_msg = self.btw_queue.get()
                self.memory.add_mid_task_instruction(btw_msg)
                self.console.print("  [cyan]⠧ Noted — adjusting...[/cyan]")

            # Get LLM response
            messages = self.memory.get_messages()
            full_response = ""
            tool_calls = []

            for response in self.engine.chat(
                messages,
                tools=tools,
                temperature=self.config.model.temperature,
                max_tokens=self.config.model.max_tokens,
                stream=True,
            ):
                if response.tool_calls:
                    tool_calls.extend(response.tool_calls)
                if response.content:
                    full_response += response.content
                    yield response.content

            # Parse tool calls from response text if engine didn't extract them
            if not tool_calls:
                tool_calls = self.engine._parse_tool_calls(full_response)

            # If no tool calls — normal exit (LLM is done)
            if not tool_calls:
                self.memory.add_assistant_message(full_response)
                break

            # Execute tool calls
            self.memory.add_assistant_message(full_response, tool_calls=[
                {"name": tc.name, "arguments": tc.arguments} for tc in tool_calls
            ])

            for tc in tool_calls:
                # Loop detection
                args_hash = str(sorted(tc.arguments.items())) if tc.arguments else ""
                call_sig = (tc.name, args_hash)
                recent_calls.append(call_sig)
                if recent_calls.count(call_sig) >= 3:
                    yield f"\n⚠ Detected loop: called {tc.name} with same args 3 times. Stopping.\n"
                    return

                # Permission check
                command = tc.arguments.get("command", "") if tc.name == "run_command" else ""
                allowed = permission_manager.should_allow(tc.name, command)

                if allowed is False:
                    reason = permission_manager.get_block_reason(command) if command else "Denied"
                    self.console.print(f"  [red]✘ Blocked: {reason}[/red]")
                    self.memory.add_tool_result(tc.name, f"BLOCKED: {reason}")
                    consecutive_errors += 1
                    continue
                elif allowed is None:
                    # Need to prompt user
                    detail = f"{tc.name}({', '.join(f'{k}={repr(v)[:30]}' for k,v in tc.arguments.items())})"
                    decision = permission_manager.prompt_user(self.console, tc.name, detail)
                    if decision == PermissionDecision.DENY:
                        self.memory.add_tool_result(tc.name, "DENIED by user")
                        continue
                    # ALLOW_ONCE, TRUST, TRUST_ALL all allow execution

                # Execute tool with visual feedback
                yield "\n"
                self.console.print(f"  [cyan]⠧[/cyan] [bold]Using:[/bold] {tc.name}")

                result = self._execute_tool(tc.name, tc.arguments)
                self._show_tool_result(tc.name, tc.arguments, result)

                # Track errors
                if not result.success:
                    consecutive_errors += 1
                    if consecutive_errors >= 5:
                        yield "\n⚠ 5 consecutive errors. Pausing — here's what's failing:\n"
                        yield f"Last error: {result.error}\n"
                        return
                else:
                    consecutive_errors = 0

                # Add result to memory
                self.memory.add_tool_result(
                    tc.name, result.output or result.error or ""
                )

                # Context refresh if needed
                if self.context.should_refresh(tc.name):
                    self.context.refresh_git_only()

            # Keep recent_calls bounded
            if len(recent_calls) > 30:
                recent_calls = recent_calls[-15:]

        else:
            # Safety ceiling hit
            yield "\n⚠ Reached maximum iterations (100). Stopping.\n"
            yield self._progress_summary()

    def _show_tool_result(self, name: str, args: dict, result: ToolResult):
        """Show tool results with appropriate visual animation."""
        if not result.success:
            self.console.print(
                f"  {ICONS['fail']} [red]{result.error}[/red]"
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
                    f"  {ICONS['done']} [green]{result.output}[/green]"
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
                    f"  {ICONS['done']} {result.output[:300]}"
                )

        # Other tools: plain output
        else:
            output = result.output[:500] if result.output else ""
            if output:
                self.console.print(
                    f"  {ICONS['done']} [green]{output}[/green]"
                )

    def _progress_summary(self) -> str:
        """Generate a progress summary when stopped mid-task."""
        return "Say 'continue' to resume where I left off.\n"

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
        ctx = self.context.current
        system_prompt = build_system_prompt(
            context_block=ctx.render_for_prompt() if ctx else "",
            persona_block=self.persona.render_summary()
        )
        self.memory.set_system_prompt(system_prompt)

    def get_memory(self) -> ConversationMemory:
        return self.memory

    def set_memory(self, memory: ConversationMemory):
        self.memory = memory
        if not self.memory.system_prompt:
            self.memory.set_system_prompt(SYSTEM_PROMPT)
