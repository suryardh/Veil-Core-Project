import re
from tools.base import ToolResult


CALC_PATTERNS = [
    re.compile(r"^[\d\s+\-*/().,%^]+$"),
    re.compile(r"(^|\s)(hitung|calculate|persen)(\s|$)", re.IGNORECASE),
    re.compile(r"\d+\s*[+\-*/%]\s*\d+"),
    re.compile(r"\b(sqrt|sin|cos|tan|log|abs|round|pow)\s*\(", re.I),
    re.compile(r"\d+\s*%\s*(?:dari)?\s*\d+"),
]

_DATETIME_TRIGGERS = ["jam berapa", "tanggal berapa", "sekarang jam", "what time", "what date"]

_TAVILY_TRIGGERS = ["cek usage", "cek tavily", "tavily usage", "sisa usage", "penggunaan api"]


def is_calculator_query(text: str) -> bool:
    return any(p.search(text) for p in CALC_PATTERNS)


def is_datetime_query(text: str) -> bool:
    lower = text.lower()
    return any(t in lower for t in _DATETIME_TRIGGERS)


def is_tavily_query(text: str) -> bool:
    lower = text.lower()
    return any(t in lower for t in _TAVILY_TRIGGERS)


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
            return tool(input_)
        except Exception as e:
            return ToolResult.fail(str(e))
