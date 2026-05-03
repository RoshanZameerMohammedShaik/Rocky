"""Shell command execution tool for Rocky.AI."""

import subprocess
import shlex
from typing import Optional
from rocky.tools.base import Tool, ToolResult, ToolParameter
from rocky.utils.platform import get_platform, get_shell_command
from rocky.utils.validators import is_dangerous_command, get_danger_reason
from rocky.ui.permissions import get_permission_manager, Permission
from rich.console import Console


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
            ]
        )
        self.console = console or Console()
    
    def execute(
        self, 
        command: str, 
        working_dir: Optional[str] = None,
        timeout: int = 60
    ) -> ToolResult:
        # Check for dangerous commands
        danger_reason = get_danger_reason(command)
        needs_permission = danger_reason is not None or is_dangerous_command(command)
        
        # Get permission
        perm_manager = get_permission_manager()
        
        if needs_permission or not perm_manager.is_trusted():
            permission = perm_manager.request_permission(
                self.console,
                command,
                reason=danger_reason
            )
            
            if permission == Permission.DENY:
                return ToolResult.denied("Command execution denied by user")
        
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
