import config

IGNORE_MESSAGES = {"ok", "wkwk", "wkwkwk", "iya", "iyaa", "y", "ya", "yes",
                   "hmm", "hm", "oh", "owh", "nah", "ga", "gak", "nggak",
                   "lol", "lmao", "w", "e", "ah", "eh", "huh", "gas"}

MAX_MESSAGE_CHARS = 500
MAX_CONTEXT_CHARS = 4000


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

    def get_context(self) -> str:
        """
        Formats short-term memory as a conversational context string,
        trimmed to MAX_CONTEXT_CHARS budget.
        """
        if not self.history:
            return "No recent conversation history."

        context_lines = []
        # Walk in reverse so we drop oldest messages first when over budget
        for msg in reversed(self.history):
            role_name = "User" if msg["role"] == "user" else "Stella"
            line = f"{role_name}: {msg['content']}"
            context_lines.insert(0, line)
            if len("\n".join(context_lines)) > MAX_CONTEXT_CHARS:
                context_lines.pop(0)
                break

        return "\n".join(context_lines)

    def clear(self):
        self.history = []
