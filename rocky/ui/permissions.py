# rocky/ui/permissions.py
"""Permission system for Rocky.Ai.

Tiered permissions with inline prompts and session-only state.
All permissions reset when session ends.
"""

import re
from enum import Enum
from typing import Optional
from rich.console import Console
from rocky.utils.logging import get_logger

logger = get_logger(__name__)


class PermissionTier(Enum):
    AUTO_ALLOW = 0  # Pure reads — never prompt
    PROMPT = 1      # Writes/mutations — prompt until trusted
    ALWAYS_PROMPT = 2  # Media/external — always prompt


class PermissionDecision(Enum):
    ALLOW_ONCE = "allow_once"
    DENY = "deny"
    TRUST = "trust"
    TRUST_ALL = "trust_all"


# Tool → Tier mapping
TOOL_TIERS = {
    # Tier 0: Auto-allow
    "read_file": PermissionTier.AUTO_ALLOW,
    "list_directory": PermissionTier.AUTO_ALLOW,
    "search_files": PermissionTier.AUTO_ALLOW,
    "glob_files": PermissionTier.AUTO_ALLOW,
    "summarize_file": PermissionTier.AUTO_ALLOW,
    "git_status": PermissionTier.AUTO_ALLOW,
    "git_log": PermissionTier.AUTO_ALLOW,
    "git_diff": PermissionTier.AUTO_ALLOW,
    "web_search": PermissionTier.AUTO_ALLOW,
    "web_fetch": PermissionTier.AUTO_ALLOW,
    "search_knowledge": PermissionTier.AUTO_ALLOW,
    "task_plan": PermissionTier.AUTO_ALLOW,
    # Tier 1: Prompt
    "write_file": PermissionTier.PROMPT,
    "edit_file": PermissionTier.PROMPT,
    "index_files": PermissionTier.PROMPT,
    "git_commit": PermissionTier.PROMPT,
    "run_command": PermissionTier.PROMPT,
    # Tier 2: Always prompt
    "describe_image": PermissionTier.ALWAYS_PROMPT,
    "transcribe_audio": PermissionTier.ALWAYS_PROMPT,
    "process_video": PermissionTier.ALWAYS_PROMPT,
}

# Always blocked regardless of trust
BLOCKED_PATTERNS = [
    (r"rm\s+(-rf?|--recursive)\s+[/~]", "Recursive deletion of system directory"),
    (r"rm\s+-rf?\s+\*", "Recursive deletion with wildcard"),
    (r"mkfs\.", "Filesystem formatting"),
    (r"dd\s+if=.*of=/dev", "Direct disk write with dd"),
    (r":\(\)\s*\{\s*:\|:&\s*\}\s*;:", "Fork bomb"),
    (r"chmod\s+-R\s+777\s+/", "Recursive chmod 777 on root"),
    (r"chown\s+-R.*\s+/", "Recursive chown on root"),
]

_blocked_compiled = [(re.compile(p, re.IGNORECASE), reason) for p, reason in BLOCKED_PATTERNS]


class PermissionManager:
    """Session-scoped permission manager.

    All state resets when session ends. No persistence.
    """

    def __init__(self):
        self._trusted_tools: set[str] = set()
        self._denied_tools: set[str] = set()
        self._trust_all: bool = False

    def get_tier(self, tool_name: str) -> PermissionTier:
        """Get the permission tier for a tool."""
        return TOOL_TIERS.get(tool_name, PermissionTier.PROMPT)

    def should_allow(self, tool_name: str, command: str = "") -> Optional[bool]:
        """Check if a tool should be allowed.

        Returns:
            True = auto-allow (tier 0 or trusted)
            False = denied or blocked
            None = needs user prompt
        """
        # Check blocked commands first
        if command and self.is_blocked_command(command):
            return False

        # Check denied
        if tool_name in self._denied_tools:
            return False

        # Check trust-all
        if self._trust_all:
            return True

        # Check per-tool trust
        if tool_name in self._trusted_tools:
            return True

        # Check tier
        tier = self.get_tier(tool_name)
        if tier == PermissionTier.AUTO_ALLOW:
            return True

        # Needs prompt
        return None

    def trust_tool(self, tool_name: str):
        """Trust a tool for this session."""
        self._trusted_tools.add(tool_name)
        self._denied_tools.discard(tool_name)

    def deny_tool(self, tool_name: str):
        """Deny a tool for this session."""
        self._denied_tools.add(tool_name)
        self._trusted_tools.discard(tool_name)

    def trust_all(self):
        """Trust all tools for this session."""
        self._trust_all = True
        self._denied_tools.clear()

    def reset(self):
        """Reset all permissions to defaults."""
        self._trusted_tools.clear()
        self._denied_tools.clear()
        self._trust_all = False

    def is_blocked_command(self, command: str) -> bool:
        """Check if command matches always-blocked patterns."""
        for pattern, _ in _blocked_compiled:
            if pattern.search(command):
                return True
        return False

    def get_block_reason(self, command: str) -> Optional[str]:
        """Get reason a command is blocked."""
        for pattern, reason in _blocked_compiled:
            if pattern.search(command):
                return reason
        return None

    def get_status(self) -> dict:
        """Get current permission state for display."""
        return {
            "trust_all": self._trust_all,
            "trusted_tools": sorted(self._trusted_tools),
            "denied_tools": sorted(self._denied_tools),
        }

    def prompt_user(self, console: Console, tool_name: str, detail: str = "") -> PermissionDecision:
        """Show inline permission prompt and get user decision.

        Uses ArrowMenu with options: Allow-Once, Deny, Trust '<tool>', Trust-All ⚠
        """
        from rocky.ui.menu import ArrowMenu

        console.print()
        console.print(f"  [bold]⚙  {tool_name}:[/bold] {detail}")
        console.print()

        menu = ArrowMenu(
            title="",
            options=[
                "Allow-Once",
                "Deny",
                f"Trust '{tool_name}'",
                "Trust-All ⚠",
            ],
            default=0,
            console=console,
        )

        choice = menu.run()

        if choice == "Allow-Once":
            return PermissionDecision.ALLOW_ONCE
        elif choice == "Deny":
            return PermissionDecision.DENY
        elif choice.startswith("Trust '"):
            self.trust_tool(tool_name)
            return PermissionDecision.TRUST
        else:
            # Trust-All — confirm first
            confirm_menu = ArrowMenu(
                title="⚠  This allows Rocky to run ALL tools without asking. Sure?",
                options=["Yes", "No"],
                default=1,  # default No for safety
                console=console,
            )
            if confirm_menu.run() == "Yes":
                self.trust_all()
                return PermissionDecision.TRUST_ALL
            else:
                return PermissionDecision.DENY


# Global instance
_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Get or create global permission manager."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager
