"""Progress bars for Rocky.Ai."""

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    DownloadColumn,
    TransferSpeedColumn,
)
from rich.panel import Panel
from contextlib import contextmanager
from typing import Optional


def create_download_progress() -> Progress:
    """Create a progress bar for downloads."""
    return Progress(
        SpinnerColumn("dots", style="cyan"),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=40, style="dim", complete_style="cyan", pulse_style="bright_cyan", finished_style="green"),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    )


def create_install_progress() -> Progress:
    """Create a progress bar for installation steps."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    )


@contextmanager
def overall_progress(console: Console, total_steps: int, title: str = "Overall Progress"):
    """Context manager for overall progress with nested task progress."""

    overall = Progress(
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("{task.fields[status]}"),
    )

    task_progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
    )

    class ProgressManager:
        def __init__(self):
            self.overall_task = overall.add_task(
                title,
                total=total_steps,
                status=f"0 of {total_steps}"
            )
            self.current_task: Optional[int] = None
            self.completed = 0

        def start_task(self, description: str, total: float = 100):
            """Start a new task."""
            if self.current_task is not None:
                task_progress.remove_task(self.current_task)
            self.current_task = task_progress.add_task(description, total=total)

        def update_task(self, advance: float = 0, completed: Optional[float] = None, description: Optional[str] = None):
            """Update current task progress."""
            if self.current_task is not None:
                kwargs = {}
                if completed is not None:
                    kwargs["completed"] = completed
                if description is not None:
                    kwargs["description"] = description
                if advance:
                    task_progress.advance(self.current_task, advance)
                if kwargs:
                    task_progress.update(self.current_task, **kwargs)

        def complete_task(self):
            """Mark current task as complete and advance overall."""
            if self.current_task is not None:
                task_progress.remove_task(self.current_task)
                self.current_task = None
            self.completed += 1
            overall.update(
                self.overall_task,
                advance=1,
                status=f"{self.completed} of {total_steps}"
            )

        def set_task_description(self, description: str):
            """Update task description (e.g., 'Downloading' -> 'Installing')."""
            if self.current_task is not None:
                task_progress.update(self.current_task, description=description)

    from rich.table import Table
    from rich.live import Live

    def make_table():
        table = Table.grid(padding=1)
        table.add_row(Panel(overall, title="[bold]Installation Progress", border_style="blue"))
        if task_progress.tasks:
            table.add_row(task_progress)
        return table

    manager = ProgressManager()

    with Live(make_table(), console=console, refresh_per_second=10) as live:
        def refresh():
            live.update(make_table())

        manager.refresh = refresh
        yield manager


class SimpleProgress:
    """Simple progress indicator for single operations."""

    def __init__(self, console: Console, description: str, total: float = 100):
        self.console = console
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
        )
        self.task = self.progress.add_task(description, total=total)
        self._live = None

    def __enter__(self):
        from rich.live import Live
        self._live = Live(self.progress, console=self.console, refresh_per_second=10)
        self._live.__enter__()
        return self

    def __exit__(self, *args):
        if self._live:
            self._live.__exit__(*args)

    def update(self, advance: float = 0, completed: Optional[float] = None, description: Optional[str] = None):
        kwargs = {}
        if completed is not None:
            kwargs["completed"] = completed
        if description is not None:
            kwargs["description"] = description
        if advance:
            self.progress.advance(self.task, advance)
        if kwargs:
            self.progress.update(self.task, **kwargs)
