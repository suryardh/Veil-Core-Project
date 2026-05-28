"""
Formatter layer for Veil tool results.
Each tool type has a dedicated formatter.
Supports multiple render modes (text, json) with truncation.
"""

import json
from collections.abc import Callable

from tools.base import ToolResult


def truncate_text(text: str, limit: int = 800) -> str:
    """Truncate text to limit chars, appending ... if cut."""
    if not text or len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _fallback(result: ToolResult) -> str:
    if result.error:
        return result.error
    if result.data is None:
        return ""
    try:
        return json.dumps(result.data, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(result.data)


def format_web_search(r: ToolResult) -> str:
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


def format_web_extract(r: ToolResult) -> str:
    if not r.success:
        return r.error or "Extract gagal."
    data = r.data or {}
    lines = ["[sumber: Tavily Extract]"]
    for item in data.get("results", []):
        lines.append(f"URL: {item.get('url', '?')}")
        content = truncate_text(item.get("raw_content") or "")
        if content:
            lines.append(content)
        lines.append("")
    for f in data.get("failed_results", []):
        lines.append(f"Gagal: {f.get('url')} — {f.get('error', 'unknown')}")
    if len(lines) == 1:
        return "Tidak ada konten yang berhasil diekstrak."
    return "\n".join(lines)


def format_datetime(r: ToolResult) -> str:
    return (r.data or "") if r.success else (r.error or "?")


def format_calculator(r: ToolResult) -> str:
    if not r.success:
        return r.error or "?"
    return (r.data or {}).get("result", "?")


def format_tavily_usage(r: ToolResult) -> str:
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


_FORMATTERS: dict[str, Callable[[ToolResult], str]] = {
    "web_search": format_web_search,
    "web_extract": format_web_extract,
    "datetime": format_datetime,
    "calculator": format_calculator,
    "tavily_usage": format_tavily_usage,
}


def format_tool_result(tool_name: str, result: ToolResult, mode: str = "text") -> str:
    """Render a ToolResult into a display string.

    Args:
        tool_name: Tool identifier (e.g. "web_search").
        result: ToolResult from tool execution.
        mode: Output format — "text" (default), "json".

    Returns:
        Formatted string ready for prompt injection.
    """
    if mode == "json":
        return json.dumps({"tool": tool_name, "result": result.data}, indent=2, ensure_ascii=False)

    fmt = _FORMATTERS.get(tool_name)
    if fmt is None:
        return _fallback(result)
    return fmt(result)
