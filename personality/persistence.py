import json
import os
from pathlib import Path
from personality.state import StellaState

DEFAULT_PATH = os.path.join("data", "state.json")
SCHEMA_VERSION = 2


def save_state(state: StellaState, path: str = DEFAULT_PATH):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": SCHEMA_VERSION,
        "state": state.to_dict(),
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_state(path: str = DEFAULT_PATH) -> StellaState:
    p = Path(path)
    if not p.exists():
        return StellaState()
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("state", data)
        version = data.get("version", 1)
        if version < 2:
            raw.setdefault("baseline_mood", "neutral")
        return StellaState.from_dict(raw)
    except Exception:
        return StellaState()
