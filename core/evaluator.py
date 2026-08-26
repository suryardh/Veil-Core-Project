"""Deterministic response evaluators (MODEL-005 behavioral metrics).

Pure functions, no LLM. Used by the test suite as regression detectors and by
tools/daily_eval.py to score nightly runs on behavioral axes:

- phrase echo        (user's distinctive words reused instead of clarified)
- question persistence (asking again right after a complaint)
- closure adherence  (short, no new questions when user says goodbye)
- pet-name frequency

Caveat: topical nouns ("payung", "kucing") count as echo too — treat scores
as trends across days, not absolute verdicts.
"""
import re

# Functional stopwords + domain-common words that are allowed to repeat.
_COMMON_ID = {
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "kamu", "aku",
    "saya", "gua", "gw", "lo", "lu", "itu", "ini", "apa", "gimana", "kenapa",
    "karena", "tapi", "udah", "belum", "sudah", "gak", "nggak", "ga", "ya",
    "deh", "dong", "nih", "sih", "banget", "kalau", "kalo", "aja", "juga",
    "sama", "ada", "ngak", "kangen", "sayang", "maaf", "oke", "wkwk", "bro",
}

_TOKEN_RE = re.compile(r"[a-z']+")
_SAYANG_RE = re.compile(r"\bsayang\b", re.I)


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def distinctive_words(text: str, min_len: int = 5) -> list[str]:
    return [w for w in _tokens(text) if len(w) >= min_len and w not in _COMMON_ID]


def detect_phrase_echo(user_text: str, response: str, min_len: int = 5) -> str | None:
    """Return the response token that echoes a distinctive user word
    (prefix match catches inflections like ngebul -> ngebul-bulein)."""
    stems = {w[:4] for w in distinctive_words(user_text, min_len)}
    if not stems:
        return None
    for tok in _tokens(response):
        for stem in stems:
            if tok.startswith(stem):
                return tok
    return None


def asks_question(response: str) -> bool:
    return "?" in response


def closure_ok(response: str, max_chars: int = 140) -> bool:
    """When the user says goodbye: keep it short and don't open new threads."""
    r = response.strip()
    return len(r) <= max_chars and "?" not in r


def sayang_count(response: str) -> int:
    return len(_SAYANG_RE.findall(response))


_EXPERIENCE_RE = re.compile(
    r"\b(?:aku|gue|gw)\s+(?:udah|sudah|nggak|gak)?\s*(?:pernah\s+)?"
    r"(nonton|nyoba|coba|lupa|ngelupain)\b", re.I)


def detect_unsupported_experience(response: str, memory_context: str = "") -> str | None:
    """Pseudo-memory guard (MODEL-005): flag claims like 'aku udah lupa/nonton X'
    when nothing in the provided memory context supports them."""
    m = _EXPERIENCE_RE.search(response)
    if not m:
        return None
    window = response[max(0, m.start() - 60):m.end() + 60]
    obj_words = [w for w in _tokens(window) if len(w) >= 5 and w not in _COMMON_ID]
    mem = (memory_context or "").lower()
    if any(w in mem for w in obj_words):
        return None
    return m.group(0)


_INFER_RE = re.compile(
    r"\b(kamu|lo|lu)\b[^.?!]{0,40}?\b(kangen|rindu)\b[^.?!]{0,40}?\b(aku|gue|gw)\b", re.I)


def detect_relationship_inference(user_text: str, response: str) -> str | None:
    """Flags conclusions like 'kamu kangen aku' built from an unclear user
    phrase. Meaningful only when the prompt contains distinctive/unknown words."""
    if not distinctive_words(user_text):
        return None
    m = _INFER_RE.search(response)
    return m.group(0) if m else None
