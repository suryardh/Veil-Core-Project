import sys
import config
from core.setup import build_agent, register_tools
from core.orchestrator import Orchestrator
from personality.core import PersonalityCore
from utils.logger import log

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    agent = build_agent()
    orch = Orchestrator()
    register_tools(orch)
    core = PersonalityCore(agent, orch)

    log.info("Veil online.")

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


if __name__ == "__main__":
    main()
