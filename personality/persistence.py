import os
from personality.state import StellaState
from memory.store import JSONStore
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
    store = JSONStore(path)
    data = {
        "version": SCHEMA_VERSION,
        "state": state.to_dict(),
    }
    store.data = data
    store._save()

def load_state(path: str = DEFAULT_PATH) -> StellaState:
    store = JSONStore(path)
    if not store.data:
        return StellaState()

    data = store.data
    raw = data.get("state", data)
    version = data.get("version", 1)
    if version < SCHEMA_VERSION:
        _run_migrations(raw, version)
    return StellaState.from_dict(raw)
