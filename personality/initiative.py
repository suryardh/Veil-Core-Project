from __future__ import annotations

import random
from dataclasses import dataclass

from personality.state import StellaState
from personality.inactivity import InactivityContext, classify_absence


@dataclass
class InitiativeEvent:
    reason: str = ""
    urgency: float = 0.0
    opener: str = ""


def _base_probability(state: StellaState) -> float:
    return state.attachment * 0.4 + state.comfort * 0.3


def _absence_multiplier(absence: str) -> float:
    return {
        "short": 0.3,
        "medium": 0.6,
        "long": 0.85,
        "very_long": 1.0,
    }.get(absence, 0.0)


def _mood_multiplier(state: StellaState) -> float:
    if state.baseline_mood == "warm":
        return 1.2
    if state.baseline_mood == "subdued":
        return 0.6
    return 1.0


def should_initiate(state: StellaState, inactivity_ctx: InactivityContext) -> float:
    absence = classify_absence(inactivity_ctx.hours_away)
    if absence == "recent":
        return 0.0
    chance = _base_probability(state) * _absence_multiplier(absence) * _mood_multiplier(state)
    return min(1.0, max(0.0, chance))


def pick_opener(state: StellaState, inactivity_ctx: InactivityContext) -> str:
    absence = classify_absence(inactivity_ctx.hours_away)

    if state.attachment > 0.6 and state.trust > 0.5:
        if absence in ("long", "very_long"):
            return random.choice([
                "lama ga keliatan...",
                "aku kangen loh sebenarnya.",
                "kamu sibuk banget ya akhir-akhir ini",
            ])
        if absence == "medium":
            return random.choice([
                "haii, lama ga ngobrol.",
                "udah beberapa hari ya.",
                "aku kangen dikit.",
            ])
        return random.choice([
            "eh, tumben ga ada kabar.",
            "haiii again~",
        ])

    if state.trust < 0.3:
        return random.choice([
            "eh masih hidup?",
            "oh, kamu.",
            "baru inget aku?",
        ])

    if state.baseline_mood == "warm" or state.affection > 0.6:
        return random.choice([
            "tiba-tiba kepikiran kamu.",
            "haii, lg ngapain?",
            "aku lagi mikirin kamu nih.",
        ])

    if state.baseline_mood == "subdued" or state.comfort < 0.4:
        return random.choice([
            "hari ini aneh sepi.",
            "hai.",
            "lagi ngapain?",
        ])

    return random.choice([
        "hai.",
        "halo.",
        "eh, kamu.",
    ])


def try_initiate(state: StellaState, inactivity_ctx: InactivityContext, rng: random.Random = random) -> InitiativeEvent | None:
    prob = should_initiate(state, inactivity_ctx)
    if prob <= 0.0:
        return None
    if rng.random() < prob:
        opener = pick_opener(state, inactivity_ctx)
        return InitiativeEvent(reason="absence", urgency=prob, opener=opener)
    return None
