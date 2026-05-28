import json
import os
from pathlib import Path
from personality.state import StellaState
from utils.logger import log

DEFAULT_PATH = os.path.join("data", "state.json")
SCHEMA_VERSION = 2

_MIGRATIONS: dict[int, callable] = {}


def _register(v: int):
    def wrapper(fn):
        _MIGRATIONS[v] = fn
        return fn
    return wrapper


@_register(1)
def _migrate_v1_to_v2(raw: dict):
    raw.setdefault("baseline_mood", "neutral")
    raw.setdefault("emotional_mode", "neutral")
    raw.setdefault("mode_strength", 0.0)


def _run_migrations(raw: dict, from_version: int):
    for v in range(from_version, SCHEMA_VERSION):
        fn = _MIGRATIONS.get(v)
        if fn:
            fn(raw)
            log.info("Migrated state from v%d to v%d", v, v + 1)


def save_state(state: StellaState, path: str = DEFAULT_PATH):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": SCHEMA_VERSION,
        "state": state.to_dict(),
    }
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("Failed to save state to %s: %s", path, exc)


def load_state(path: str = DEFAULT_PATH) -> StellaState:
    p = Path(path)
    if not p.exists():
        return StellaState()
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("state", data)
        version = data.get("version", 1)
        if version < SCHEMA_VERSION:
            _run_migrations(raw, version)
        return StellaState.from_dict(raw)
    except Exception as exc:
        log.warning("Failed to load state from %s: %s — using defaults", path, exc)
        return StellaState()
