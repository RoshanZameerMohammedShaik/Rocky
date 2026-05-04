"""Permission prompts for Rocky.Ai."""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from enum import Enum
from typing import Optional


class Permission(Enum):
    ALLOW = "allow"      # Allow once
    TRUST = "trust"      # Trust for session
    DENY = "deny"        # Deny


class PermissionManager:
    """Manages command execution permissions."""
    
    def __init__(self):
        self.trusted_session = False
        self._denied_commands: set[str] = set()
    
    def enable_trust(self):
        """Enable trust mode for the session."""
        self.trusted_session = True
    
    def disable_trust(self):
        """Disable trust mode."""
        self.trusted_session = False
    
    def is_trusted(self) -> bool:
        """Check if session is in trust mode."""
        return self.trusted_session
    
    def request_permission(
        self, 
        console: Console, 
        command: str,
        reason: Optional[str] = None
    ) -> Permission:
        """Request permission to run a command."""
        
        # If trusted, auto-allow
        if self.trusted_session:
            return Permission.ALLOW
        
        # Show permission prompt
        console.print()
        
        content = f"[bold white]$ {command}[/bold white]"
        if reason:
            content += f"\n\n[yellow]⚠️ {reason}[/yellow]"
        
        panel = Panel(
            content,
            title="[bold]Rocky.Ai wants to run:[/bold]",
            border_style="yellow",
        )
        console.print(panel)
        
        console.print()
        console.print("[bold][A][/bold]llow once  •  [bold][T][/bold]rust for session  •  [bold][D][/bold]eny")
        console.print()
        
        while True:
            choice = Prompt.ask(
                "Your choice",
                choices=["a", "A", "t", "T", "d", "D", "allow", "trust", "deny"],
                default="a"
            ).lower()
            
            if choice in ("a", "allow"):
                return Permission.ALLOW
            elif choice in ("t", "trust"):
                self.trusted_session = True
                console.print("[green]✓ Trust enabled for this session[/green]")
                return Permission.TRUST
            elif choice in ("d", "deny"):
                return Permission.DENY


# Global permission manager
_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Get or create global permission manager."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager
