from __future__ import annotations

from dataclasses import dataclass
from personality.state import StellaState


@dataclass
class InactivityContext:
    hours_away: float = 0.0
    feeling: str = ""
    opener: str | None = None
    temporary_mood: str | None = None


def classify_absence(hours: float) -> str:
    if hours < 6:
        return "recent"
    if hours < 24:
        return "short"
    if hours < 72:
        return "medium"
    if hours < 168:
        return "long"
    return "very_long"


@dataclass
class InactivityEffect:
    hours_away: float = 0.0
    severity: str = "short"
    mood_shift: str | None = None
    trust_delta: float = 0.0
    attachment_delta: float = 0.0
    initiative_multiplier: float = 1.0


SEVERITY_MULT = {
    "recent": 0.0,
    "short": 0.0,
    "medium": 0.5,
    "long": 0.8,
    "very_long": 1.0,
}

MAX_DELTA = 0.03


def _branch_effect(absence: str, state: StellaState) -> tuple[str | None, float, float, float]:
    base = SEVERITY_MULT.get(absence, 0.0)

    if state.attachment > 0.6 and state.trust > 0.5:
        return ("yearning", 0.0, MAX_DELTA * base, 1.3)

    if state.attachment > 0.6 and state.trust <= 0.5:
        return ("withdrawn", -MAX_DELTA * base, 0.0, 0.6)

    if state.trust > 0.5:
        mood = "soft" if absence in ("medium", "long") else None
        return (mood, 0.0, MAX_DELTA * 0.5 * base, 1.1)

    mood = "withdrawn" if absence in ("long", "very_long") else None
    return (mood, -MAX_DELTA * 0.5 * base, 0.0, 0.8)


def compute_inactivity_effect(state: StellaState, now: float) -> InactivityEffect:
    if state.last_interaction_ts <= 0:
        return InactivityEffect()

    hours = (now - state.last_interaction_ts) / 3600
    absence = classify_absence(hours)
    if absence == "recent":
        return InactivityEffect(hours_away=hours, severity="short")

    mood_shift, trust_delta, attachment_delta, initiative_mult = _branch_effect(absence, state)
    return InactivityEffect(
        hours_away=hours,
        severity=absence,
        mood_shift=mood_shift,
        trust_delta=round(trust_delta, 4),
        attachment_delta=round(attachment_delta, 4),
        initiative_multiplier=initiative_mult,
    )


def compute_inactivity_context(state: StellaState, now: float) -> InactivityContext:
    if state.last_interaction_ts <= 0:
        return InactivityContext()

    hours = (now - state.last_interaction_ts) / 3600
    ctx = InactivityContext(hours_away=hours)
    absence = classify_absence(hours)

    if absence == "recent":
        return ctx

    if state.attachment > 0.6 and state.trust > 0.5:
        ctx.feeling = "missed_you"
        ctx.temporary_mood = "longing"
        if absence in ("medium", "long"):
            ctx.opener = "missed_you"
    elif state.trust < 0.3:
        ctx.feeling = "guarded"
        ctx.temporary_mood = "guarded"
    elif state.comfort < 0.4:
        ctx.feeling = "uncertain"
        ctx.temporary_mood = "neutral"
    else:
        ctx.feeling = "welcome_back"
        if absence in ("medium", "long", "very_long"):
            ctx.opener = "welcome_back"

    return ctx
