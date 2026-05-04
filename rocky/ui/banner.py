"""Rocky.Ai startup banner — braille unicode art logo."""
from rich.console import Console
from rich.text import Text


ROCKY_BANNER = """
⠀⠀⢀⣴⣶⣶⣦⡀⠀⠀⠀⢀⣴⣶⣦⣄⡀⠀⠀⠀⢀⣴⣶⣶⣦⡀⠀⠀⢀⣶⡄⠀⠀⠀⠀⢀⣶⡄⠀⠀⠀⢀⣶⣶⣶⣶⣶⣶⣦⡀⠀
⠀⠀⣿⡟⠁⠀⠙⣿⡆⠀⣴⡿⠋⠀⠈⠻⣷⡀⠀⠀⣿⡟⠁⠀⠙⣿⡆⠀⢸⣿⡇⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⢸⣿⡏⠀⠀⠀⠻⣿⡇⠀
⠀⠀⣿⡇⠀⠀⠀⣿⣇⣾⠟⠀⠀⠀⠀⣠⣿⠇⠀⠀⣿⡇⠀⠀⠀⣿⡇⠀⢸⣿⡇⠀⠀⣀⠀⢸⣿⡇⠀⠀⠀⢸⣿⡇⠀⠀⠀⢀⣿⡇⠀
⠀⠀⣿⡇⠀⠀⠀⣿⡿⠋⠀⠀⠀⣠⣾⡿⠁⠀⠀⠀⣿⡇⠀⠀⠀⣿⡇⠀⢸⣿⡇⠀⣼⡿⠀⢸⣿⡇⠀⠀⠀⢸⣿⣷⣶⣶⣶⡿⠋⠀⠀
⠀⠀⣿⡇⠀⠀⠀⠋⠀⠀⠀⠀⣴⡿⠋⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⣿⡇⠀⢸⣿⡇⣾⠟⠀⠀⢸⣿⡇⠀⠀⠀⢸⣿⡏⠉⠻⣷⡀⠀⠀⠀
⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠹⣷⣄⠀⠀⠀⠀⠀⣿⡇⠀⠀⠀⣿⡇⠀⢸⣿⡿⣿⣄⠀⠀⢸⣿⡇⠀⠀⠀⢸⣿⡇⠀⠀⠹⣷⡄⠀⠀
⠀⠀⣿⣧⡀⠀⣀⣼⡇⠀⠀⠀⠀⠘⢿⣦⡀⠀⠀⠀⣿⣧⡀⠀⣀⣿⠇⠀⢸⣿⡇⠹⣿⣦⠀⢸⣿⣧⣀⣀⡀⢸⣿⡇⠀⠀⠀⢻⣿⡄⠀
⠀⠀⠻⢿⣿⣿⡿⠟⠁⠀⠀⠀⠀⠀⠈⠻⣿⣦⠀⠀⠻⢿⣿⣿⡿⠟⠀⠀⢸⣿⡇⠀⠙⠿⠀⠈⠻⠿⠿⠿⠃⢸⣿⡇⠀⠀⠀⠀⢿⣷⠀
"""


def show_banner(console: Console, version: str = "1.0") -> None:
    """Display the Rocky.Ai startup banner."""
    banner_text = Text(ROCKY_BANNER, style="bold cyan")
    console.print(banner_text, justify="center")

    tagline = Text(f"Rocky.Ai v{version} — Your local AI assistant", style="dim white")
    console.print(tagline, justify="center")
    console.print()
