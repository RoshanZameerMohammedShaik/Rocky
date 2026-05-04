"""Arrow-key menu selector for Rocky.Ai.

Reusable interactive menu with blue ▶ selector.
Used for: quit confirmation, permission prompts, sensitive data prompt.
"""

import sys
from typing import Optional
from rich.console import Console
from rich.text import Text
from rich.live import Live


SELECTOR = "▶"
SELECTOR_STYLE = "bold blue"


class ArrowMenu:
    """Interactive arrow-key menu with blue ▶ selector."""

    def __init__(
        self,
        title: str,
        options: list[str],
        default: int = 0,
        console: Optional[Console] = None,
    ):
        self.title = title
        self.options = options
        self.selected = default
        self.console = console or Console()

    def move_down(self):
        self.selected = (self.selected + 1) % len(self.options)

    def move_up(self):
        self.selected = (self.selected - 1) % len(self.options)

    def get_selected(self) -> str:
        return self.options[self.selected]

    def render(self) -> Text:
        """Render the menu as Rich Text."""
        output = Text()
        output.append(f"  {self.title}\n\n", style="bold")

        for i, option in enumerate(self.options):
            if i == self.selected:
                output.append(f"    {SELECTOR} ", style=SELECTOR_STYLE)
                output.append(f"{option}\n", style="bold white")
            else:
                output.append(f"      {option}\n", style="dim")

        return output

    def run(self) -> str:
        """Run the interactive menu. Returns selected option string."""
        try:
            import tty
            import termios

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)

            try:
                tty.setraw(fd)

                with Live(
                    self.render(),
                    console=self.console,
                    refresh_per_second=30,
                    transient=True,
                ) as live:
                    while True:
                        ch = sys.stdin.read(1)

                        if ch == "\r" or ch == "\n":
                            break
                        elif ch == "\x1b":
                            seq = sys.stdin.read(2)
                            if seq == "[A":  # Up arrow
                                self.move_up()
                            elif seq == "[B":  # Down arrow
                                self.move_down()

                        live.update(self.render())

            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        except (ImportError, termios.error, ValueError):
            # Fallback for non-Unix or piped input
            self.console.print(self.render())
            self.console.print()
            choices = [str(i + 1) for i in range(len(self.options))]
            from rich.prompt import Prompt
            choice = Prompt.ask(
                "Select",
                choices=choices,
                default=str(self.selected + 1),
            )
            self.selected = int(choice) - 1

        # Print final state
        selected_text = Text()
        selected_text.append(f"    {SELECTOR} ", style=SELECTOR_STYLE)
        selected_text.append(self.get_selected(), style="bold white")
        self.console.print(selected_text)

        return self.get_selected()
