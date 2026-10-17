import re

FRAME_PATTERNS = [
    re.compile(r"^(?:tolong\s+)?(?:ingat|ingatkan|catat|simpan|jangan\s+lupa)\s+(?:kalau|bahwa|ya)\s+", re.I),
    re.compile(r"^(?:tolong\s+)?remember\s+(?:that|to|)\s+", re.I),
    re.compile(r"^(?:tolong\s+)?(?:catat|simpan|note)\s+(?:kalau|bahwa|ya|that)\s+", re.I),
    # "ingat"/"inget" are ambiguous in Indonesian: they mean both "remember
    # (store) this" and "do you recall". Requiring the same particle as line 1
    # ("ya/bahwa/kalau") keeps explicit save commands working while stopping
    # recall questions like "inget ga kemarin kita bahas apa?" from being
    # stored as facts.
    re.compile(r"^ingat(?:kan)?\s+(?:ya|bahwa|kalau)\s*[,:]?\s+", re.I),
    re.compile(r"^inget(?:kan)?\s+(?:ya|bahwa|kalau)\s*[,:]?\s+", re.I),
    re.compile(r"^remember\s+", re.I),
]

# A stored fact is an assertion, not a question. Anything phrased as a question
# is a request to recall, never something worth persisting.
_QUESTION_LEAD = re.compile(
    r"^(apa|apakah|kenapa|mengapa|gimana|bagai\w*|kapan|dimana|di\s*mana|siapa"
    r"|berapa|mana|what|when|where|who|why|how|which"
    r"|do\s+you|did\s+you|can\s+you|remember\s+(?:what|whether|if|how|why))\b",
    re.I,
)
_QUESTION_TAIL = re.compile(r"[?？]\s*$")


def _looks_like_question(text: str) -> bool:
    return bool(_QUESTION_TAIL.search(text) or _QUESTION_LEAD.match(text))

IMPORTANCE_KEYWORDS = {
    4: [
        "nama", "nama panggilan", "umur", "tanggal lahir", "ulang tahun",
        "alamat", "no hp", "telepon", "email", "status",
        "name", "age", "birthday", "address", "phone",
    ],
    3: [
        "pekerjaan", "kesukaan", "favorit", "suka", "cinta", "sayang",
        "hobby", "hobi", "doyan", "gemar", "sering",
        "favorite", "love", "like", "prefer",
    ],
    2: [
        "tidak suka", "ga suka", "benci", "gak suka", "nggak suka",
        "takut", "trauma", "phobia", "alergi",
        "besok", "lusa", "jam", "meeting", "rapat", "janji", "janjian",
        "tanggal", "deadline",
        "tomorrow", "remind", "schedule",
    ],
}

TYPE_KEYWORDS = {
    "personal_info": ["nama", "umur", "alamat", "no hp", "telepon", "email",
                      "tanggal lahir", "ulang tahun", "status", "pekerjaan",
                      "name", "age", "address", "phone", "email", "birthday"],
    "preference": ["suka", "cinta", "sayang", "favorit", "hobby", "hobi",
                   "doyan", "gemar", "sering", "tidak suka", "ga suka", "benci",
                   "like", "love", "favorite", "prefer", "enjoy"],
    "reminder": ["besok", "lusa", "jam", "meeting", "rapat", "janji",
                 "janjian", "tanggal", "deadline", "jangan lupa",
                 "tomorrow", "remind", "schedule", "appointment"],
}


def strip_framing(text: str) -> str:
    for pat in FRAME_PATTERNS:
        text = pat.sub("", text)
    text = re.sub(r"^(?:ya|iya|oke)(?:,|\s)+", "", text, flags=re.I)
    text = re.sub(r"\s*(?:jangan\s+lupa(?: ya| deh)?|ya\s+sih)\s*\.?\s*$", "", text, flags=re.I).strip()
    text = text.strip()
    if text and text[0].isalpha():
        text = text[0].upper() + text[1:]
    return text


def classify_type(text: str) -> str:
    lower = text.lower()
    for ttype, keywords in TYPE_KEYWORDS.items():
        if any(k in lower for k in keywords):
            return ttype
    return "general"


def compute_importance(text: str) -> int:
    lower = text.lower()
    for imp, keywords in IMPORTANCE_KEYWORDS.items():
        if any(k in lower for k in keywords):
            return imp
    word_count = len(text.split())
    if word_count >= 5:
        return 2
    return 1


def extract_fact(text: str) -> dict:
    seeded = any(p.search(text) for p in FRAME_PATTERNS)
    content = strip_framing(text)
    # Reject degenerate or question-shaped content. Previously an input like
    # "inget ya," was persisted verbatim as a fact, because the empty-content
    # branch returned the original text while still reporting seeded=True.
    if not content or _looks_like_question(content):
        return {"type": "general", "content": text, "importance": 1,
                "tags": ["general"], "seeded": False}
    ftype = classify_type(content)
    return {
        "type": ftype,
        "content": content,
        "importance": compute_importance(content),
        "tags": [ftype],
        "seeded": seeded,
    }
