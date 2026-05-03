"""Splash screen for Rocky.AI."""

from rich.console import Console
from rocky import __version__
from rocky.utils.network import is_online
from rocky.ui.animations import show_startup


def show_splash(console: Console, compact: bool = False):
    """Display the Rocky.AI splash screen with animation."""
    show_startup(console, __version__)

    online = is_online()
    status = "[green]Online[/green]" if online else "[yellow]Offline[/yellow]"
    console.print(f"  Running {status}  [dim]\u2022[/dim]  Type [bold]/help[/bold] for commands")

    if not online:
        console.print()
        console.print("  [dim]Connect to internet for web search[/dim]")

    console.print()
    console.print("[dim]" + "\u2500" * 60 + "[/dim]")
    console.print()


def show_goodbye(console: Console):
    """Display goodbye message."""
    console.print()
    console.print("  [bold cyan]Goodbye! See you next time.[/bold cyan]")
    console.print()
