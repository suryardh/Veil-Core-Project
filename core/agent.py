from llm.engine import LLMEngine
from memory.long_term import LongTermMemory
from memory.short_term import ShortTermMemory
from personality.stella import StellaPersonality


class VeilAgent:
    def __init__(self, model_path, mode="casual"):
        self.llm = LLMEngine(model_path)
        self.mode = mode
        self.short_memory = ShortTermMemory()
        self.long_memory = LongTermMemory()

    # ── Internal helpers ──────────────────────────────────────

    def _build_prompt(self, user_input, tool_result=None):
        long_mem = self.long_memory.get_relevant_facts(user_input)
        recent_history = self.short_memory.get_context()

        memory_context = f"""
Relevant memories:
{long_mem}

Recent chat history:
{recent_history}
""".strip()

        user_context = ""
        if tool_result:
            user_context = f"""
Additional Context / Tool Result:
{tool_result}
""".strip()

        system_prompt = StellaPersonality.build_prompt(
            mode=self.mode,
            memory_context=memory_context,
            user_context=user_context,
        )

        return f"""
{system_prompt}

User: {user_input}
Stella:
""".strip()

    @staticmethod
    def _clean_response(text):
        text = text.strip()
        if text.startswith("Stella:"):
            text = text[len("Stella:") :].strip()
        return text

    # ── Public API ────────────────────────────────────────────

    def chat_with_context(self, user_input: str, tool_result: str = None) -> str:
        """
        Sends user input to Stella alongside memory and optional tool result.
        """
        prompt = self._build_prompt(user_input, tool_result)
        response = self.llm.generate(prompt)
        response = self._clean_response(response)

        self.short_memory.add_message("user", user_input)
        self.short_memory.add_message("assistant", response)
        return response

    def chat_stream(self, user_input: str):
        """
        Stream output token by token with full memory context.
        """
        prompt = self._build_prompt(user_input)
        full_response = ""
        for chunk in self.llm.stream(prompt):
            token = chunk["choices"][0]["text"]
            full_response += token
            yield token
        full_response = self._clean_response(full_response)
        self.short_memory.add_message("user", user_input)
        self.short_memory.add_message("assistant", full_response)
