"""Tools for Rocky.AI."""

from rocky.tools.base import Tool, ToolResult, ToolParameter, get_tool_registry
from rocky.tools.files import (
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    ListDirectoryTool,
    SearchFilesTool,
)
from rocky.tools.shell import RunCommandTool
from rocky.tools.web import WebSearchTool, WebFetchTool
from rocky.tools.media import DescribeImageTool, TranscribeAudioTool, ProcessVideoTool
from rocky.tools.git import GitStatusTool, GitDiffTool, GitLogTool, GitCommitTool
from rocky.tools.knowledge import IndexFilesTool, SearchKnowledgeTool

__all__ = [
    "Tool",
    "ToolResult",
    "ToolParameter",
    "get_tool_registry",
    # File tools
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
    "ListDirectoryTool",
    "SearchFilesTool",
    # Shell
    "RunCommandTool",
    # Web
    "WebSearchTool",
    "WebFetchTool",
    # Media
    "DescribeImageTool",
    "TranscribeAudioTool",
    "ProcessVideoTool",
    # Git
    "GitStatusTool",
    "GitDiffTool",
    "GitLogTool",
    "GitCommitTool",
    # Knowledge
    "IndexFilesTool",
    "SearchKnowledgeTool",
]
