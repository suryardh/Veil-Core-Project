from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Normalized return type for all tools."""
    success: bool
    data: Any = None
    error: str | None = None
    source: str = ""
    meta: dict = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any = None, source: str = "", **meta) -> ToolResult:
        return cls(success=True, data=data, source=source, meta=meta)

    @classmethod
    def fail(cls, error: str, source: str = "") -> ToolResult:
        return cls(success=False, data=None, error=error, source=source)


@dataclass
class ToolContext:
    """Structured context passed from runtime to LLM after tool execution."""
    tool: str
    formatted: str
    raw: Any = None
    success: bool = True
    source: str = ""
    error: str | None = None

    @classmethod
    def from_result(cls, tool: str, result: ToolResult, *, label: str = "") -> ToolContext:
        from core.formatter import format_tool_result
        fmt = format_tool_result(tool, result)
        if label:
            fmt = f"{label}:\n{fmt}"
        return cls(
            tool=tool,
            formatted=fmt,
            raw=result.data if result.success else None,
            success=result.success,
            source=result.source,
            error=result.error,
        )

    @classmethod
    def from_error(cls, tool: str, error: str, *, label: str = "") -> ToolContext:
        msg = f"{label} error: {error}" if label else f"Error: {error}"
        return cls(tool=tool, formatted=msg, raw=None, success=False, error=error)


@dataclass
class ToolInfo:
    name: str
    description: str
    category: str = "general"


@dataclass
class ParamInfo:
    name: str
    type: str = "str"
    description: str = ""


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    @property
    def all_tools(self) -> dict[str, BaseTool]:
        return dict(self._tools)

    def describe_tools(self) -> str:
        lines = []
        for name, t in sorted(self._tools.items()):
            lines.append(f"- {name}: {t.description}")
        return "\n".join(lines)

    def describe_for_planner(self) -> str:
        lines = ["Available tools:"]
        for name, t in sorted(self._tools.items()):
            params = ""
            if name in ("web_search", "web_extract", "calculator"):
                params = "(query)"
            elif name == "datetime":
                params = "()"
            lines.append(f"- {name}{params}: {t.description}")
        return "\n".join(lines)


class BaseTool(ABC):
    """
    Abstract base class for all Veil tools.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    def category(self) -> str:
        return "general"

    @property
    def metadata(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
        }

    @abstractmethod
    def execute(self, *args, **kwargs) -> ToolResult:
        ...

    def __call__(self, *args, **kwargs) -> ToolResult:
        return self.execute(*args, **kwargs)
