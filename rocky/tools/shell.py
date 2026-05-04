"""Shell command execution tool for Rocky.Ai."""

import subprocess
import threading
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from rocky.tools.base import Tool, ToolResult, ToolParameter
from rocky.utils.platform import get_shell_command
from rocky.utils.validators import get_danger_reason
from rocky.ui.permissions import get_permission_manager, PermissionDecision
from rich.console import Console


@dataclass
class BackgroundJob:
    id: int
    command: str
    started: datetime = field(default_factory=datetime.now)
    completed: bool = False
    output: str = ""
    error: str = ""
    exit_code: Optional[int] = None


class BackgroundJobManager:
    """Manages background shell jobs."""

    def __init__(self):
        self._jobs: dict[int, BackgroundJob] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def start_job(self, command: str, working_dir: Optional[str] = None, timeout: int = 300) -> int:
        with self._lock:
            job_id = self._next_id
            self._next_id += 1

            job = BackgroundJob(id=job_id, command=command)
            self._jobs[job_id] = job

        thread = threading.Thread(
            target=self._run_job, args=(job, command, working_dir, timeout), daemon=True
        )
        thread.start()
        return job_id

    def _run_job(self, job: BackgroundJob, command: str, working_dir: Optional[str], timeout: int):
        try:
            # Use the existing shell command helper
            shell_cmd = get_shell_command(command)
            result = subprocess.run(
                shell_cmd, capture_output=True, text=True,
                timeout=timeout, cwd=working_dir
            )
            with self._lock:
                job.output = result.stdout
                job.error = result.stderr
                job.exit_code = result.returncode
                job.completed = True
        except subprocess.TimeoutExpired:
            with self._lock:
                job.error = f"Timed out after {timeout}s"
                job.completed = True
                job.exit_code = -1
        except Exception as e:
            with self._lock:
                job.error = str(e)
                job.completed = True
                job.exit_code = -1

    def get_job(self, job_id: int) -> Optional[BackgroundJob]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[BackgroundJob]:
        return list(self._jobs.values())


_job_manager: Optional[BackgroundJobManager] = None


def get_job_manager() -> BackgroundJobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = BackgroundJobManager()
    return _job_manager


class RunCommandTool(Tool):
    """Execute shell commands."""

    def __init__(self, console: Optional[Console] = None):
        super().__init__(
            name="run_command",
            description="Execute a shell command (bash on Linux/macOS, PowerShell on Windows)",
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="The command to execute",
                    required=True
                ),
                ToolParameter(
                    name="working_dir",
                    type="string",
                    description="Working directory for the command",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout in seconds",
                    required=False,
                    default=60
                ),
                ToolParameter(
                    name="run_in_background",
                    type="boolean",
                    description="Run command in background, returns job ID immediately",
                    required=False,
                    default=False
                ),
            ]
        )
        self.console = console or Console()

    def execute(
        self,
        command: str,
        working_dir: Optional[str] = None,
        timeout: int = 60,
        run_in_background: bool = False
    ) -> ToolResult:
        # Check for dangerous commands
        danger_reason = get_danger_reason(command)
        perm_manager = get_permission_manager()

        # Check if command is blocked
        if perm_manager.is_blocked_command(command):
            block_reason = perm_manager.get_block_reason(command)
            return ToolResult.denied(f"Blocked command: {block_reason}")

        # Check permission
        should_allow = perm_manager.should_allow("run_command", command)
        if should_allow is False:
            return ToolResult.denied("Command execution denied")
        elif should_allow is None:
            # Need to prompt
            detail = danger_reason if danger_reason else command
            decision = perm_manager.prompt_user(self.console, "run_command", detail)
            if decision == PermissionDecision.DENY:
                return ToolResult.denied("Command execution denied by user")

        # Handle background execution
        if run_in_background:
            job_manager = get_job_manager()
            job_id = job_manager.start_job(command, working_dir, timeout)
            return ToolResult.ok(
                f"Command started in background with job ID: {job_id}",
                data={"job_id": job_id}
            )

        # Synchronous execution
        try:
            # Build command for shell
            shell_cmd = get_shell_command(command)

            # Execute
            result = subprocess.run(
                shell_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
            )

            output_parts = []
            if result.stdout:
                output_parts.append(result.stdout)
            if result.stderr:
                output_parts.append(f"[stderr]\n{result.stderr}")

            output = "\n".join(output_parts) if output_parts else "(no output)"

            if result.returncode != 0:
                return ToolResult.fail(
                    f"Command failed with exit code {result.returncode}\n{output}"
                )

            return ToolResult.ok(output, data={"exit_code": result.returncode})

        except subprocess.TimeoutExpired:
            return ToolResult.fail(f"Command timed out after {timeout} seconds")
        except FileNotFoundError:
            return ToolResult.fail(f"Command not found: {command.split()[0]}")
        except Exception as e:
            return ToolResult.fail(f"Error executing command: {e}")
