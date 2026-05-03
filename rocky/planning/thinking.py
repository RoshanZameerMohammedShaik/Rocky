"""Thinking/reasoning display for Rocky.AI."""

from dataclasses import dataclass, field
from typing import Optional
from rich.console import Console
from rich.tree import Tree
from rich.live import Live


@dataclass
class ThinkingStep:
    """A step in the thinking process."""
    description: str
    status: str = "pending"  # pending, running, done, error
    result: Optional[str] = None


class ThinkingChain:
    """Manages and displays thinking steps."""
    
    def __init__(self, console: Console):
        self.console = console
        self.steps: list[ThinkingStep] = []
        self._live: Optional[Live] = None
    
    def add_step(self, description: str) -> int:
        """Add a thinking step. Returns step index."""
        self.steps.append(ThinkingStep(description=description))
        return len(self.steps) - 1
    
    def update_step(self, index: int, status: str, result: Optional[str] = None):
        """Update a step's status."""
        if 0 <= index < len(self.steps):
            self.steps[index].status = status
            if result:
                self.steps[index].result = result
    
    def render(self) -> Tree:
        """Render thinking steps as a tree."""
        tree = Tree("🧠 [bold cyan]Thinking...[/bold cyan]")
        
        status_icons = {
            "pending": "○",
            "running": "◐",
            "done": "●",
            "error": "✗",
        }
        
        status_styles = {
            "pending": "dim",
            "running": "yellow",
            "done": "green",
            "error": "red",
        }
        
        for step in self.steps:
            icon = status_icons.get(step.status, "○")
            style = status_styles.get(step.status, "")
            
            text = f"{icon} [{style}]{step.description}[/{style}]"
            if step.result:
                text += f" → [dim]{step.result[:50]}[/dim]"
            
            tree.add(text)
        
        return tree
    
    def display(self):
        """Display current thinking state."""
        self.console.print(self.render())
    
    def clear(self):
        """Clear all steps."""
        self.steps.clear()


def show_thinking(console: Console, steps: list[str]):
    """Simple display of thinking steps."""
    console.print("🧠 [bold cyan]Thinking...[/bold cyan]")
    for i, step in enumerate(steps):
        prefix = "└─" if i == len(steps) - 1 else "├─"
        console.print(f"   {prefix} [dim]{step}[/dim]")
