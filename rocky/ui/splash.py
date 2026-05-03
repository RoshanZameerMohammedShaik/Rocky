"""ASCII splash screen for Rocky.AI."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rocky import __version__
from rocky.utils.network import is_online

ROCKY_ASCII = r"""
██████╗  ██████╗  ██████╗██╗  ██╗██╗   ██╗     █████╗ ██╗
██╔══██╗██╔═══██╗██╔════╝██║ ██╔╝╚██╗ ██╔╝    ██╔══██╗██║
██████╔╝██║   ██║██║     █████╔╝  ╚████╔╝     ███████║██║
██╔══██╗██║   ██║██║     ██╔═██╗   ╚██╔╝      ██╔══██║██║
██║  ██║╚██████╔╝╚██████╗██║  ██╗   ██║    ██╗██║  ██║██║
╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝   ╚═╝    ╚═╝╚═╝  ╚═╝╚═╝
"""

ROCKY_ASCII_SMALL = r"""
 ____            _           _    ___ 
|  _ \ ___   ___| | ___   _ / \  |_ _|
| |_) / _ \ / __| |/ / | | / _ \  | | 
|  _ < (_) | (__|   <| |_| / ___ \ | | 
|_| \_\___/ \___|_|\_\\__, /_/   \_\___|
                      |___/            
"""


def show_splash(console: Console, compact: bool = False):
    """Display the Rocky.AI splash screen."""
    ascii_art = ROCKY_ASCII_SMALL if compact else ROCKY_ASCII
    
    # Build status line
    online = is_online()
    status = "[green]Online[/green]" if online else "[yellow]Offline[/yellow]"
    
    # Create splash content
    splash_text = Text()
    splash_text.append(ascii_art, style="bold cyan")
    
    console.print(splash_text)
    console.print()
    console.print(f"  [bold]Your local AI assistant[/bold]  •  v{__version__}")
    console.print(f"  Running {status}  •  Type [bold]/help[/bold] for commands")
    
    if not online:
        console.print()
        console.print("  [dim]💡 Tip: Connect to internet for real-time web search[/dim]")
    
    console.print()
    console.print("─" * 60)
    console.print()


def show_goodbye(console: Console):
    """Display goodbye message."""
    console.print()
    console.print("[bold cyan]👋 Goodbye! See you next time.[/bold cyan]")
    console.print()
