import sys
import config
from core.agent import VeilAgent
from core.orchestrator import Orchestrator
from tools.web.search import WebSearchTool, WebExtractTool, TavilyUsageTool
from tools.system.datetime import DateTimeTool
from tools.system.calculator import CalculatorTool
from utils.logger import log

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def build_agent():
    return VeilAgent(config.MODEL_PATH)


def register_tools(orch):
    orch.register_tool("web_search", WebSearchTool())
    orch.register_tool("web_extract", WebExtractTool())
    orch.register_tool("tavily_usage", TavilyUsageTool())
    orch.register_tool("datetime", DateTimeTool())
    orch.register_tool("calculator", CalculatorTool())


def main():
    agent = build_agent()
    orch = Orchestrator(agent)
    register_tools(orch)

    log.info("Veil online.")

    try:
        while True:
            user = input("You: ")
            if user.lower() in ("exit", "quit"):
                break
            response = orch.handle(user)
            print(f"Stella: {response}\n")
    except KeyboardInterrupt:
        print()
        log.info("Shutdown by user.")
    except Exception as e:
        log.exception("Unhandled error: %s", e)


if __name__ == "__main__":
    main()
