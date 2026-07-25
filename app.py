import sys
import config
from core.bootstrap import create_core_components, run_cli_app
from utils.logger import log

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def main():
    agent, orch, core = create_core_components()
    run_cli_app(agent, orch, core)

if __name__ == "__main__":
    main()