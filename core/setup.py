"""
core/setup.py

Shared bootstrap helpers untuk app.py dan app_tui.py.
Diekstrak untuk mencegah duplikasi kode (BUG-MN1).
"""
import os
import sys

import config
from core.agent import VeilAgent
from core.orchestrator import Orchestrator
from tools.web.search import WebSearchTool, WebExtractTool, TavilyUsageTool
from tools.system.datetime import DateTimeTool
from tools.system.calculator import CalculatorTool
from utils.logger import log


def build_agent() -> VeilAgent:
    if not os.path.exists(config.MODEL_PATH):
        log.error("Model file not found: %s", config.MODEL_PATH)
        log.error("Download Qwen2.5-3B-Instruct Q4_K_M GGUF and place it at %s", config.MODEL_PATH)
        sys.exit(1)
    return VeilAgent(config.MODEL_PATH)


def register_tools(orch: Orchestrator) -> None:
    orch.register_tool("web_search", WebSearchTool())
    orch.register_tool("web_extract", WebExtractTool())
    orch.register_tool("tavily_usage", TavilyUsageTool())
    orch.register_tool("datetime", DateTimeTool())
    orch.register_tool("calculator", CalculatorTool())
