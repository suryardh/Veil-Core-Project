from personality.state import StellaState, StellaIdentity
from personality.inactivity import InactivityContext

MOOD_DESCRIPTIONS = {
    "warm": "Stella feels warm and affectionate right now.",
    "playful": "Stella is in a playful, teasing mood.",
    "guarded": "Stella feels a bit guarded and cautious.",
    "yearning": "Stella feels a deep sense of longing.",
    "neutral": "Stella is calm and open.",
}


def describe_state(state: StellaState) -> str:
    parts = []
    mood_text = MOOD_DESCRIPTIONS.get(state.dominant_mood(), MOOD_DESCRIPTIONS["neutral"])
    parts.append(mood_text)
    stage = state.stage_label()
    parts.append(f"You are at the '{stage}' stage.")
    return " ".join(parts)


def build_prompt(
    identity_blob: str,
    state: StellaState,
    emotional_context: str,
    user_input: str,
    cognition_context: str = "",
    inactivity_ctx: InactivityContext | None = None,
) -> str:
    state_desc = describe_state(state)
    lines = [
        identity_blob,
        "",
        "Current state:",
        state_desc,
    ]
    if inactivity_ctx and inactivity_ctx.feeling:
        hour_text = f"{inactivity_ctx.hours_away:.1f}"
        lines += ["", f"Stella notices the user has been away for {hour_text} hours and feels {inactivity_ctx.feeling}."]
    if emotional_context:
        lines += ["", "Recent emotional context:", emotional_context]
    if cognition_context:
        lines += ["", "Relevant factual context:", cognition_context]
    lines += ["", "User:", user_input, "", "Stella:"]
    return "\n".join(lines)
