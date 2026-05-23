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
