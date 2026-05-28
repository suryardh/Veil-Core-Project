import sys

import config
from core.setup import build_agent, register_tools
from core.orchestrator import Orchestrator
from personality.core import PersonalityCore
from utils.logger import log

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.align import Align

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def _state_text(state) -> str:
    mood = state.dominant_mood()
    mode = state.emotional_mode if state.mode_strength > 0.15 else ""
    parts = [f"mood: {mood}", f"trust: {state.trust:.2f}", f"attachment: {state.attachment:.2f}"]
    if mode:
        parts.insert(1, f"mode: {mode}")
    return "  |  ".join(parts)


def _mood_color(state) -> str:
    if state.baseline_mood == "warm":
        return "bright_magenta"
    if state.baseline_mood == "subdued":
        return "blue"
    return "cyan"


def main():
    agent = build_agent()
    orch = Orchestrator()
    register_tools(orch)
    core = PersonalityCore(agent, orch)

    history: list[tuple[str, str]] = []

    # Buat layout sekali di luar loop — hanya update konten per turn (BUG-MN2 fix)
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
    )

    try:
        while True:
            opener = core.initiative_cue()
            if opener:
                history.append(("Stella", opener))

            color = _mood_color(core.state)
            header_text = Text()
            header_text.append(" Veil — ", style="bold white")
            header_text.append(core.state.stage_label(), style=f"bold {color}")
            header_text.append(f"\n {_state_text(core.state)}", style="dim white")
            layout["header"].update(Panel(Align.center(header_text), style=color))

            body = Text()
            for speaker, msg in history[-20:]:
                if speaker == "Stella":
                    body.append(f"\n Stella: ", style="bold cyan")
                    body.append(msg, style="cyan")
                else:
                    body.append(f"\n You: ", style="bold green")
                    body.append(msg, style="green")
            layout["body"].update(Panel(body, title="Percakapan"))

            console.clear()
            console.print(layout)

            raw = Prompt.ask("\n[bold green]>[/bold green]")
            user = raw.strip()
            if not user:
                continue
            if user.lower() in ("exit", "quit"):
                break

            history.append(("User", user))
            response = core.handle(user)
            history.append(("Stella", response))

    except KeyboardInterrupt:
        print()
        log.info("Shutdown by user.")
    except Exception as e:
        log.exception("Unhandled error: %s", e)


if __name__ == "__main__":
    main()
