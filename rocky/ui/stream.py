"""Rich Live markdown streaming renderer for Rocky.Ai.

Streams LLM response tokens through Rich Markdown for progressive rendering.
Tables, code blocks, and lists format as they stream in.
"""

from typing import Generator
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.text import Text


class StreamRenderer:
    """Renders streaming LLM output as formatted markdown."""

    def __init__(self, console: Console):
        self.console = console
        self._buffer = ""

    def stream(self, chunks: Generator[str, None, None]) -> str:
        """Stream chunks and render as markdown progressively.

        Returns the full accumulated response text.
        """
        self._buffer = ""

        with Live(
            Text(""),
            console=self.console,
            refresh_per_second=10,
            vertical_overflow="visible",
        ) as live:
            for chunk in chunks:
                self._buffer += chunk
                # Render current buffer as markdown
                try:
                    live.update(Markdown(self._buffer))
                except Exception:
                    # Fallback: render as plain text if markdown parsing fails mid-stream
                    live.update(Text(self._buffer))

        return self._buffer

    def show_thinking(self) -> Live:
        """Show thinking spinner. Caller manages the context."""
        spinner = Spinner("dots", text="Thinking...", style="cyan")
        return Live(spinner, console=self.console, refresh_per_second=10)
