"""Base tool class for Rocky.AI."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class ToolStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class ToolResult:
    """Result from a tool execution."""
    status: ToolStatus
    output: str
    data: Optional[Any] = None
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.status == ToolStatus.SUCCESS
    
    @classmethod
    def ok(cls, output: str, data: Any = None) -> "ToolResult":
        return cls(status=ToolStatus.SUCCESS, output=output, data=data)
    
    @classmethod
    def fail(cls, error: str) -> "ToolResult":
        return cls(status=ToolStatus.ERROR, output="", error=error)
    
    @classmethod
    def denied(cls, reason: str = "Permission denied") -> "ToolResult":
        return cls(status=ToolStatus.PERMISSION_DENIED, output="", error=reason)


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # "string", "integer", "boolean", "array"
    description: str
    required: bool = True
    default: Any = None


@dataclass
class Tool(ABC):
    """Base class for all tools."""
    
    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
    
    def to_schema(self) -> dict:
        """Convert tool to JSON schema for LLM."""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }
    
    def validate_params(self, **kwargs) -> Optional[str]:
        """Validate parameters. Returns error message or None if valid."""
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return f"Missing required parameter: {param.name}"
        return None


class ToolRegistry:
    """Registry of available tools."""
    
    def __init__(self):
        self._tools: dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def get_schemas(self) -> list[dict]:
        """Get JSON schemas for all tools."""
        return [tool.to_schema() for tool in self._tools.values()]


# Global tool registry
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
