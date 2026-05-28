from tools.base import ToolResult


class Orchestrator:
    def __init__(self, tools: dict | None = None):
        self.tools: dict = tools or {}

    def register_tool(self, name: str, func):
        self.tools[name] = func

    def run_tool(self, name: str, input_: str = "") -> ToolResult:
        tool = self.tools.get(name)
        if not tool:
            return ToolResult.fail(f"Tool '{name}' tidak tersedia.")
        try:
            if name == "datetime":
                return tool()
            return tool(input_)
        except Exception as e:
            return ToolResult.fail(str(e))
