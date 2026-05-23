from typing import Any
from tools.base import BaseTool


class ToolRegistry:
    """
    Registry for managing and executing active tools.
    """
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def execute_tool(self, name: str, *args, **kwargs) -> Any:
        tool = self.get(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' is not registered."}
        try:
            result = tool.execute(*args, **kwargs)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e), "tool": name}

    def list_tools(self, category: str = None) -> dict:
        tools = self._tools.values()
        if category:
            tools = [t for t in tools if t.category == category]
        return {t.name: {"description": t.description, "category": t.category} for t in tools}
