"""
core/bootstrap.py

Shared bootstrap helpers for app.py and app_tui.py.
Extracted to prevent code duplication.
"""
import sys
import os
import time

import config
from core.agent import VeilAgent
from core.orchestrator import Orchestrator
from personality.core import PersonalityCore
from tools.web.search import WebSearchTool, WebExtractTool, TavilyUsageTool
from tools.system.datetime import DateTimeTool
from tools.system.calculator import CalculatorTool
from utils.logger import log

def _configure_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

def _build_agent() -> VeilAgent:
    if not os.path.exists(config.MODEL_PATH):
        log.error("Model file not found: %s", config.MODEL_PATH)
        log.error("Download Qwen2.5-3B-Instruct Q4_K_M GGUF and place it at %s", config.MODEL_PATH)
        sys.exit(1)
    return VeilAgent(config.MODEL_PATH)

def _register_tools(orch: Orchestrator) -> None:
    orch.register_tool("web_search", WebSearchTool())
    orch.register_tool("web_extract", WebExtractTool())
    orch.register_tool("tavily_usage", TavilyUsageTool())
    orch.register_tool("datetime", DateTimeTool())
    orch.register_tool("calculator", CalculatorTool())

def create_core_components():
    _configure_stdout()
    agent = _build_agent()
    orch = Orchestrator()
    _register_tools(orch)
    core = PersonalityCore(agent, orch)
    return agent, orch, core

def run_cli_app(agent, orch, core):
    log.info("Veil online (CLI).")
    try:
        while True:
            opener = core.initiative_cue()
            if opener:
                print(f"\nStella: {opener}")
            user = input("You: ").strip()
            if not user:
                continue
            if user.lower() in ("exit", "quit"):
                break
            response = core.handle(user)
            print(f"Stella: {response}\n")
    except KeyboardInterrupt:
        print()
        log.info("Shutdown by user.")
    except Exception as e:
        log.exception("Unhandled error: %s", e)

# ponytail: This is a placeholder for the TUI runner.
# It should be defined in app_tui.py and not duplicated here.
# add when Rich Layout logic needs to be shared or app_tui.py becomes too complex.
def run_tui_app(agent, orch, core):
    log.info("Veil online (TUI).")
    # TUI logic will be here, currently in app_tui.py
    # This function should be replaced by importing and calling app_tui.main()
    # or similar, passing agent, orch, core.
    log.warning("run_tui_app is a stub. Please use app_tui.py directly.")
    try:
        # Dummy loop for now
        while True:
            opener = core.initiative_cue()
            if opener:
                print(f"\nStella: {opener}")
            user = input("You (TUI stub): ").strip()
            if not user:
                continue
            if user.lower() in ("exit", "quit"):
                break
            response = core.handle(user)
            print(f"Stella (TUI stub): {response}\n")
    except KeyboardInterrupt:
        print()
        log.info("Shutdown by user.")
    except Exception as e:
        log.exception("Unhandled error: %s", e)
