from tools.base import ToolContext

_TRIGGERS = ["rangkum", "ringkas", "summarize", "detail", "jelaskan", "explain", "cari tahu", "cari", "search"]


def _should_process(text: str) -> bool:
    lower = text.lower()
    return any(t in lower for t in _TRIGGERS)


def _summarize(results: list[dict]) -> str:
    if not results:
        return ""
    parts = []
    for r in results[:3]:
        snippet = r.get("snippet", r.get("content", ""))[:200]
        title = r.get("title", "")
        if title and snippet:
            parts.append(f"{title}: {snippet}")
        elif snippet:
            parts.append(snippet)
    return "\n".join(parts)


class Cognition:
    def __init__(self, tools: dict):
        self.tools = tools

    @staticmethod
    def can_handle(text: str) -> bool:
        return _should_process(text)

    def process(self, text: str) -> str | None:
        if not self.can_handle(text):
            return None

        search_fn = self.tools.get("web_search")
        extract_fn = self.tools.get("web_extract")
        if search_fn is None:
            return None

        raw_result = search_fn(text)
        if not raw_result.success:
            return None

        results = raw_result.data.get("results", [])
        if not results:
            return None

        urls = [r["url"] for r in results if r.get("url")]
        if urls and extract_fn is not None:
            urls_str = "\n".join(urls[:3])
            extract_result = extract_fn(urls_str)
            if extract_result.success:
                extracted = extract_result.data.get("results", [])
                if extracted:
                    content = extracted[0].get("content", "")[:500]
                    if content:
                        return content

        return _summarize(results)
