from personality.state import StellaState
from personality.inactivity import InactivityContext
from personality.rhythm import RhythmConfig

MOOD_DESCRIPTIONS = {
    "warm": "Stella feels warm and affectionate toward you.",
    "playful": "Stella is in a playful, flirty mood.",
    "guarded": "Stella feels a bit guarded and cautious.",
    "yearning": "Stella feels a deep longing for you.",
    "neutral": "Stella is calm and open.",
}

BASELINE_DESCRIPTIONS = {
    "warm": "Her feelings for you have been warm and affectionate lately.",
    "subdued": "Overall, her mood has been subdued and quiet recently.",
    "neutral": "Overall, her emotional state is balanced.",
}

EMOTION_MODE_DESCRIPTIONS = {
    "comforting": "Stella wants to comfort you tenderly.",
    "playful": "Stella is feeling playful and flirty.",
    "withdrawn": "Stella is withdrawn and quiet.",
    "yearning": "Stella yearns for you deeply.",
    "soft": "Stella feels soft and tender toward you.",
    "excited": "Stella is excited to be with you.",
}


def describe_state(state: StellaState) -> str:
    parts = []
    mood_text = MOOD_DESCRIPTIONS.get(state.dominant_mood(), MOOD_DESCRIPTIONS["neutral"])
    parts.append(mood_text)
    base_text = BASELINE_DESCRIPTIONS.get(state.baseline_mood)
    if base_text:
        parts.append(base_text)
    if state.mode_strength > 0.15 and state.emotional_mode != "neutral":
        mode_text = EMOTION_MODE_DESCRIPTIONS.get(state.emotional_mode)
        if mode_text:
            parts.append(mode_text)
    return " ".join(parts)


def build_prompt(
    identity_blob: str,
    state: StellaState,
    emotional_context: str,
    inactivity_ctx: InactivityContext | None = None,
    rhythm: RhythmConfig | None = None,
) -> str:
    state_desc = describe_state(state)
    lines = [
        identity_blob,
        "",
        "Current state:",
        state_desc,
    ]
    if rhythm and rhythm.tone_labels:
        style = f"Style: {rhythm.verbosity}, {rhythm.cadence}, {rhythm.energy} — {', '.join(rhythm.tone_labels)}"
        lines += ["", style]
    if inactivity_ctx and inactivity_ctx.feeling:
        hour_text = f"{inactivity_ctx.hours_away:.1f}"
        lines += ["", f"Stella notices the user has been away for {hour_text} hours and feels {inactivity_ctx.feeling}."]
    if emotional_context:
        lines += ["", "Recent emotional context:", emotional_context]
    return "\n".join(lines)
