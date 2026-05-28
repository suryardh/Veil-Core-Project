import hashlib
import time

import requests

import config
from tools.base import BaseTool, ToolResult
from utils.async_utils import with_retry

TAVILY_API_BASE = "https://api.tavily.com"
CACHE_TTL = 3600

_SEARCH_ERR = "Web search tidak tersedia — TAVILY_API_KEY belum diset."
_EXTRACT_ERR = "Extract tidak tersedia — TAVILY_API_KEY belum diset."
_USAGE_ERR = "Cek usage tidak tersedia — TAVILY_API_KEY belum diset."


def _api_key() -> str:
    key = config.TAVILY_API_KEY
    if not key:
        raise RuntimeError("TAVILY_API_KEY belum diset")
    return key


def _search(query: str) -> list[dict]:
    resp = requests.post(
        f"{TAVILY_API_BASE}/search",
        json={
            "query": query,
            "search_depth": "basic",
            "max_results": 5,
            "include_answer": False,
        },
        headers={"Authorization": f"Bearer {_api_key()}"},
        timeout=config.SEARCH_TIMEOUT,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Tavily HTTP {resp.status_code}")
    data = resp.json()
    out = []
    for r in data.get("results", []):
        out.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
        })
    if not out:
        raise RuntimeError("tidak ada hasil")
    return out


def check_usage() -> dict:
    resp = requests.get(
        f"{TAVILY_API_BASE}/usage",
        headers={"Authorization": f"Bearer {_api_key()}"},
        timeout=config.SEARCH_TIMEOUT,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Tavily usage HTTP {resp.status_code}")
    return resp.json()


def extract_urls(urls: str | list[str], query: str = "", extract_depth: str = "basic", format: str = "markdown") -> dict:
    body = {"urls": urls, "extract_depth": extract_depth, "format": format}
    if query:
        body["query"] = query
    resp = requests.post(
        f"{TAVILY_API_BASE}/extract",
        json=body,
        headers={"Authorization": f"Bearer {_api_key()}"},
        timeout=config.SEARCH_TIMEOUT,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Tavily extract HTTP {resp.status_code}")
    return resp.json()


class _CachedMixin:
    """TTL cache mixin for tools."""

    def __init__(self):
        self._cache: dict = {}

    def _get_cached(self, key: str):
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() - entry["timestamp"] > CACHE_TTL:
            del self._cache[key]
            return None
        return entry["value"]

    def _set_cache(self, key: str, value):
        if len(self._cache) >= config.WEB_SEARCH_CACHE_SIZE:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = {"value": value, "timestamp": time.time()}


class WebSearchTool(BaseTool, _CachedMixin):
    """Search the web via Tavily API."""

    def __init__(self):
        _CachedMixin.__init__(self)

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Mencari informasi real-time dari web (via Tavily API)."

    @property
    def category(self) -> str:
        return "web"

    @staticmethod
    def _clean_query(query: str) -> str:
        prefixes = [
            "cari di google tentang ", "cari tentang ", "search google for ",
            "search for ", "google ", "browse ", "search ", "cari ", "browsing ",
            "cari di duckduckgo tentang ", "ddg ",
        ]
        result = query.strip()
        while True:
            lower = result.lower()
            best_idx = -1
            best_len = 0
            for prefix in prefixes:
                idx = lower.find(prefix)
                if idx != -1 and (best_idx == -1 or idx < best_idx):
                    best_idx = idx
                    best_len = len(prefix)
            if best_idx == -1:
                break
            result = result[best_idx + best_len:].strip()
        return result

    def execute(self, query: str) -> ToolResult:
        query = self._clean_query(query)
        if not query:
            return ToolResult.fail("Tidak ada query pencarian.", "tavily")

        cache_key = hashlib.md5(query.encode()).hexdigest()
        cached = self._get_cached(cache_key)
        if cached is not None:
            return ToolResult.ok(cached, "tavily")

        try:
            results = with_retry(_search, query, max_retries=1, backoff=1.0)
            self._set_cache(cache_key, {"query": query, "results": results})
            return ToolResult.ok({"query": query, "results": results}, "tavily")
        except Exception:
            return ToolResult.fail(_SEARCH_ERR, "tavily")


class WebExtractTool(BaseTool, _CachedMixin):
    """Extract content from URLs via Tavily Extract API."""

    def __init__(self):
        _CachedMixin.__init__(self)

    @property
    def name(self) -> str:
        return "web_extract"

    @property
    def description(self) -> str:
        return "Mengambil konten dari satu atau lebih URL."

    @property
    def category(self) -> str:
        return "web"

    def _cache_key(self, urls: list[str]) -> str:
        return hashlib.md5(",".join(sorted(urls)).encode()).hexdigest()

    def execute(self, urls_str: str) -> ToolResult:
        urls = [u.strip() for u in urls_str.replace("\n", ",").split(",") if u.strip()]
        if not urls:
            return ToolResult.fail("Tidak ada URL untuk diekstrak.", "tavily")

        cache_key = self._cache_key(urls)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return ToolResult.ok(cached, "tavily")

        try:
            raw = with_retry(extract_urls, urls, extract_depth="basic", format="markdown", max_retries=1, backoff=1.0)
            data = {
                "urls": urls,
                "results": raw.get("results", []),
                "failed_results": raw.get("failed_results", []),
            }
            self._set_cache(cache_key, data)
            return ToolResult.ok(data, "tavily")
        except Exception:
            return ToolResult.fail(_EXTRACT_ERR, "tavily")


class TavilyUsageTool(BaseTool):
    """Check Tavily API quota and account details."""

    @property
    def name(self) -> str:
        return "tavily_usage"

    @property
    def description(self) -> str:
        return "Menampilkan sisa kuota API Tavily dan detail akun."

    @property
    def category(self) -> str:
        return "web"

    def execute(self, _unused: str = "") -> ToolResult:
        try:
            raw = check_usage()
            return ToolResult.ok({"raw": raw}, "tavily")
        except Exception:
            return ToolResult.fail(_USAGE_ERR, "tavily")
