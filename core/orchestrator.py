from core.intent_router import IntentRouter
from core.state_manager import StateManager


def _format_web_search(r) -> str:
    if not r.success:
        return r.error or "Web search tidak tersedia."
    results = (r.data or {}).get("results", [])
    lines = ["[sumber: Tavily]"]
    for i, item in enumerate(results[:5]):
        lines.append(f"[{i + 1}] {item['title']}")
        lines.append(f"    URL: {item['url']}")
        if item.get("snippet"):
            lines.append(f"    {item['snippet']}")
    return "\n".join(lines)


def _format_web_extract(r) -> str:
    if not r.success:
        return r.error or "Extract gagal."
    data = r.data or {}
    lines = ["[sumber: Tavily Extract]"]
    for item in data.get("results", []):
        lines.append(f"URL: {item.get('url', '?')}")
        content = (item.get("raw_content") or "")[:800]
        if content:
            lines.append(content)
        lines.append("")
    for f in data.get("failed_results", []):
        lines.append(f"Gagal: {f.get('url')} — {f.get('error', 'unknown')}")
    if len(lines) == 1:
        return "Tidak ada konten yang berhasil diekstrak."
    return "\n".join(lines)


def _format_datetime(r) -> str:
    return (r.data or "") if r.success else (r.error or "?")


def _format_calculator(r) -> str:
    if not r.success:
        return r.error or "?"
    return (r.data or {}).get("result", "?")


def _format_tavily_usage(r) -> str:
    if not r.success:
        return r.error or "Usage tidak tersedia."
    raw = (r.data or {}).get("raw", {})
    key = raw.get("key", {})
    acct = raw.get("account", {})
    limit = key.get("limit")
    limit_str = str(limit) if limit is not None else "-"
    lines = [
        "[sumber: Tavily Usage]",
        f"Plan       : {acct.get('current_plan', '?')}",
        f"Key usage  : {key.get('usage', '?')} / {limit_str}",
        f"  search   : {key.get('search_usage', 0)}",
        f"  extract  : {key.get('extract_usage', 0)}",
        f"  crawl    : {key.get('crawl_usage', 0)}",
        f"Plan usage : {acct.get('plan_usage', '?')} / {acct.get('plan_limit', '?')}",
    ]
    paygo = acct.get("paygo_usage")
    if paygo is not None:
        paygo_limit = acct.get("paygo_limit")
        paygo_str = str(paygo_limit) if paygo_limit is not None else "-"
        lines.append(f"PayGo usage: {paygo} / {paygo_str}")
    return "\n".join(lines)


_FORMATTERS = {
    "web_search": _format_web_search,
    "web_extract": _format_web_extract,
    "datetime": _format_datetime,
    "calculator": _format_calculator,
    "tavily_usage": _format_tavily_usage,
}


class Orchestrator:
    """
    Thin coordinator: routes intent → tool → format → LLM.
    """

    def __init__(self, agent, tools_registry=None):
        self.agent = agent
        self.tools = tools_registry or {}
        self.intent = IntentRouter()
        self.state = StateManager()

    def register_tool(self, name, func):
        self.tools[name] = func

    def detect_intent(self, user_input: str) -> str:
        return self.intent.detect(user_input)

    def _run_tool(self, tool_name, user_input, context_label):
        tool = self.tools.get(tool_name)
        if not tool:
            return f"Tool '{tool_name}' tidak tersedia."
        try:
            if tool_name == "datetime":
                result = tool()
            else:
                result = tool(user_input)

            self.state.record(tool_name, user_input, result)
            fmt = _FORMATTERS.get(tool_name, lambda r: str(r.data or r.error or ""))(result)
            return self.agent.chat_with_context(
                user_input,
                tool_result=f"{context_label}:\n{fmt}",
            )
        except Exception as e:
            return self.agent.chat_with_context(
                user_input,
                tool_result=f"{context_label} error: {e}",
            )

    def handle(self, user_input: str):
        ref = self.state.resolve(user_input)
        if ref:
            return self._run_tool("web_extract", ref["url"], "Extracted content")

        intent = self.intent.detect(user_input)
        if intent == "web_search":
            return self._run_tool("web_search", user_input, "Web search result")
        if intent == "datetime":
            return self._run_tool("datetime", user_input, "Current datetime")
        if intent == "calculator":
            return self._run_tool("calculator", user_input, "Calculation result")
        if intent == "memory_write":
            self.agent.long_memory.remember("fact", user_input)
            return "Oke, aku simpan itu di memori."
        return self.agent.chat_with_context(user_input)
