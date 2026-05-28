import json
import os
import tempfile
import time
from dataclasses import dataclass, field, asdict
from typing import Any

from utils.logger import log

SALIENCE_THRESHOLD = 0.25
RECURRENCE_WINDOW = 3600


@dataclass
class EmotionalRecord:
    type: str = "interaction"
    content: str = ""
    valence: float = 0.0
    arousal: float = 0.0
    timestamp: float = 0.0
    recurrence: int = 1

    @property
    def salience(self) -> float:
        return abs(self.valence) * self.arousal * (1 + 0.2 * self.recurrence)


class EmotionalMemory:
    def __init__(self, filepath: str = ""):
        self.filepath = filepath or os.path.join("logs", "emotional_memory.json")
        self.records: list[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.records = []

    def _save(self):
        dirpath = os.path.dirname(os.path.abspath(self.filepath))
        os.makedirs(dirpath, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=dirpath,
                prefix=".tmp_", suffix=".json", delete=False
            ) as tmp:
                json.dump(self.records, tmp, ensure_ascii=False, indent=2)
                tmp_path = tmp.name
            os.replace(tmp_path, self.filepath)
        except Exception as exc:
            log.warning("Failed to save emotional memory to %s: %s", self.filepath, exc)

    def record(self, type_: str, content: str, valence: float, arousal: float):
        record = EmotionalRecord(type=type_, content=content, valence=valence, arousal=arousal)
        if record.salience < SALIENCE_THRESHOLD:
            return
        now = time.time()
        for r in self.records:
            if r["type"] == type_ and r["content"] == content and now - r["timestamp"] < RECURRENCE_WINDOW:
                r["recurrence"] += 1
                r["valence"] = valence
                r["arousal"] = arousal
                r["timestamp"] = now
                self._save()
                return
        record.timestamp = now
        self.records.append(record.__dict__)
        self._save()

    def recall_recent(self, n: int = 5) -> list[dict]:
        sorted_records = sorted(self.records, key=lambda r: r["timestamp"], reverse=True)
        return sorted_records[:n]

    def recall_by_valence(self, min_valence: float = 0.0) -> list[dict]:
        return [r for r in self.records if r["valence"] >= min_valence]

    def emotional_summary(self) -> str:
        recent = self.recall_recent(5)
        if not recent:
            return ""
        lines = []
        for r in recent:
            emot = "positif" if r["valence"] > 0.3 else "negatif" if r["valence"] < -0.3 else "netral"
            label = r["content"][:60]
            times = f"(x{r['recurrence']})" if r["recurrence"] > 1 else ""
            lines.append(f"- {label} [{emot}]{times}")
        return "\n".join(lines)

    def clear(self):
        self.records = []
        self._save()
