"""CLI entry point for Rocky.AI."""

import sys
import signal
from typing import Optional
from rich.console import Console

from rocky import __version__, __app_name__
from rocky.agent import Agent
from rocky.session import SessionManager
from rocky.ui.splash import show_splash, show_goodbye
from rocky.ui.input import get_input_handler
from rocky.ui.permissions import get_permission_manager
from rocky.ui.animations import ICONS
from rocky.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


class RockyCLI:
    """Main CLI application."""

    def __init__(self):
        self.console = Console()
        self.agent: Optional[Agent] = None
        self.session_manager = SessionManager()
        self.running = True

        # Setup interrupt handler
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, sig, frame):
        """Handle Ctrl+C gracefully."""
        self.console.print("\n[yellow]Interrupted. Type /quit to exit.[/yellow]")

    def run(self):
        """Main run loop."""
        setup_logging()

        # Show splash screen
        show_splash(self.console)

        # Initialize agent
        self.agent = Agent(self.console)
        if not self.agent.initialize():
            return 1

        self.console.print(f"[green]{ICONS['success']} Rocky.AI is ready![/green]")
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

                # Process message
                self.console.print()
                self.console.print("[bold cyan]Rocky:[/bold cyan]", end=" ")

                for chunk in self.agent.process_message(user_input):
                    self.console.print(chunk, end="")

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
            "/exit": self._cmd_quit,
            "/clear": self._cmd_clear,
            "/save": self._cmd_save,
            "/load": self._cmd_load,
            "/sessions": self._cmd_sessions,
            "/model": self._cmd_model,
            "/models": self._cmd_models,
            "/trust": self._cmd_trust,
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
[bold]Available Commands:[/bold]

  /help          Show this help message
  /quit, /exit   Exit Rocky.AI
  /clear         Clear conversation history
  /save [name]   Save current session
  /load <name>   Load a saved session
  /sessions      List saved sessions
  /model         Show current model info
  /models        List available models
  /trust         Enable trust mode (skip permission prompts)
  /version       Show version info
"""
        self.console.print(help_text)

    def _cmd_quit(self, args: str):
        """Quit the application."""
        self.running = False

    def _cmd_clear(self, args: str):
        """Clear conversation."""
        if self.agent:
            self.agent.clear_memory()
        self.console.print(f"[green]{ICONS['success']} Conversation cleared.[/green]")

    def _cmd_save(self, args: str):
        """Save session."""
        if not self.agent:
            return

        name = args.strip() if args else None
        saved_name = self.session_manager.save_session(self.agent.get_memory(), name)
        self.console.print(f"[green]{ICONS['success']} Session saved as: {saved_name}[/green]")

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
            self.console.print(f"[green]{ICONS['success']} Loaded session: {name}[/green]")
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
        """Show current model info."""
        if not self.agent:
            return

        model_name = self.agent.model_manager.get_text_model()
        info = self.agent.engine.get_model_info()

        self.console.print(f"[bold]Current Model:[/bold] {model_name}")
        if info.get("loaded"):
            self.console.print(f"  Context: {info.get('n_ctx', 'N/A')} tokens")
            self.console.print(f"  Path: [dim]{info.get('path', 'N/A')}[/dim]")

    def _cmd_models(self, args: str):
        """List available models."""
        if not self.agent:
            return

        from rocky.llm.downloader import format_size

        models = self.agent.model_manager.list_models()

        self.console.print("[bold]Available Models:[/bold]")
        self.console.print()
        for m in models:
            status = "[green]downloaded[/green]" if m["downloaded"] else "[dim]not downloaded[/dim]"
            self.console.print(
                f"  [bold]{m['key']}[/bold] - {m['name']} "
                f"({m['parameters']}, {m['quantization']}, "
                f"{format_size(m['size_bytes'])}) [{status}]"
            )
            self.console.print(f"    {m['description']}")
            self.console.print()

    def _cmd_trust(self, args: str):
        """Enable trust mode."""
        perm_manager = get_permission_manager()
        perm_manager.enable_trust()
        self.console.print(f"[green]{ICONS['success']} Trust mode enabled for this session.[/green]")
        self.console.print("[dim]All commands will run without permission prompts.[/dim]")

    def _cmd_version(self, args: str):
        """Show version."""
        self.console.print(f"[bold]{__app_name__}[/bold] v{__version__}")


def main():
    """Entry point."""
    cli = RockyCLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
