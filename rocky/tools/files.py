"""File operation tools for Rocky.Ai."""

import os
import re
import glob as glob_module
from pathlib import Path
from typing import Optional
from rocky.tools.base import Tool, ToolResult, ToolParameter
from rocky.utils.validators import is_binary_file


class ReadFileTool(Tool):
    """Read contents of a file."""
    
    def __init__(self):
        super().__init__(
            name="read_file",
            description="Read the contents of a file at the specified path",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to read",
                    required=True
                ),
                ToolParameter(
                    name="start_line",
                    type="integer",
                    description="Starting line number (1-based)",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="end_line",
                    type="integer",
                    description="Ending line number (1-based, inclusive)",
                    required=False,
                    default=None
                ),
            ]
        )
    
    def execute(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> ToolResult:
        try:
            file_path = Path(path).expanduser().resolve()
            
            if not file_path.exists():
                return ToolResult.fail(f"File not found: {path}")
            
            if not file_path.is_file():
                return ToolResult.fail(f"Not a file: {path}")
            
            if is_binary_file(file_path):
                return ToolResult.fail(f"Cannot read binary file: {path}")
            
            content = file_path.read_text(encoding="utf-8", errors="replace")
            
            # Handle line range
            if start_line is not None or end_line is not None:
                lines = content.splitlines()
                start = (start_line or 1) - 1
                end = end_line or len(lines)
                content = "\n".join(lines[start:end])
            
            return ToolResult.ok(content, data={"path": str(file_path), "lines": len(content.splitlines())})
            
        except PermissionError:
            return ToolResult.fail(f"Permission denied: {path}")
        except Exception as e:
            return ToolResult.fail(f"Error reading file: {e}")


class WriteFileTool(Tool):
    """Write content to a file."""
    
    def __init__(self):
        super().__init__(
            name="write_file",
            description="Write content to a file, creating it if it doesn't exist",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to write",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write to the file",
                    required=True
                ),
            ]
        )
    
    def execute(self, path: str, content: str) -> ToolResult:
        try:
            file_path = Path(path).expanduser().resolve()
            
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file exists for reporting
            existed = file_path.exists()
            old_content = file_path.read_text() if existed else None
            
            file_path.write_text(content, encoding="utf-8")
            
            action = "Modified" if existed else "Created"
            return ToolResult.ok(
                f"{action} file: {path}",
                data={
                    "path": str(file_path),
                    "action": action.lower(),
                    "old_content": old_content,
                    "new_content": content
                }
            )
            
        except PermissionError:
            return ToolResult.fail(f"Permission denied: {path}")
        except Exception as e:
            return ToolResult.fail(f"Error writing file: {e}")


class EditFileTool(Tool):
    """Edit a file using find and replace."""
    
    def __init__(self):
        super().__init__(
            name="edit_file",
            description="Edit a file by replacing old_str with new_str",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to edit",
                    required=True
                ),
                ToolParameter(
                    name="old_str",
                    type="string",
                    description="String to find and replace",
                    required=True
                ),
                ToolParameter(
                    name="new_str",
                    type="string",
                    description="Replacement string",
                    required=True
                ),
            ]
        )
    
    def execute(self, path: str, old_str: str, new_str: str) -> ToolResult:
        try:
            file_path = Path(path).expanduser().resolve()
            
            if not file_path.exists():
                return ToolResult.fail(f"File not found: {path}")
            
            content = file_path.read_text(encoding="utf-8")
            old_content = content
            
            # Check if old_str exists
            if old_str not in content:
                return ToolResult.fail(f"String not found in file: {old_str[:50]}...")
            
            # Count occurrences
            count = content.count(old_str)
            if count > 1:
                return ToolResult.fail(
                    f"String found {count} times. Please provide more context to make it unique."
                )
            
            # Perform replacement
            new_content = content.replace(old_str, new_str, 1)
            file_path.write_text(new_content, encoding="utf-8")
            
            return ToolResult.ok(
                f"Edited file: {path}",
                data={
                    "path": str(file_path),
                    "old_content": old_content,
                    "new_content": new_content
                }
            )
            
        except PermissionError:
            return ToolResult.fail(f"Permission denied: {path}")
        except Exception as e:
            return ToolResult.fail(f"Error editing file: {e}")


class ListDirectoryTool(Tool):
    """List contents of a directory."""
    
    def __init__(self):
        super().__init__(
            name="list_directory",
            description="List files and directories at the specified path",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the directory to list",
                    required=True
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="Whether to list recursively",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Glob pattern to filter files (e.g., '*.py')",
                    required=False,
                    default=None
                ),
            ]
        )
    
    def execute(self, path: str, recursive: bool = False, pattern: Optional[str] = None) -> ToolResult:
        try:
            dir_path = Path(path).expanduser().resolve()
            
            if not dir_path.exists():
                return ToolResult.fail(f"Directory not found: {path}")
            
            if not dir_path.is_dir():
                return ToolResult.fail(f"Not a directory: {path}")
            
            entries = []
            
            if pattern:
                if recursive:
                    glob_pattern = f"**/{pattern}"
                else:
                    glob_pattern = pattern
                
                for item in dir_path.glob(glob_pattern):
                    rel_path = item.relative_to(dir_path)
                    entry_type = "dir" if item.is_dir() else "file"
                    entries.append(f"[{entry_type}] {rel_path}")
            else:
                if recursive:
                    for item in dir_path.rglob("*"):
                        rel_path = item.relative_to(dir_path)
                        entry_type = "dir" if item.is_dir() else "file"
                        entries.append(f"[{entry_type}] {rel_path}")
                else:
                    for item in sorted(dir_path.iterdir()):
                        entry_type = "dir" if item.is_dir() else "file"
                        entries.append(f"[{entry_type}] {item.name}")
            
            output = "\n".join(entries[:500])  # Limit output
            if len(entries) > 500:
                output += f"\n... and {len(entries) - 500} more"
            
            return ToolResult.ok(output, data={"path": str(dir_path), "count": len(entries)})
            
        except PermissionError:
            return ToolResult.fail(f"Permission denied: {path}")
        except Exception as e:
            return ToolResult.fail(f"Error listing directory: {e}")


class SearchFilesTool(Tool):
    """Search for patterns in files."""
    
    def __init__(self):
        super().__init__(
            name="search_files",
            description="Search for a pattern in files using regex",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Directory to search in",
                    required=True
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Regex pattern to search for",
                    required=True
                ),
                ToolParameter(
                    name="file_pattern",
                    type="string",
                    description="Glob pattern for files to search (e.g., '*.py')",
                    required=False,
                    default="*"
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of results to return",
                    required=False,
                    default=50
                ),
            ]
        )
    
    def execute(
        self, 
        path: str, 
        pattern: str, 
        file_pattern: str = "*",
        max_results: int = 50
    ) -> ToolResult:
        try:
            dir_path = Path(path).expanduser().resolve()
            
            if not dir_path.exists():
                return ToolResult.fail(f"Directory not found: {path}")
            
            regex = re.compile(pattern, re.IGNORECASE)
            results = []
            
            glob_pattern = f"**/{file_pattern}" if not file_pattern.startswith("**/") else file_pattern
            
            for file_path in dir_path.glob(glob_pattern):
                if not file_path.is_file():
                    continue
                
                if is_binary_file(file_path):
                    continue
                
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    for i, line in enumerate(content.splitlines(), 1):
                        if regex.search(line):
                            rel_path = file_path.relative_to(dir_path)
                            results.append(f"{rel_path}:{i}: {line.strip()[:100]}")
                            
                            if len(results) >= max_results:
                                break
                except Exception:
                    continue
                
                if len(results) >= max_results:
                    break
            
            if not results:
                return ToolResult.ok("No matches found", data={"matches": 0})
            
            output = "\n".join(results)
            return ToolResult.ok(output, data={"matches": len(results)})
            
        except re.error as e:
            return ToolResult.fail(f"Invalid regex pattern: {e}")
        except Exception as e:
            return ToolResult.fail(f"Error searching files: {e}")
