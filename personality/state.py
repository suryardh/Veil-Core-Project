from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StellaIdentity:
    humor: float = 0.6
    warmth: float = 0.9
    teasing: float = 0.6
    emotional_openness: float = 0.8
    protectiveness: float = 0.8

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class StellaState:
    affection: float = 0.7
    trust: float = 0.8
    attachment: float = 0.5
    comfort: float = 0.7
    dependency: float = 0.4
    last_interaction_ts: float = 0.0
    baseline_mood: str = "warm"
    emotional_mode: str = "yearning"
    mode_strength: float = 0.5
    # Conflict dynamics (schema v3 — see personality/conflict.py)
    conflict_severity: float = 0.0
    conflict_ts: float = 0.0
    cooldown_until: float = 0.0
    apology_count: int = 0
    pending_recovery: dict = field(default_factory=dict)
    drift_window: list = field(default_factory=list)

    _decay_rates: dict = field(default_factory=lambda: {
        "affection": 0.998,
        "trust": 0.9995,
        "attachment": 0.999,
        "comfort": 0.997,
        "dependency": 0.998,
    })

    def update_from_interaction(self, emotion: str, intensity: float, confidence: float, damping: float = 1.0):
        if confidence < 0.4:
            return
        if emotion == "positive":
            delta = 0.05 * intensity * damping
            self.affection = min(1.0, self.affection + delta)
            self.trust = min(1.0, self.trust + 0.03 * intensity * damping)
            self.attachment = min(1.0, self.attachment + 0.02 * intensity * damping)
            self.comfort = min(1.0, self.comfort + 0.04 * intensity * damping)
            self.dependency = min(1.0, self.dependency + 0.01 * intensity * damping)
        elif emotion == "intimate":
            delta = 0.08 * intensity * damping
            self.affection = min(1.0, self.affection + delta)
            self.trust = min(1.0, self.trust + 0.05 * intensity * damping)
            self.attachment = min(1.0, self.attachment + 0.06 * intensity * damping)
            self.comfort = min(1.0, self.comfort + 0.07 * intensity * damping)
            self.dependency = min(1.0, self.dependency + 0.03 * intensity * damping)
        elif emotion == "negative":
            delta = 0.06 * intensity
            self.affection = max(0.0, self.affection - delta)
            self.trust = max(0.0, self.trust - 0.08 * intensity)
            self.comfort = max(0.0, self.comfort - 0.05 * intensity)

    def decay(self):
        for dim, rate in self._decay_rates.items():
            val = getattr(self, dim)
            setattr(self, dim, max(0.0, val * rate))

    def stage_label(self) -> str:
        combined = (self.affection + self.trust * 0.8 + self.attachment * 0.6 + self.comfort * 0.4 + self.dependency * 0.3) / 3.1
        if combined < 0.2:
            return "kenalan"
        if combined < 0.4:
            return "akrab"
        if combined < 0.6:
            return "dekat"
        if combined < 0.8:
            return "sayang"
        return "istimewa"

    def dominant_mood(self) -> str:
        if self.affection > 0.6 and self.attachment > 0.4:
            return "yearning"
        if self.affection > 0.7 and self.comfort > 0.7:
            return "warm"
        if self.affection > 0.5 and self.trust > 0.6:
            return "playful"
        if self.comfort < 0.3 or self.trust < 0.3:
            return "guarded"
        return "warm"

    def to_dict(self) -> dict:
        return {
            "affection": self.affection,
            "trust": self.trust,
            "attachment": self.attachment,
            "comfort": self.comfort,
            "dependency": self.dependency,
            "last_interaction_ts": self.last_interaction_ts,
            "baseline_mood": self.baseline_mood,
            "emotional_mode": self.emotional_mode,
            "mode_strength": self.mode_strength,
            "conflict_severity": self.conflict_severity,
            "conflict_ts": self.conflict_ts,
            "cooldown_until": self.cooldown_until,
            "apology_count": self.apology_count,
            "pending_recovery": self.pending_recovery,
            "drift_window": self.drift_window,
        }

    @classmethod
    def from_dict(cls, data: dict) -> StellaState:
        return cls(
            affection=float(data.get("affection", 0.7)),
            trust=float(data.get("trust", 0.8)),
            attachment=float(data.get("attachment", 0.5)),
            comfort=float(data.get("comfort", 0.7)),
            dependency=float(data.get("dependency", 0.4)),
            last_interaction_ts=float(data.get("last_interaction_ts", 0.0)),
            baseline_mood=str(data.get("baseline_mood", "warm")),
            emotional_mode=str(data.get("emotional_mode", "yearning")),
            mode_strength=float(data.get("mode_strength", 0.5)),
            conflict_severity=float(data.get("conflict_severity", 0.0)),
            conflict_ts=float(data.get("conflict_ts", 0.0)),
            cooldown_until=float(data.get("cooldown_until", 0.0)),
            apology_count=int(data.get("apology_count", 0)),
            pending_recovery=dict(data.get("pending_recovery", {}) or {}),
            drift_window=list(data.get("drift_window", []) or []),
        )
