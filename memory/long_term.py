import time

import config
from memory.store import JSONStore


class LongTermMemory:
    MAX_FACTS = 500
    MAX_INJECT = 10

    def __init__(self, filepath=None):
        path = filepath or config.LONG_TERM_MEMORY_PATH
        self.store = JSONStore(path)
        if self.store.get("facts") is None:
            self.store.set("facts", [])

    def remember(self, category: str, content: str, importance: int = 1):
        if not content:
            return
        facts = self.store.get("facts", [])
        if not any(f["content"].lower() == content.lower() for f in facts):
            facts.append(
                {
                    "type": category,
                    "category": category,
                    "content": content,
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

        # Inisialisasi dulu agar closure _score() tidak UnboundLocalError
        # jika semua kata dalam query ≤2 karakter
        query_words: list[str] = []
        if query:
            query_words = [w.lower() for w in query.split() if len(w) > 2]

        def _score(fact: dict) -> float:
            if not query or not query_words:
                return fact.get("importance", 1) / 5.0
            content = fact["content"].lower()
            matches = sum(1 for w in query_words if w in content)
            match_ratio = matches / max(len(query_words), 1)
            imp_norm = fact.get("importance", 1) / 5.0
            return match_ratio * 0.7 + imp_norm * 0.3

        scored = sorted(facts, key=_score, reverse=True)
        top = scored[:10]

        lines = []
        for fact in top:
            lines.append(f"- {fact['content']}")
        return "\n".join(lines)
