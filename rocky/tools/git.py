"""Git operations tool for Rocky.Ai."""

import subprocess
from pathlib import Path
from typing import Optional
from rocky.tools.base import Tool, ToolResult, ToolParameter
from rocky.utils.platform import is_command_available
from rocky.utils.logging import get_logger

logger = get_logger(__name__)


class GitStatusTool(Tool):
    """Show git repository status."""
    
    def __init__(self):
        super().__init__(
            name="git_status",
            description="Show the status of a git repository.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the git repository",
                    required=False,
                    default="."
                ),
            ]
        )
    
    def execute(self, path: str = ".") -> ToolResult:
        if not is_command_available("git"):
            return ToolResult.fail("Git is not installed.")
        
        repo_path = Path(path).expanduser().resolve()
        
        try:
            result = subprocess.run(
                ["git", "-P", "status"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return ToolResult.fail(result.stderr or "Not a git repository")
            
            return ToolResult.ok(result.stdout, data={"path": str(repo_path)})
            
        except subprocess.TimeoutExpired:
            return ToolResult.fail("Git command timed out")
        except Exception as e:
            return ToolResult.fail(f"Git error: {e}")


class GitDiffTool(Tool):
    """Show git diff."""
    
    def __init__(self):
        super().__init__(
            name="git_diff",
            description="Show changes in a git repository.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the git repository",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="staged",
                    type="boolean",
                    description="Show staged changes only",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="file",
                    type="string",
                    description="Specific file to diff",
                    required=False,
                    default=None
                ),
            ]
        )
    
    def execute(self, path: str = ".", staged: bool = False, file: Optional[str] = None) -> ToolResult:
        if not is_command_available("git"):
            return ToolResult.fail("Git is not installed.")
        
        repo_path = Path(path).expanduser().resolve()
        
        try:
            cmd = ["git", "-P", "diff"]
            if staged:
                cmd.append("--cached")
            if file:
                cmd.extend(["--", file])
            
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return ToolResult.fail(result.stderr or "Git diff failed")
            
            output = result.stdout or "(no changes)"
            return ToolResult.ok(output, data={"path": str(repo_path)})
            
        except Exception as e:
            return ToolResult.fail(f"Git error: {e}")


class GitLogTool(Tool):
    """Show git commit history."""
    
    def __init__(self):
        super().__init__(
            name="git_log",
            description="Show recent commit history.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the git repository",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="count",
                    type="integer",
                    description="Number of commits to show",
                    required=False,
                    default=10
                ),
                ToolParameter(
                    name="oneline",
                    type="boolean",
                    description="Show compact one-line format",
                    required=False,
                    default=True
                ),
            ]
        )
    
    def execute(self, path: str = ".", count: int = 10, oneline: bool = True) -> ToolResult:
        if not is_command_available("git"):
            return ToolResult.fail("Git is not installed.")
        
        repo_path = Path(path).expanduser().resolve()
        
        try:
            cmd = ["git", "-P", "log", f"-n{count}"]
            if oneline:
                cmd.append("--oneline")
            
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return ToolResult.fail(result.stderr or "Git log failed")
            
            return ToolResult.ok(result.stdout, data={"path": str(repo_path), "count": count})
            
        except Exception as e:
            return ToolResult.fail(f"Git error: {e}")


class GitCommitTool(Tool):
    """Create a git commit."""
    
    def __init__(self, console=None):
        super().__init__(
            name="git_commit",
            description="Create a git commit with the staged changes.",
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="Commit message",
                    required=True
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the git repository",
                    required=False,
                    default="."
                ),
            ]
        )
        self.console = console
    
    def execute(self, message: str, path: str = ".") -> ToolResult:
        if not is_command_available("git"):
            return ToolResult.fail("Git is not installed.")
        
        repo_path = Path(path).expanduser().resolve()
        
        try:
            # Check if there are staged changes
            status_result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=repo_path,
                capture_output=True,
                timeout=10
            )
            
            if status_result.returncode == 0:
                return ToolResult.fail("No staged changes to commit. Use 'git add' first.")
            
            # Create commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return ToolResult.fail(result.stderr or "Commit failed")
            
            return ToolResult.ok(result.stdout, data={"path": str(repo_path), "message": message})
            
        except Exception as e:
            return ToolResult.fail(f"Git error: {e}")
