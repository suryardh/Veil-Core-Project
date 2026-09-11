import re

FRAME_PATTERNS = [
    re.compile(r"^(?:tolong\s+)?(?:ingat|ingatkan|catat|simpan|jangan\s+lupa)\s+(?:kalau|bahwa|ya)\s+", re.I),
    re.compile(r"^(?:tolong\s+)?remember\s+(?:that|to|)\s+", re.I),
    re.compile(r"^(?:tolong\s+)?(?:catat|simpan|note)\s+(?:kalau|bahwa|ya|that)\s+", re.I),
    re.compile(r"^ingat(?:kan)?\s+", re.I),
    re.compile(r"^inget(?:kan)?\s+", re.I),
    re.compile(r"^remember\s+", re.I),
]

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
    if not content:
        return {"type": "general", "content": text, "importance": 1,
                "tags": ["general"], "seeded": seeded}
    ftype = classify_type(content)
    return {
        "type": ftype,
        "content": content,
        "importance": compute_importance(content),
        "tags": [ftype],
        "seeded": seeded,
    }
