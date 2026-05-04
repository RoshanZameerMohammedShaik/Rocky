"""Dynamic environment context for Rocky.Ai.

Auto-gathers system state and injects into the system prompt.
Refreshes automatically after state-changing tool calls.
"""

import os
import subprocess
import platform
from dataclasses import dataclass, field
from typing import Optional
from rocky.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SessionContext:
    """Environment context gathered at session start."""

    working_dir: str = ""
    is_git_repo: bool = False
    git_branch: str = ""
    git_status_summary: str = ""
    git_recent_commits: list[str] = field(default_factory=list)
    os_name: str = ""
    shell: str = ""
    python_version: str = ""
    ram_gb: int = 0
    has_gpu: bool = False
    gpu_name: str = ""
    internet_available: bool = False
    current_model: str = ""
    user_persona_summary: str = ""

    def render_for_prompt(self) -> str:
        """Render context as text for system prompt injection."""
        lines = ["## Current Environment"]
        lines.append(f"- Working directory: {self.working_dir}")

        if self.is_git_repo:
            lines.append(f"- Git: {self.git_branch} branch, {self.git_status_summary}")
            if self.git_recent_commits:
                commits = ", ".join(self.git_recent_commits[:5])
                lines.append(f"- Recent commits: {commits}")

        gpu_info = f", {self.gpu_name}" if self.has_gpu else ""
        lines.append(
            f"- System: {self.os_name}, {self.shell}, "
            f"Python {self.python_version}, {self.ram_gb}GB RAM{gpu_info}"
        )

        if self.current_model:
            lines.append(f"- Model: {self.current_model}")

        status = "available" if self.internet_available else "offline"
        lines.append(f"- Internet: {status}")

        if self.user_persona_summary:
            lines.append("")
            lines.append("## About This User")
            lines.append(self.user_persona_summary)

        return "\n".join(lines)


class ContextGatherer:
    """Gathers environment context."""

    def __init__(self):
        self._last_context: Optional[SessionContext] = None
        self._call_count = 0

    def gather(self, working_dir: Optional[str] = None) -> SessionContext:
        """Gather full environment context."""
        ctx = SessionContext()

        ctx.working_dir = working_dir or os.getcwd()
        ctx.os_name = platform.system()
        ctx.shell = os.environ.get("SHELL", "unknown")
        ctx.python_version = platform.python_version()

        # RAM
        try:
            from rocky.utils.platform import get_memory_gb
            ctx.ram_gb = get_memory_gb()
        except Exception:
            ctx.ram_gb = 0

        # GPU
        try:
            from rocky.utils.platform import has_gpu
            ctx.has_gpu = has_gpu()
        except Exception:
            ctx.has_gpu = False

        # Internet
        try:
            from rocky.utils.network import is_online
            ctx.internet_available = is_online()
        except Exception:
            ctx.internet_available = False

        # GPU name
        if ctx.has_gpu:
            ctx.gpu_name = self._get_gpu_name()

        # Git info
        git_info = self._get_git_info(ctx.working_dir)
        if git_info:
            ctx.is_git_repo = True
            ctx.git_branch = git_info.get("branch", "")
            ctx.git_status_summary = git_info.get("status", "")
            ctx.git_recent_commits = git_info.get("commits", [])

        self._last_context = ctx
        return ctx

    def refresh_git_only(self, working_dir: Optional[str] = None) -> None:
        """Lightweight refresh — only git state."""
        if self._last_context is None:
            self.gather(working_dir)
            return

        wd = working_dir or self._last_context.working_dir
        git_info = self._get_git_info(wd)
        if git_info:
            self._last_context.git_branch = git_info.get("branch", "")
            self._last_context.git_status_summary = git_info.get("status", "")
            self._last_context.git_recent_commits = git_info.get("commits", [])

    def should_refresh(self, tool_name: str) -> bool:
        """Check if a tool call should trigger context refresh."""
        self._call_count += 1

        # Full refresh triggers
        if tool_name == "run_command":
            return True  # might have cd'd

        # Git-only refresh triggers
        git_tools = {"git_commit", "write_file", "edit_file"}
        if tool_name in git_tools:
            return True

        # Periodic lightweight refresh
        if self._call_count % 20 == 0:
            return True

        return False

    @property
    def current(self) -> Optional[SessionContext]:
        return self._last_context

    def _get_git_info(self, path: str) -> Optional[dict]:
        """Get git repo information."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=path, capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return None

            info = {}

            # Branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=path, capture_output=True, text=True, timeout=5
            )
            info["branch"] = result.stdout.strip() or "detached"

            # Status summary
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=path, capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().splitlines()
            modified = sum(1 for line in lines if line.startswith(" M") or line.startswith("M"))
            untracked = sum(1 for line in lines if line.startswith("??"))
            staged = sum(1 for line in lines if line[0] in "AMDRC")

            parts = []
            if modified:
                parts.append(f"{modified} modified")
            if staged:
                parts.append(f"{staged} staged")
            if untracked:
                parts.append(f"{untracked} untracked")
            info["status"] = ", ".join(parts) if parts else "clean"

            # Recent commits
            result = subprocess.run(
                ["git", "-P", "log", "--oneline", "-n5"],
                cwd=path, capture_output=True, text=True, timeout=5
            )
            info["commits"] = [
                line.split(" ", 1)[1] if " " in line else line
                for line in result.stdout.strip().splitlines()[:5]
            ]

            return info

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"Git info gathering failed: {e}")
            return None

    def _get_gpu_name(self) -> str:
        """Detect GPU name."""
        # NVIDIA
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().splitlines()[0]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # macOS Metal
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True, text=True, timeout=5
                )
                if "Apple" in result.stdout:
                    return result.stdout.strip().split("\n")[0]
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        return "GPU detected"
