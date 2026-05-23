import re
import time
from dataclasses import dataclass, field

_REF_PATTERNS = [
    re.compile(r"(?:nomor|no\.?|#)\s*(\d+)", re.IGNORECASE),
    re.compile(r"yang (pertama|kedua|ketiga|keempat|kelima|\d+)", re.IGNORECASE),
    re.compile(r"(?:buka|lihat|open)\s*(?:nomor|no\.?|#|yang\s+)?\s*(\d+|pertama|kedua|ketiga|keempat|kelima)", re.IGNORECASE),
    re.compile(r"link (pertama|kedua|ketiga|\d+)", re.IGNORECASE),
]

_ORDINAL = {
    "pertama": 1, "kedua": 2, "ketiga": 3, "keempat": 4, "kelima": 5,
}


def _parse_ref_index(text: str) -> int | None:
    for pat in _REF_PATTERNS:
        m = pat.search(text)
        if m:
            val = m.group(1)
            if val in _ORDINAL:
                return _ORDINAL[val]
            try:
                return int(val)
            except ValueError:
                return None
    return None


@dataclass
class SessionState:
    """Cross-turn conversation state for reference resolution and tool chaining."""
    last_search_results: list = field(default_factory=list)
    last_tool: str | None = None
    active_topic: str | None = None
    tool_history: list = field(default_factory=list)

    def record_tool(self, tool_name: str, query: str, result):
        self.last_tool = tool_name
        self.active_topic = query
        self.tool_history.append({
            "tool": tool_name,
            "query": query,
            "timestamp": time.time(),
        })
        if tool_name == "web_search" and result.success and result.data:
            self.last_search_results = result.data.get("results", [])


class StateManager:
    """
    Manages session state and resolves user references to prior results.
    """

    def __init__(self):
        self.session = SessionState()

    def record(self, tool_name: str, query: str, result):
        self.session.record_tool(tool_name, query, result)

    def resolve(self, text: str) -> dict | None:
        if not self.session.last_search_results:
            return None
        idx = _parse_ref_index(text)
        if idx is None:
            return None
        if idx < 1 or idx > len(self.session.last_search_results):
            return None
        return self.session.last_search_results[idx - 1]
