"""Platform-specific utilities for Rocky.Ai."""

import os
import platform
import shutil
from pathlib import Path
from typing import Optional


def get_platform() -> str:
    """Get current platform: 'macos', 'windows', or 'linux'."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    return "linux"


def get_shell() -> str:
    """Get appropriate shell for current platform."""
    if get_platform() == "windows":
        return "powershell"
    return os.environ.get("SHELL", "/bin/bash")


def get_shell_command(command: str) -> list[str]:
    """Wrap command for appropriate shell."""
    plat = get_platform()
    if plat == "windows":
        return ["powershell", "-Command", command]
    return [get_shell(), "-c", command]


def which(program: str) -> Optional[Path]:
    """Find program in PATH, cross-platform."""
    path = shutil.which(program)
    return Path(path) if path else None


def is_command_available(command: str) -> bool:
    """Check if a command is available."""
    return which(command) is not None


def get_home_dir() -> Path:
    """Get user home directory."""
    return Path.home()


def get_temp_dir() -> Path:
    """Get temp directory."""
    import tempfile
    return Path(tempfile.gettempdir())


def get_cpu_count() -> int:
    """Get number of CPU cores."""
    return os.cpu_count() or 1


def get_memory_gb() -> float:
    """Get total system memory in GB."""
    try:
        import psutil
        return psutil.virtual_memory().total / (1024**3)
    except ImportError:
        # Fallback for systems without psutil
        return 8.0  # Assume minimum
