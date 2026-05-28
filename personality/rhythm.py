from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from personality.state import StellaState
from personality.analyzer import EmotionAnalysis

REACTION_COOLDOWN = 120


@dataclass
class ReactionResult:
    text: str = ""
    consume_turn: bool = True


@dataclass
class RhythmConfig:
    verbosity: str = "normal"
    cadence: str = "normal"
    energy: str = "normal"
    tone_labels: list[str] = field(default_factory=list)


def _apply_mode_modulation(config: RhythmConfig, state: StellaState) -> RhythmConfig:
    if state.mode_strength <= 0.3 or state.emotional_mode == "neutral":
        return config
    mods = {
        "comforting": {"energy": "low", "cadence": "flowing"},
        "withdrawn": {"verbosity": "short", "energy": "low"},
        "excited": {"energy": "high"},
        "yearning": {"cadence": "hesitant", "energy": "low"},
    }
    override = mods.get(state.emotional_mode)
    if override is None:
        return config
    return RhythmConfig(
        verbosity=override.get("verbosity", config.verbosity),
        cadence=override.get("cadence", config.cadence),
        energy=override.get("energy", config.energy),
        tone_labels=config.tone_labels,
    )


def compute_rhythm(state: StellaState, analysis: EmotionAnalysis) -> RhythmConfig:
    dominant = state.dominant_mood()

    if dominant == "guarded":
        return _apply_mode_modulation(RhythmConfig(verbosity="short", cadence="hesitant", energy="low", tone_labels=["guarded", "short"]), state)

    if analysis.arousal > 0.7:
        return _apply_mode_modulation(RhythmConfig(verbosity="normal", cadence="flowing", energy="high", tone_labels=["reactive"]), state)

    if state.baseline_mood == "warm" and state.affection > 0.5:
        return _apply_mode_modulation(RhythmConfig(verbosity="elaborate", cadence="flowing", energy="high", tone_labels=["warm", "expressive"]), state)

    if state.baseline_mood == "subdued":
        return _apply_mode_modulation(RhythmConfig(verbosity="short", cadence="hesitant", energy="low", tone_labels=["subdued", "quiet"]), state)

    if analysis.confidence < 0.3:
        return _apply_mode_modulation(RhythmConfig(verbosity="short", cadence="normal", energy="low", tone_labels=["short"]), state)

    if state.baseline_mood == "warm":
        return _apply_mode_modulation(RhythmConfig(verbosity="normal", cadence="flowing", energy="normal", tone_labels=["warm"]), state)

    return _apply_mode_modulation(RhythmConfig(), state)


REACTION_TEMPLATES: dict[str, list[str]] = {
    "amused": ["wkwk", "AKWKWK", "haha", "😂"],
    "touched": ["ya ampun", "ih 😭", "🥺", "😳"],
    "pensive": ["hmm...", "ya...", "hmm iya juga"],
    "playful": ["ih serius?", "🙄", "yahaha"],
    "subdued": ["...", "ya udah", "oh"],
}


def try_reaction(state: StellaState, analysis: EmotionAnalysis, last_reaction_ts: float, rng: random.Random = random, now: float | None = None) -> ReactionResult | None:
    now = now or time.time()
    if now - last_reaction_ts < REACTION_COOLDOWN:
        return None

    prob = max(0.05, state.comfort * 0.3)
    if rng.random() >= prob:
        return None

    if analysis.valence > 0.5 and analysis.arousal > 0.6:
        category = rng.choice(["amused", "touched"])
    elif analysis.valence < -0.3 and analysis.arousal > 0.5:
        category = rng.choice(["pensive", "subdued"])
    elif analysis.arousal > 0.5 and analysis.confidence > 0.5:
        category = "playful"
    else:
        return None

    templates = REACTION_TEMPLATES.get(category, [])
    if not templates:
        return None

    return ReactionResult(text=rng.choice(templates), consume_turn=True)
