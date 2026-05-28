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
