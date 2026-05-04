"""CLI entry point for Rocky.Ai."""

import sys
import signal
from typing import Optional
from rich.console import Console

from rocky import __version__, __app_name__
from rocky.agent import Agent
from rocky.agent_runner import AgentRunner
from rocky.session import SessionManager
from rocky.ui.splash import show_splash, show_goodbye
from rocky.ui.input import get_input_handler
from rocky.ui.permissions import get_permission_manager
from rocky.ui.animations import ICONS
from rocky.ui.menu import ArrowMenu
from rocky.tools.shell import get_job_manager
from rocky.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


class RockyCLI:
    """Main CLI application."""

    def __init__(self):
        self.console = Console()
        self.agent: Optional[Agent] = None
        self.runner: Optional[AgentRunner] = None
        self.session_manager = SessionManager()
        self.running = True

        # Setup interrupt handler
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, sig, frame):
        """Handle Ctrl+C — stop agent when working, quit menu when idle."""
        if self.runner and self.runner.is_working:
            self.runner.request_stop()
            self.console.print("\n[yellow]⚠ Stopping...[/yellow]")
        else:
            # Show quit menu
            menu = ArrowMenu(
                title="Quit Rocky.Ai?",
                options=["Yes", "No", "Refresh and quit"],
                default=0,
                console=self.console,
            )
            try:
                choice = menu.run()
                if choice == "Yes":
                    self.running = False
                elif choice == "Refresh and quit":
                    if self.agent:
                        self.agent.persona.save()
                        self.console.print("  [green]✔ Memory saved[/green]")
                    self.running = False
                # "No" = do nothing, return to prompt
            except Exception:
                pass  # If menu fails, just ignore

    def run(self):
        """Main run loop."""
        setup_logging()

        # Show splash screen
        show_splash(self.console)

        # Initialize agent
        self.agent = Agent(self.console)
        if not self.agent.initialize():
            return 1

        # Initialize runner
        self.runner = AgentRunner(self.agent, self.console)

        self.console.print(f"[green]{ICONS['done']} Rocky.Ai is ready![/green]")
        self.console.print()

        # Get input handler
        input_handler = get_input_handler()

        # Main loop
        while self.running:
            try:
                user_input = input_handler.get_input("You: ")

                if user_input is None:
                    self.running = False
                    break

                user_input = user_input.strip()

                if not user_input:
                    continue

                # Handle slash commands
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                # Process message via runner
                self.console.print()
                self.console.print("[bold cyan]Rocky:[/bold cyan]", end=" ")

                self.runner.start(user_input)
                self.runner.wait()

                self.console.print()
                self.console.print()

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Type /quit to exit.[/yellow]")
            except Exception as e:
                logger.error(f"Error: {e}")
                self.console.print(f"[red]Error: {e}[/red]")

        show_goodbye(self.console)
        return 0

    def _handle_command(self, command: str):
        """Handle slash commands."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        commands = {
            "/help": self._cmd_help,
            "/quit": self._cmd_quit,
            "/clear": self._cmd_clear,
            "/save": self._cmd_save,
            "/load": self._cmd_load,
            "/sessions": self._cmd_sessions,
            "/model": self._cmd_model,
            "/tools": self._cmd_tools,
            "/refresh": self._cmd_refresh,
            "/jobs": self._cmd_jobs,
            "/version": self._cmd_version,
        }

        handler = commands.get(cmd)
        if handler:
            handler(args)
        else:
            self.console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
            self.console.print("Type [bold]/help[/bold] for available commands.")

    def _cmd_help(self, args: str):
        """Show help."""
        help_text = """
[bold]Commands:[/bold]

  /help          Show this help
  /quit          Exit Rocky.Ai (or Ctrl+C when idle)
  /clear         Clear conversation history
  /model [name]  Show current model / switch model
  /tools         Manage permissions (list/trust/deny/reset)
  /refresh       Save memory checkpoint
  /jobs          Show background job status
  /save [name]   Save session
  /load <name>   Load a saved session
  /sessions      List saved sessions
  /version       Show version

[dim]Tip: Use /refresh to keep my memory updated[/dim]
"""
        self.console.print(help_text)

    def _cmd_quit(self, args: str):
        """Quit the application."""
        self.running = False

    def _cmd_clear(self, args: str):
        """Clear conversation."""
        if self.agent:
            self.agent.clear_memory()
        self.console.print(f"[green]{ICONS['done']} Conversation cleared.[/green]")

    def _cmd_save(self, args: str):
        """Save session."""
        if not self.agent:
            return

        name = args.strip() if args else None
        saved_name = self.session_manager.save_session(self.agent.get_memory(), name)
        self.console.print(f"[green]{ICONS['done']} Session saved as: {saved_name}[/green]")

    def _cmd_load(self, args: str):
        """Load session."""
        if not self.agent:
            return

        name = args.strip()
        if not name:
            self.console.print("[yellow]Usage: /load <session_name>[/yellow]")
            return

        memory = self.session_manager.load_session(name)
        if memory:
            self.agent.set_memory(memory)
            self.console.print(f"[green]{ICONS['done']} Loaded session: {name}[/green]")
        else:
            self.console.print(f"[red]Session not found: {name}[/red]")

    def _cmd_sessions(self, args: str):
        """List sessions."""
        sessions = self.session_manager.list_sessions()

        if not sessions:
            self.console.print("[dim]No saved sessions.[/dim]")
            return

        self.console.print("[bold]Saved Sessions:[/bold]")
        for s in sessions[:10]:
            self.console.print(f"  {s['name']} ({s['turns']} turns) - {s['created'][:10]}")

    def _cmd_model(self, args: str):
        """Show current model or switch model."""
        if not self.agent:
            return

        args = args.strip()

        if not args:
            # Show current model + list all
            model_name = self.agent.model_manager.get_text_model()
            info = self.agent.engine.get_model_info()

            self.console.print(f"[bold]Current Model:[/bold] {model_name}")
            if info.get("loaded"):
                self.console.print(f"  Context: {info.get('n_ctx', 'N/A')} tokens")
            self.console.print()

            # Also list available models
            from rocky.llm.downloader import format_size
            models = self.agent.model_manager.list_models()
            self.console.print("[bold]Available Models:[/bold]")
            for m in models:
                current = " [green]◀ current[/green]" if m['key'] == model_name else ""
                status = "[green]downloaded[/green]" if m["downloaded"] else "[dim]not downloaded[/dim]"
                self.console.print(
                    f"  {m['key']} — {m['name']} "
                    f"({m['parameters']}, {format_size(m['size_bytes'])}) "
                    f"[{status}]{current}"
                )
        else:
            # Switch model
            self.console.print(f"  Switching to [bold]{args}[/bold]...")
            # Model switching would go here (future implementation)
            self.console.print("  [yellow]Model switching not yet implemented[/yellow]")

    def _cmd_tools(self, args: str):
        """Manage tool permissions."""
        perm_manager = get_permission_manager()
        parts = args.strip().split()

        if not parts or parts[0] == "list":
            status = perm_manager.get_status()
            self.console.print("[bold]Permission State:[/bold]")
            if status["trust_all"]:
                self.console.print("  Mode: [green]Trust-All[/green]")
            else:
                self.console.print("  Mode: Per-tool prompts")
            if status["trusted_tools"]:
                self.console.print(f"  Trusted: {', '.join(status['trusted_tools'])}")
            if status["denied_tools"]:
                self.console.print(f"  Denied: {', '.join(status['denied_tools'])}")

        elif parts[0] == "trust" and len(parts) > 1:
            tool_name = parts[1]
            perm_manager.trust_tool(tool_name)
            self.console.print(f"  [green]✔ Trusted '{tool_name}' for this session[/green]")

        elif parts[0] == "trust-all":
            perm_manager.trust_all()
            self.console.print("  [green]✔ All tools trusted for this session[/green]")
            self.console.print("  [yellow]⚠ Rocky can now run any command without asking[/yellow]")

        elif parts[0] == "deny" and len(parts) > 1:
            tool_name = parts[1]
            perm_manager.deny_tool(tool_name)
            self.console.print(f"  [red]✘ Denied '{tool_name}' for this session[/red]")

        elif parts[0] == "reset":
            perm_manager.reset()
            self.console.print("  [green]✔ Permissions reset to defaults[/green]")

        else:
            self.console.print("Usage: /tools [list|trust <tool>|trust-all|deny <tool>|reset]")

    def _cmd_refresh(self, args: str):
        """Memory checkpoint — save persona and learnings."""
        if self.agent:
            self.agent.persona.save()
            self.console.print("  [green]✔ Memory checkpoint saved[/green]")
            self.console.print("  [dim]Persona and learnings persisted to ~/.rocky/persona/[/dim]")

    def _cmd_jobs(self, args: str):
        """Show background job status."""
        manager = get_job_manager()
        jobs = manager.list_jobs()

        if not jobs:
            self.console.print("  [dim]No background jobs.[/dim]")
            return

        for job in jobs:
            status = "[green]✔ done[/green]" if job.completed else "[cyan]⠧ running[/cyan]"
            self.console.print(f"  Job #{job.id}: {status} — {job.command[:60]}")
            if job.completed and job.exit_code != 0:
                self.console.print(f"    [red]Exit: {job.exit_code}[/red]")

    def _cmd_version(self, args: str):
        """Show version."""
        self.console.print(f"[bold]{__app_name__}[/bold] v{__version__}")


def main():
    """Entry point."""
    cli = RockyCLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
