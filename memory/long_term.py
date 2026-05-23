import time

import config
from memory.store import JSONStore

IMPORTANCE_KEYWORDS = {
    3: [
        "nama",
        "nama panggilan",
        "umur",
        "tanggal lahir",
        "ulang tahun",
        "pekerjaan",
        "kesukaan",
        "favorit",
        "suka",
        "cinta",
        "sayang",
        "alamat",
        "no hp",
        "telepon",
        "email",
        "status",
    ],
    2: [
        "tidak suka",
        "ga suka",
        "benci",
        "gak suka",
        "nggak suka",
        "takut",
        "trauma",
        "phobia",
        "alergi",
    ],
}


def _compute_importance(text: str) -> int:
    lower = text.lower()
    for imp, keywords in IMPORTANCE_KEYWORDS.items():
        if any(k in lower for k in keywords):
            return imp
    return 1


class LongTermMemory:
    MAX_FACTS = 500
    MAX_INJECT = 10

    def __init__(self, filepath=None):
        path = filepath or config.LONG_TERM_MEMORY_PATH
        self.store = JSONStore(path)
        if self.store.get("facts") is None:
            self.store.set("facts", [])

    def remember(self, category: str, content: str):
        fact_text = content
        for prefix in [
            "ingat kalau ",
            "ingat bahwa ",
            "ingat ",
            "remember that ",
            "remember ",
        ]:
            if fact_text.lower().startswith(prefix):
                fact_text = fact_text[len(prefix) :]
                break
        if fact_text:
            fact_text = fact_text[0].upper() + fact_text[1:]
        facts = self.store.get("facts", [])
        if not any(f["content"].lower() == fact_text.lower() for f in facts):
            importance = _compute_importance(fact_text)
            facts.append(
                {
                    "category": category,
                    "content": fact_text,
                    "importance": importance,
                    "timestamp": time.time(),
                }
            )

            # Cap total stored facts
            if len(facts) > self.MAX_FACTS:
                facts = sorted(facts, key=lambda f: f["timestamp"], reverse=True)[
                    : self.MAX_FACTS
                ]
            self.store.set("facts", facts)

    def get_relevant_facts(self, query: str = None) -> str:
        facts = self.store.get("facts", [])
        if not facts:
            return "No long-term memories saved yet."
        candidates = facts
        if query:
            query_words = [w.lower() for w in query.split() if len(w) > 2]
            if query_words:
                candidates = [
                    f
                    for f in facts
                    if any(w in f["content"].lower() for w in query_words)
                ]
        if not candidates:
            candidates = facts[-5:]

        # Sort by importance desc, then by recency desc
        candidates = sorted(
            candidates,
            key=lambda f: (f.get("importance", 1), f.get("timestamp", 0)),
            reverse=True,
        )[: self.MAX_INJECT]

        lines = []
        for fact in candidates:
            lines.append(f"- {fact['content']}")
        return "\n".join(lines)
