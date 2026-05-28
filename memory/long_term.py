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

        # Take top 5 by importance desc, then top 5 by recency from remaining
        by_importance = sorted(
            candidates,
            key=lambda f: (f.get("importance", 1), f.get("timestamp", 0)),
            reverse=True,
        )[:5]
        by_recency = sorted(candidates, key=lambda f: f.get("timestamp", 0), reverse=True)
        used_ids = {id(f) for f in by_importance}
        fill = [f for f in by_recency if id(f) not in used_ids][:5]
        candidates = by_importance + fill

        lines = []
        for fact in candidates:
            lines.append(f"- {fact['content']}")
        return "\n".join(lines)
