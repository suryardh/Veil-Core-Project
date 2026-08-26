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
