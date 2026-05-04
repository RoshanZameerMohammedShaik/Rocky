"""Input validation and safety checks for Rocky.Ai."""

import re
from pathlib import Path
from typing import Optional


# Dangerous command patterns
DANGEROUS_PATTERNS = [
    r"rm\s+(-rf?|--recursive)\s+[/~]",  # rm -rf /
    r"rm\s+-rf?\s+\*",  # rm -rf *
    r">\s*/dev/sd[a-z]",  # Write to disk device
    r"mkfs\.",  # Format filesystem
    r"dd\s+if=.*of=/dev",  # dd to device
    r":\(\)\s*\{\s*:\|:&\s*\}\s*;:",  # Fork bomb
    r"chmod\s+-R\s+777\s+/",  # chmod 777 /
    r"chown\s+-R.*\s+/",  # chown -R /
    r"curl.*\|\s*(ba)?sh",  # Pipe curl to shell
    r"wget.*\|\s*(ba)?sh",  # Pipe wget to shell
]

# Compiled patterns for efficiency
_dangerous_compiled = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


def is_dangerous_command(command: str) -> bool:
    """Check if a command matches dangerous patterns."""
    for pattern in _dangerous_compiled:
        if pattern.search(command):
            return True
    return False


def get_danger_reason(command: str) -> Optional[str]:
    """Get reason why a command is dangerous."""
    reasons = {
        r"rm\s+(-rf?|--recursive)\s+[/~]": "Recursive deletion of system/home directory",
        r"rm\s+-rf?\s+\*": "Recursive deletion with wildcard",
        r">\s*/dev/sd[a-z]": "Direct write to disk device",
        r"mkfs\.": "Filesystem formatting",
        r"dd\s+if=.*of=/dev": "Direct disk write with dd",
        r":\(\)\s*\{\s*:\|:&\s*\}\s*;:": "Fork bomb detected",
        r"chmod\s+-R\s+777\s+/": "Recursive permission change on root",
        r"chown\s+-R.*\s+/": "Recursive ownership change on root",
        r"curl.*\|\s*(ba)?sh": "Piping remote content to shell",
        r"wget.*\|\s*(ba)?sh": "Piping remote content to shell",
    }
    
    for pattern, reason in reasons.items():
        if re.search(pattern, command, re.IGNORECASE):
            return reason
    return None


def is_valid_path(path: str) -> bool:
    """Check if a path string is valid."""
    try:
        Path(path)
        return True
    except Exception:
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing dangerous characters."""
    # Remove path separators and null bytes
    sanitized = re.sub(r'[/\\:\*\?"<>\|\x00]', '_', filename)
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    return sanitized or "unnamed"


def is_binary_file(path: Path) -> bool:
    """Check if a file is binary."""
    try:
        with open(path, 'rb') as f:
            chunk = f.read(8192)
            return b'\x00' in chunk
    except Exception:
        return False
