"""
utils/text.py

Shared text utility functions.
"""
import re

CLEANUP_PATTERNS = [
    (re.compile(r"<\|im_start\|>\s*(?:assistant|user|system)?", re.I), ""),
    (re.compile(r"<\|im_end\|>"), ""),
    (re.compile(r"^\s*(?:assistant|user|system)\s*", re.I), ""),
]

# Verbal-tic suppression: the model imitates its own stored history, so a
# single "Gas," snowballs into every reply. Strip tics before persisting to
# short-term memory to break the reinforcement loop (MODEL-005 finding).
_TIC_TOKENS = ("wkwk", "wkhwk", "haha", "hahaha", "hehe", "gas", "hehehe")
_TIC_LEAD = re.compile(
    r"^\s*(?:(?:\b(?:%s)\b)[,.!~ ]*\s*)+" % "|".join(_TIC_TOKENS), re.I)
_SENTENCE_GAS = re.compile(r"(?<=[.!?]\s)Gas,\s*")
# Pronoun normalization: the model slips into Jakartan "gw/lo" and formal
# "saya" despite rules; these substitutes are safe in every position.
_PRONOUN_FIXES = [
    (re.compile(r"\b(gw|gue|gua)\b", re.I), "aku"),
    (re.compile(r"\b(lo|lu|elo)\b", re.I), "kamu"),
    (re.compile(r"\bsaya\b"), "aku"),
    (re.compile(r"\bSaya\b"), "Aku"),
]
_WRAP_QUOTES = ('"',)
_EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF]\uFE0F?")
_HIKS_RE = re.compile(r"\s*\bhiks+\b\.?", re.I)
_EMOJI_GLUE_RE = re.compile(r"([\U0001F000-\U0001FAFF\u2600-\u27BF])([a-zA-Z])")
_EN_STOPWORDS = {"the", "you", "your", "are", "is", "it's", "i've", "i'm", "did",
                 "and", "of", "to", "that", "what", "have", "has", "was", "will",
                 "should", "tell", "after", "about", "think"}
_ID_MARKERS = {"yang", "dan", "kamu", "aku", "gak", "ga", "nggak", "udah",
               "belum", "itu", "ini", "saya", "apa", "dong", "deh", "nih", "ya"}


def _drop_english_sentences(text: str) -> str:
    """Indonesian-first persona: remove sentences that are mostly English."""
    parts = re.split(r"(?<=[.!?])\s+", text)
    kept = []
    for p in parts:
        words = re.findall(r"[a-z']+", p.lower())
        en_hits = sum(1 for w in words if w in _EN_STOPWORDS)
        id_hits = sum(1 for w in words if w in _ID_MARKERS)
        if len(words) >= 4 and en_hits >= 2 and id_hits == 0:
            continue
        kept.append(p)
    result = " ".join(kept).strip()
    return result if result else text


def _fix_glued_emoji(text: str) -> str:
    return _EMOJI_GLUE_RE.sub(r"\1 \2", text)


def _cap_emojis(text: str, cap: int = 2) -> str:
    found = list(_EMOJI_RE.finditer(text))
    if len(found) <= cap:
        return text
    for m in reversed(found[cap:]):
        text = text[:m.start()] + text[m.end():]
    return re.sub(r" {2,}", " ", text)


def _collapse_gas(text: str) -> str:
    """The model spams 'gas' as a compliance tic — allow one per message."""
    if len(re.findall(r"\bgas\b", text, re.I)) < 2:
        return text
    seen = False
    out = []
    for part in re.split(r"(\bgas\b)", text, flags=re.I):
        if re.fullmatch(r"\bgas\b", part, re.I):
            if seen:
                out.append(" ")
                continue
            seen = True
        out.append(part)
    cleaned = "".join(out)
    cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
    return re.sub(r"( ){2,}", r"\1", cleaned)


def collapse_sayang(text: str) -> str:
    """Pet-name overuse reads as checkbox affection — one per message max."""
    parts = re.split(r"(\bsayang\b)", text)
    if len(parts) <= 3:
        return text
    seen = False
    out = []
    for part in parts:
        if part.lower() == "sayang":
            if seen:
                continue
            seen = True
        out.append(part)
    return re.sub(r"( ){2,}", r"\1", "".join(out)).strip(" ,")


def strip_emojis_from_source(text: str, source_text: str) -> str:
    """Drop emojis the user just sent — echoing them is compliance, not expression."""
    source_emojis = set(_EMOJI_RE.findall(source_text or ""))
    if not source_emojis:
        return text
    return _EMOJI_RE.sub(lambda m: "" if m.group() in source_emojis else m.group(), text).strip()


def _strip_tics(text: str) -> str:
    stripped = _TIC_LEAD.sub("", text.strip())
    stripped = _SENTENCE_GAS.sub("", stripped)
    if not stripped.strip():
        return text
    # Chat replies must open with a capital — the model often drops it.
    for i, ch in enumerate(stripped):
        if ch.isalpha():
            return stripped[:i] + ch.upper() + stripped[i + 1:]
        if not ch.isspace() and ch not in "\"'([*_-":
            break
    return stripped


def _unwrap_quotes(text: str) -> str:
    for q in _WRAP_QUOTES:
        if len(text) > 1 and text.startswith(q) and text.endswith(q):
            return text[1:-1].strip()
    return text


def sanitize_llm_output(text: str) -> str:
    """Clean and sanitize the output from an LLM response."""
    text = text.strip()
    if "<|im_end|>" in text:
        text = text.split("<|im_end|>")[0]
    for pattern, replacement in CLEANUP_PATTERNS:
        text = pattern.sub(replacement, text)
    for pattern, sub in _PRONOUN_FIXES:
        text = pattern.sub(sub, text)
    text = _HIKS_RE.sub("", text)
    text = _collapse_gas(text)
    text = _drop_english_sentences(text)
    return _strip_tics(_unwrap_quotes(_cap_emojis(_fix_glued_emoji(text)))).strip()
