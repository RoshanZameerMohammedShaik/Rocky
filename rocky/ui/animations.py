"""Terminal animations for Rocky.Ai.

Visual feedback system:
- Rectangular loading dots for thinking/waiting
- Green +lines for file writes
- Red -lines for file deletes
- Shimmer sweep for file reads
- Startup ASCII animation
"""

import time
import threading
import sys
from typing import Optional
from rich.console import Console
from rich.text import Text
from contextlib import contextmanager


# Status icons
ICONS = {
    "thinking": "\u2588\u2588",
    "reading": "\u25B6",
    "writing": "\u270F",
    "analyzing": "\u2318",
    "searching": "\u2315",
    "transcribing": "\u266B",
    "learning": "\u2261",
    "processing": "\u2699",
    "success": "\u2714",
    "error": "\u2718",
    "warning": "\u26A0",
}


# ===== RECTANGULAR LOADING DOTS =====
# 8 positions in a rectangle: top-left, top-mid-left, top-mid-right, top-right,
# bottom-right, bottom-mid-right, bottom-mid-left, bottom-left
RECT_DOTS = [
    (0, 0), (0, 1), (0, 2), (0, 3),
    (1, 3), (1, 2), (1, 1), (1, 0),
]

RECT_DOT_CHARS = "\u2022"  # bullet
RECT_DOT_ACTIVE = "\u25CF"  # filled circle


class RectangularLoader:
    """Fast rectangular cycling dots animation."""

    def __init__(self, console: Console, message: str = "Thinking"):
        self.console = console
        self.message = message
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._position = 0

    def _render_frame(self) -> str:
        """Render one frame of the rectangular dots."""
        # 2 rows x 4 cols grid
        grid = [["  "] * 4 for _ in range(2)]

        trail_length = 3
        for offset in range(trail_length):
            idx = (self._position - offset) % 8
            row, col = RECT_DOTS[idx]
            if offset == 0:
                grid[row][col] = "\033[96m\u25CF\033[0m"  # cyan active
            elif offset == 1:
                grid[row][col] = "\033[36m\u25CB\033[0m"  # dim cyan
            else:
                grid[row][col] = "\033[90m\u00B7\033[0m"  # gray dot

        # Fill remaining with dim dots
        for r in range(2):
            for c in range(4):
                if grid[r][c] == "  ":
                    grid[r][c] = "\033[90m\u00B7\033[0m"

        top = " ".join(grid[0])
        bot = " ".join(grid[1])
        return f"  {top}\n  {bot}"

    def _animate(self):
        """Animation loop running in background thread."""
        while self._running:
            frame = self._render_frame()
            # Move cursor up 2 lines, clear, redraw
            sys.stdout.write(f"\033[2A\033[2K{frame}\n\033[2K")
            sys.stdout.flush()
            self._position = (self._position + 1) % 8
            time.sleep(0.15)  # Fast cycling

    def start(self):
        """Start the loading animation."""
        self._running = True
        # Print initial placeholder lines
        msg_line = f"\033[96m  {self.message}...\033[0m"
        sys.stdout.write(f"\n{msg_line}\n\n\n")
        sys.stdout.flush()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the loading animation."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.3)
        # Clear the animation lines
        sys.stdout.write("\033[3A\033[J")
        sys.stdout.flush()


@contextmanager
def loading_animation(console: Console, message: str = "Thinking"):
    """Context manager for the rectangular loading dots."""
    loader = RectangularLoader(console, message)
    loader.start()
    try:
        yield loader
    finally:
        loader.stop()


# ===== FILE DIFF DISPLAY =====

def show_write_lines(console: Console, filepath: str, content: str):
    """Show written lines with green + prefix and green background."""
    console.print()
    console.print(f"  \033[1m\u270F  Writing: {filepath}\033[0m")
    console.print()

    lines = content.splitlines()
    for line in lines:
        # Green background with + prefix
        styled = Text(f"  + {line}")
        styled.stylize("on #0d2818")
        styled.stylize("green")
        console.print(styled)

    console.print()


def show_delete_lines(console: Console, filepath: str, content: str):
    """Show deleted lines with red - prefix and red background."""
    console.print()
    console.print(f"  \033[1m\u2718  Deleting from: {filepath}\033[0m")
    console.print()

    lines = content.splitlines()
    for line in lines:
        # Red background with - prefix
        styled = Text(f"  - {line}")
        styled.stylize("on #2d0a0a")
        styled.stylize("red")
        console.print(styled)

    console.print()


def show_edit_diff(console: Console, filepath: str, old_lines: str, new_lines: str):
    """Show edit diff with red deletions and green additions."""
    console.print()
    console.print(f"  \033[1m\u270F  Editing: {filepath}\033[0m")
    console.print()

    # Show removed lines
    if old_lines:
        for line in old_lines.splitlines():
            styled = Text(f"  - {line}")
            styled.stylize("on #2d0a0a")
            styled.stylize("red")
            console.print(styled)

    # Show added lines
    if new_lines:
        for line in new_lines.splitlines():
            styled = Text(f"  + {line}")
            styled.stylize("on #0d2818")
            styled.stylize("green")
            console.print(styled)

    console.print()


# ===== FILE READ SHIMMER =====

def show_read_shimmer(console: Console, filepath: str, content: str):
    """Show file read with shimmer animation (like slide-to-unlock).

    A white highlight sweeps across semi-transparent text.
    """
    console.print()
    console.print(f"  \033[1m\u25B6  Reading: {filepath}\033[0m")
    console.print()

    lines = content.splitlines()[:20]  # Cap at 20 lines for display

    # First show lines dimly
    line_count = len(lines)
    display_lines = []
    for line in lines:
        display_lines.append(f"    {line}")

    # Print dim version first
    for dl in display_lines:
        console.print(f"[dim]{dl}[/dim]")

    # Shimmer sweep animation (5 frames sweeping left to right)
    frames = 6
    for frame in range(frames):
        # Move cursor up
        sys.stdout.write(f"\033[{line_count}A")
        sweep_pos = frame / (frames - 1)  # 0.0 to 1.0

        for i, line in enumerate(display_lines):
            # Calculate brightness based on position
            line_progress = i / max(line_count - 1, 1)
            distance = abs(sweep_pos - line_progress)

            if distance < 0.2:
                # Bright white (in the sweep zone)
                sys.stdout.write(f"\033[2K\033[97m{line}\033[0m\n")
            elif distance < 0.4:
                # Medium brightness
                sys.stdout.write(f"\033[2K\033[37m{line}\033[0m\n")
            else:
                # Dim
                sys.stdout.write(f"\033[2K\033[90m{line}\033[0m\n")

        sys.stdout.flush()
        time.sleep(0.12)

    # Final state: normal brightness
    sys.stdout.write(f"\033[{line_count}A")
    for line in display_lines:
        sys.stdout.write(f"\033[2K\033[0m{line}\n")
    sys.stdout.flush()

    if len(content.splitlines()) > 20:
        console.print(f"    [dim]... ({len(content.splitlines()) - 20} more lines)[/dim]")
    console.print()


# ===== STARTUP ANIMATION =====

ROCKY_LOGO = """
 ____            _            _    ___
|  _ \\ ___   ___| | ___   _  / \\  |_ _|
| |_) / _ \\ / __| |/ / | | |/ _ \\  | |
|  _ < (_) | (__|   <| |_| / ___ \\ | |
|_| \\_\\___/ \\___|_|\\_\\\\__, /_/   \\_\\___|
                      |___/
"""


def show_startup(console: Console, version: str):
    """Show startup animation with Rocky logo."""
    # Animate logo appearing line by line
    logo_lines = ROCKY_LOGO.strip().splitlines()

    for i, line in enumerate(logo_lines):
        console.print(f"[bold cyan]{line}[/bold cyan]")
        time.sleep(0.05)

    console.print()
    console.print(f"  [bold]Your local AI assistant[/bold]  [dim]\u2022[/dim]  v{version}")
    console.print()


def show_status(console: Console, icon: str, message: str, style: str = ""):
    """Show a status message with icon."""
    icon_char = ICONS.get(icon, "\u2022")
    if style:
        console.print(f"  {icon_char} [{style}]{message}[/{style}]")
    else:
        console.print(f"  {icon_char} {message}")
