"""Conversation intent/constraint detection (TODO MODEL-005 revision).

Turns user feedback/closures into structured flags consumed by the Context
Builder. Unlike emotion state (tone-only), constraints are HARD requirements
for the next reply — the user explicitly expressed them, or Stella's own
recent behavior triggered a guardrail (question-spam, repeat echo).

Deterministic, no LLM.
"""
import re

from core.evaluator import _tokens, asks_question, distinctive_words

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
        if constraints.get("avoid_questions") and not constraints.get("question_quota"):
            out.append(
                "User just complained about being asked too many questions. "
                "Do NOT ask anything in this reply — acknowledge and adjust.")
        if constraints.get("question_quota"):
            out.append(
                "Your last replies kept asking questions. This reply must NOT "
                "ask a question — react to what they said, continue the topic, "
                "or share something instead.")
        if constraints.get("repeat_echo"):
            out.append(
                "The user's message repeats what they already sent this "
                "conversation, and your previous reply already addressed it. "
                "Do NOT restate or paraphrase your earlier reply. Give a "
                "short, clearly DIFFERENT reply — a tease, a callback, or "
                "mild annoyance — and quote nothing from your last message.")
        if constraints.get("avoid_topic_expansion"):
            out.append("Do not introduce or expand any topic.")
    return out


# Flags that persist a few turns after the triggering complaint.
_PERSISTENT_FLAGS = {"avoid_questions", "avoid_topic_expansion"}


def _near_duplicate(a: str, b: str) -> bool:
    """True when two user turns carry essentially the same content.

    Jaccard overlap on distinctive tokens. A strict threshold so a normal
    follow-up that reuses a topic word doesn't trip it — only "he sent the
    same message again" (MODEL-011: upgrading from a re-confirm repeat).
    """
    sa = set(distinctive_words(a, min_len=5))
    sb = set(distinctive_words(b, min_len=5))
    if not sa or not sb:
        return False
    union = sa | sb
    return len(sa & sb) / len(union) >= 0.75


class ConversationConstraints:
    """Session-scoped constraint store with per-flag TTL (in turns).

    A complaint like 'jangan nanya mulu' keeps avoid_questions active for the
    next `ttl` replies even if the user never repeats it. Momentary flags
    (closing) are never persisted.
    """

    def __init__(self, ttl: int = 2):
        self.ttl = ttl
        self._flags: dict[str, int] = {}
        self._last_user_text = ""
        self._question_streak = 0

    def observe(self, user_text: str) -> dict:
        """Merge fresh detection into the store; return currently active flags."""
        fresh = detect_constraints(user_text)
        # MODEL-011: message repeated verbatim-ish -> don't re-confirm/restate.
        if self._last_user_text and _near_duplicate(self._last_user_text, user_text):
            fresh["repeat_echo"] = True
        self._last_user_text = user_text
        for key in _PERSISTENT_FLAGS:
            if fresh.get(key):
                self._flags[key] = max(self._flags.get(key, 0), self.ttl)
        active = self.active()
        # MODEL-011b: 2+ question-replies in a row -> next reply must not ask.
        if self._question_streak >= 2:
            active["avoid_questions"] = True
            active["question_quota"] = True
        # Momentary flags pass through without persistence.
        for key, value in fresh.items():
            if key not in _PERSISTENT_FLAGS:
                active[key] = value
        return active

    def note_reply(self, reply: str) -> None:
        """Feed back Stella's own reply so the question-spam quota is self-enforcing."""
        if asks_question(reply):
            self._question_streak += 1
        else:
            self._question_streak = 0

    def tick(self) -> None:
        """Call after each consumed reply."""
        self._flags = {k: v - 1 for k, v in self._flags.items() if v - 1 > 0}

    def active(self) -> dict:
        return {k: True for k, v in self._flags.items() if v > 0}
