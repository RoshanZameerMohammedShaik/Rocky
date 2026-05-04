"""Input validation and safety checks for Rocky.Ai."""

import re
from dataclasses import dataclass
from enum import Enum
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


# Sensitive data detection


class SensitiveDataType(Enum):
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    API_KEY = "api_key"
    PASSWORD = "password"
    CREDIT_CARD = "credit_card"
    PRIVATE_KEY = "private_key"


@dataclass
class SensitiveDataMatch:
    type: SensitiveDataType
    value: str
    description: str


# Patterns for sensitive data detection
SENSITIVE_PATTERNS = [
    (
        SensitiveDataType.PRIVATE_KEY,
        r"-----BEGIN\s+(RSA |EC |DSA )?PRIVATE KEY-----",
        "Private key detected",
    ),
    (SensitiveDataType.API_KEY, r"(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}", "AWS access key"),
    (SensitiveDataType.API_KEY, r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}", "GitHub token"),
    (SensitiveDataType.API_KEY, r"sk-[A-Za-z0-9]{32,}", "API secret key"),
    (SensitiveDataType.API_KEY, r"xox[baprs]-[0-9A-Za-z\-]{10,}", "Slack token"),
    (
        SensitiveDataType.CREDIT_CARD,
        r"\b(?:4[0-9]{3}|5[1-5][0-9]{2}|3[47][0-9]{1})[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}\b",
        "Credit card number",
    ),
    (SensitiveDataType.SSN, r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "Possible SSN"),
    (
        SensitiveDataType.PASSWORD,
        r"""(?:password|passwd|pwd|secret)\s*[=:]\s*['"][^'"]{4,}['"]""",
        "Password in assignment",
    ),
    (
        SensitiveDataType.PHONE,
        r"\b(?:\+1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b",
        "Phone number",
    ),
    (
        SensitiveDataType.EMAIL,
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b",
        "Email address",
    ),
]

_sensitive_compiled = [(t, re.compile(p, re.IGNORECASE), d) for t, p, d in SENSITIVE_PATTERNS]


def detect_sensitive_data(text: str) -> list[SensitiveDataMatch]:
    """Detect sensitive data patterns in text."""
    matches = []
    for data_type, pattern, description in _sensitive_compiled:
        for match in pattern.finditer(text):
            matches.append(SensitiveDataMatch(
                type=data_type,
                value=match.group(0)[:20] + "..." if len(match.group(0)) > 20 else match.group(0),
                description=description,
            ))
    return matches
