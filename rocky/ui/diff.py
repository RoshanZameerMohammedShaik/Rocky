"""Diff display for Rocky.Ai."""

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from difflib import unified_diff
from pathlib import Path
from typing import Optional


def show_diff(
    console: Console,
    old_content: str,
    new_content: str,
    filename: str = "file",
    context_lines: int = 3
):
    """Display a unified diff between old and new content."""
    
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = list(unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
        n=context_lines
    ))
    
    if not diff:
        console.print("[dim]No changes[/dim]")
        return
    
    # Build colored diff output
    diff_text = Text()
    
    for line in diff:
        line = line.rstrip('\n')
        if line.startswith('+++') or line.startswith('---'):
            diff_text.append(line + "\n", style="bold")
        elif line.startswith('@@'):
            diff_text.append(line + "\n", style="cyan")
        elif line.startswith('+'):
            diff_text.append(line + "\n", style="green")
        elif line.startswith('-'):
            diff_text.append(line + "\n", style="red")
        else:
            diff_text.append(line + "\n", style="dim")
    
    panel = Panel(
        diff_text,
        title=f"[bold]Changes to {filename}[/bold]",
        border_style="blue",
    )
    console.print(panel)


def show_file_change(
    console: Console,
    path: Path,
    old_content: Optional[str],
    new_content: str,
    operation: str = "modified"
):
    """Show a file change with appropriate formatting."""
    
    filename = path.name
    
    if operation == "created":
        console.print(f"[green]+ Created:[/green] {path}")
        # Show preview of new file
        preview = new_content[:500]
        if len(new_content) > 500:
            preview += "\n..."
        
        # Detect language for syntax highlighting
        suffix = path.suffix.lower()
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sh": "bash",
            ".bash": "bash",
        }
        lang = lang_map.get(suffix, "text")
        
        syntax = Syntax(preview, lang, theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"[bold]{filename}[/bold]", border_style="green"))
        
    elif operation == "deleted":
        console.print(f"[red]- Deleted:[/red] {path}")
        
    elif operation == "modified" and old_content is not None:
        console.print(f"[yellow]~ Modified:[/yellow] {path}")
        show_diff(console, old_content, new_content, str(path))
    
    else:
        console.print(f"[blue]? {operation}:[/blue] {path}")
