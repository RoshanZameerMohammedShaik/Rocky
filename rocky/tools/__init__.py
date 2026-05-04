"""Tools for Rocky.Ai."""

from rocky.tools.base import Tool, ToolResult, ToolParameter, get_tool_registry
from rocky.tools.files import (
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    ListDirectoryTool,
    SearchFilesTool,
    GlobFilesTool,
    SummarizeFileTool,
)
from rocky.tools.shell import RunCommandTool
from rocky.tools.web import WebSearchTool, WebFetchTool
from rocky.tools.media import DescribeImageTool, TranscribeAudioTool, ProcessVideoTool
from rocky.tools.git import GitStatusTool, GitDiffTool, GitLogTool, GitCommitTool
from rocky.tools.knowledge import IndexFilesTool, SearchKnowledgeTool
from rocky.tools.task_plan import TaskPlanTool

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
    "GlobFilesTool",
    "SummarizeFileTool",
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
    # Task planning
    "TaskPlanTool",
]
