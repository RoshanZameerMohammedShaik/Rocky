"""Animations and spinners for Rocky.AI."""

import time
import threading
from typing import Optional, Callable
from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live
from rich.text import Text
from contextlib import contextmanager


class AnimationState:
    """Thread-safe animation state."""
    def __init__(self):
        self._message = ""
        self._steps: list[str] = []
        self._lock = threading.Lock()
        self._running = False
    
    @property
    def message(self) -> str:
        with self._lock:
            return self._message
    
    @message.setter
    def message(self, value: str):
        with self._lock:
            self._message = value
    
    def add_step(self, step: str):
        with self._lock:
            self._steps.append(step)
    
    def get_steps(self) -> list[str]:
        with self._lock:
            return self._steps.copy()
    
    def clear_steps(self):
        with self._lock:
            self._steps.clear()


# Animation icons for different states
ICONS = {
    "thinking": "🧠",
    "reading": "📖",
    "writing": "✏️",
    "analyzing": "🔍",
    "searching": "🌐",
    "transcribing": "🎧",
    "learning": "📚",
    "processing": "⚙️",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
}


@contextmanager
def thinking_animation(console: Console, message: str = "Thinking"):
    """Context manager for thinking animation."""
    state = AnimationState()
    state.message = message
    
    def render() -> Text:
        text = Text()
        text.append(f"{ICONS['thinking']} ", style="bold")
        text.append(state.message, style="cyan")
        text.append("...", style="dim")
        
        steps = state.get_steps()
        if steps:
            text.append("\n")
            for step in steps[-5:]:  # Show last 5 steps
                text.append(f"   ├─ {step}\n", style="dim")
        
        return text
    
    with Live(render(), console=console, refresh_per_second=10, transient=True) as live:
        def update():
            while state._running:
                live.update(render())
                time.sleep(0.1)
        
        state._running = True
        thread = threading.Thread(target=update, daemon=True)
        thread.start()
        
        try:
            yield state
        finally:
            state._running = False
            thread.join(timeout=0.5)


@contextmanager  
def status_animation(console: Console, icon: str, message: str):
    """Context manager for status animation with spinner."""
    spinner = Spinner("dots", text=f" {message}...")
    
    with Live(spinner, console=console, refresh_per_second=10, transient=True):
        yield


def show_status(console: Console, icon: str, message: str, style: str = ""):
    """Show a status message with icon."""
    icon_char = ICONS.get(icon, "•")
    if style:
        console.print(f"{icon_char} [{style}]{message}[/{style}]")
    else:
        console.print(f"{icon_char} {message}")


def show_thinking_steps(console: Console, steps: list[str]):
    """Display thinking steps."""
    console.print(f"{ICONS['thinking']} [bold cyan]Thinking...[/bold cyan]")
    for i, step in enumerate(steps):
        prefix = "└─" if i == len(steps) - 1 else "├─"
        console.print(f"   {prefix} [dim]{step}[/dim]")
