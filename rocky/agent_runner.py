"""Threading wrapper for Rocky.Ai agent.

Runs the agent loop in a worker thread while the main thread
handles user input (/btw, Ctrl+C).
"""

import threading
from queue import Queue
from typing import Optional
from rich.console import Console
from rocky.agent import Agent


class AgentRunner:
    """Manages agent execution in a separate thread."""

    def __init__(self, agent: Agent, console: Console):
        self.agent = agent
        self.console = console
        self.btw_queue: Queue = Queue()
        self.stop_event = threading.Event()
        self.is_working = False
        self._thread: Optional[threading.Thread] = None

    def inject_btw(self, message: str):
        """Inject a /btw mid-task instruction."""
        self.agent.btw_queue.put(message)
        self.console.print("  [cyan]⠧ Noted — adjusting...[/cyan]")

    def request_stop(self):
        """Request the agent loop to stop."""
        self.stop_event.set()

    def start(self, user_input: str):
        """Start processing a user message in the worker thread."""
        self.is_working = True
        self.stop_event.clear()

        self._thread = threading.Thread(
            target=self._worker, args=(user_input,), daemon=True
        )
        self._thread.start()

    def wait(self):
        """Wait for the agent to finish."""
        if self._thread:
            self._thread.join()
        self.is_working = False

    def _worker(self, user_input: str):
        """Worker thread — runs the agent loop."""
        try:
            for chunk in self.agent.process_message(user_input):
                if self.stop_event.is_set():
                    self.console.print("\n[yellow]⚠ Stopped by user.[/yellow]")
                    break
                # Output is handled by agent internally via console
                # But text chunks need to be printed
                if chunk:
                    self.console.print(chunk, end="")
        except Exception as e:
            self.console.print(f"\n[red]✘ Error: {e}[/red]")
        finally:
            self.is_working = False
