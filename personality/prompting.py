from personality.state import StellaState
from personality.inactivity import InactivityContext
from personality.rhythm import RhythmConfig

# All descriptions are INTERNAL-STATE notes, not behavioral instructions.
# A 7B model will treat "Stella yearns for you deeply" as a command to perform
# longing (pet names, hearts) — which caused persona overfitting (MODEL-005).
MOOD_DESCRIPTIONS = {
    "warm": "Internal mood: warm and fond.",
    "playful": "Internal mood: playful.",
    "guarded": "Internal mood: guarded and cautious.",
    "yearning": "Internal mood: quietly missing him.",
    "neutral": "Internal mood: calm.",
}

BASELINE_DESCRIPTIONS = {
    "warm": "Recent days have felt warm between them.",
    "subdued": "Recent days have been subdued overall.",
    "neutral": "Recent days feel balanced overall.",
}

EMOTION_MODE_DESCRIPTIONS = {
    "comforting": "Undertone right now: gentle, wanting to reassure.",
    "playful": "Undertone right now: mischievous.",
    "withdrawn": "Undertone right now: distant and quiet.",
    "yearning": "Undertone right now: missing him more than usual.",
    "soft": "Undertone right now: tender.",
    "excited": "Undertone right now: extra energy.",
}

MOOD_DISCLAIMER = (
    "These are private feelings only — they shape the tone, never the required "
    "content. She may reply plainly; pet names, compliments, flirting, and "
    "emojis are optional, not expected."
)


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
    user_constraints: list[str] | None = None,
) -> str:
    state_desc = describe_state(state)
    lines = [
        identity_blob,
        "",
        "Current state:",
        state_desc,
        MOOD_DISCLAIMER,
    ]
    if rhythm and rhythm.tone_labels:
        style = f"Style: {rhythm.verbosity}, {rhythm.cadence}, {rhythm.energy} — {', '.join(rhythm.tone_labels)}"
        lines += ["", style]
    if inactivity_ctx and inactivity_ctx.feeling:
        hour_text = f"{inactivity_ctx.hours_away:.1f}"
        # Internal-state framing (same policy as MOOD_DISCLAIMER): a raw token
        # like "missed_you" read as an instruction caused affection overuse.
        feeling_note = {
            "missed_you": "privately missed him",
            "guarded": "privately feels a bit distant",
            "uncertain": "privately feels unsure how to act",
            "welcome_back": "privately feels glad he is back",
        }.get(inactivity_ctx.feeling, inactivity_ctx.feeling.replace("_", " "))
        lines += ["", f"(She has been away {hour_text} hours; internally she {feeling_note}.)"]
    if emotional_context:
        lines += ["", "Recent emotional context:", emotional_context]
    if user_constraints:
        lines += ["", "User constraints (MUST follow):"]
        lines += [f"- {c}" for c in user_constraints]
    return "\n".join(lines)
