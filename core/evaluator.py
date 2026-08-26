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
