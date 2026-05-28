import config

IGNORE_MESSAGES = {"ok", "wkwk", "wkwkwk", "iya", "iyaa", "y", "ya", "yes",
                   "hmm", "hm", "oh", "owh", "nah", "ga", "gak", "nggak",
                   "lol", "lmao", "w", "e", "ah", "eh", "huh", "gas"}

MAX_MESSAGE_CHARS = 500


class ShortTermMemory:
    """
    ShortTermMemory holds recent conversation messages in-memory.
    """
    def __init__(self, limit=None):
        self.history = []
        self.limit = limit or config.SHORT_TERM_MEMORY_LIMIT

    def add_message(self, role: str, content: str):
        content = content.strip()
        if not content:
            return
        if content.lower() in IGNORE_MESSAGES:
            return
        if len(content) > MAX_MESSAGE_CHARS:
            content = content[:MAX_MESSAGE_CHARS] + "..."

        self.history.append({"role": role, "content": content})
        if len(self.history) > self.limit * 2:
            self.history = self.history[-self.limit * 2:]

    def clear(self):
        self.history = []
