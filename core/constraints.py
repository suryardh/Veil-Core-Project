"""Conversation intent/constraint detection (TODO MODEL-005 revision).

Turns user feedback/closures into structured flags consumed by the Context
Builder. Unlike emotion state (tone-only), constraints are HARD requirements
for the next reply — the user explicitly expressed them.

Deterministic, no LLM.
"""
import re

_CLOSING_RE = re.compile(
    r"\b(udah\s+dulu|cukup\s+dulu|mau\s+istirahat|mau\s+tidur|ngantuk|"
    r"cabut|pergi\s+dulu|off\s+dulu|udahan|pamit)\b", re.I)

_NO_QUESTIONS_RE = re.compile(
    r"(jangan\s+(nanya|tanya|bertanya)|nggak?\s+usah\s+nanya|malah\s+nanya|"
    r"kebanyakan\s+nanya|nanya\s+mulu|stop\s+asking)", re.I)


def detect_constraints(user_text: str) -> dict:
    """Return structured flags for the next reply only."""
    closing = bool(_CLOSING_RE.search(user_text))
    return {
        "conversation_closing": closing,
        "avoid_topic_expansion": closing,
        "avoid_questions": bool(_NO_QUESTIONS_RE.search(user_text)) or closing,
    }


def render_constraints(constraints: dict | None) -> list[str]:
    """Render flags as hard directives for the prompt (empty if none)."""
    if not constraints:
        return []
    out = []
    if constraints.get("conversation_closing"):
        out.append(
            "User is ending the conversation. Reply with ONE short warm "
            "sentence. No questions, no new topics, no invitations to chat again.")
    else:
        if constraints.get("avoid_questions"):
            out.append(
                "User just complained about being asked too many questions. "
                "Do NOT ask anything in this reply — acknowledge and adjust.")
        if constraints.get("avoid_topic_expansion"):
            out.append("Do not introduce or expand any topic.")
    return out


# Flags that persist a few turns after the triggering complaint.
_PERSISTENT_FLAGS = {"avoid_questions", "avoid_topic_expansion"}


class ConversationConstraints:
    """Session-scoped constraint store with per-flag TTL (in turns).

    A complaint like 'jangan nanya mulu' keeps avoid_questions active for the
    next `ttl` replies even if the user never repeats it. Momentary flags
    (closing) are never persisted.
    """

    def __init__(self, ttl: int = 2):
        self.ttl = ttl
        self._flags: dict[str, int] = {}

    def observe(self, user_text: str) -> dict:
        """Merge fresh detection into the store; return currently active flags."""
        fresh = detect_constraints(user_text)
        for key in _PERSISTENT_FLAGS:
            if fresh.get(key):
                self._flags[key] = max(self._flags.get(key, 0), self.ttl)
        active = self.active()
        # Momentary flags pass through without persistence.
        for key, value in fresh.items():
            if key not in _PERSISTENT_FLAGS:
                active[key] = value
        return active

    def tick(self) -> None:
        """Call after each consumed reply."""
        self._flags = {k: v - 1 for k, v in self._flags.items() if v - 1 > 0}

    def active(self) -> dict:
        return {k: True for k, v in self._flags.items() if v > 0}
