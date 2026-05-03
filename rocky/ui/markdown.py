"""Markdown rendering for Rocky.AI."""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from typing import Optional
import re


def render_markdown(console: Console, content: str, title: Optional[str] = None):
    """Render markdown content to the console."""
    md = Markdown(content)
    
    if title:
        console.print(Panel(md, title=title, border_style="blue"))
    else:
        console.print(md)


def render_code_block(
    console: Console, 
    code: str, 
    language: str = "text",
    title: Optional[str] = None,
    line_numbers: bool = True
):
    """Render a code block with syntax highlighting."""
    syntax = Syntax(
        code, 
        language, 
        theme="monokai", 
        line_numbers=line_numbers,
        word_wrap=True
    )
    
    if title:
        console.print(Panel(syntax, title=title, border_style="blue"))
    else:
        console.print(syntax)


def extract_code_blocks(content: str) -> list[tuple[str, str]]:
    """Extract code blocks from markdown content.
    
    Returns list of (language, code) tuples.
    """
    pattern = r"```(\w*)\n(.*?)```"
    matches = re.findall(pattern, content, re.DOTALL)
    return [(lang or "text", code.strip()) for lang, code in matches]


def render_response(console: Console, content: str):
    """Render an AI response, handling code blocks specially."""
    # Split content by code blocks
    parts = re.split(r"(```\w*\n.*?```)", content, flags=re.DOTALL)
    
    for part in parts:
        if part.startswith("```"):
            # Extract language and code
            match = re.match(r"```(\w*)\n(.*?)```", part, re.DOTALL)
            if match:
                lang = match.group(1) or "text"
                code = match.group(2).strip()
                render_code_block(console, code, lang)
        else:
            # Regular markdown
            if part.strip():
                render_markdown(console, part.strip())
