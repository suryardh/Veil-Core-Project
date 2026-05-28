import re

from llm.engine import LLMEngine
from memory.long_term import LongTermMemory
from memory.short_term import ShortTermMemory
import config

CLEANUP_PATTERNS = [
    (re.compile(r"<\|im_start\|>\s*(?:assistant|user|system)?", re.I), ""),
    (re.compile(r"<\|im_end\|>"), ""),
    (re.compile(r"^\s*(?:assistant|user|system)\s*", re.I), ""),
]


class VeilAgent:
    def __init__(self, model_path):
        self.llm = LLMEngine(model_path)
        self.short_memory = ShortTermMemory()
        self.long_memory = LongTermMemory()

    @staticmethod
    def _truncate(text, budget):
        if len(text) <= budget:
            return text
        return "..." + text[-(budget - 3):]

    def _format_history_as_chat(self) -> str:
        blocks = []
        for msg in self.short_memory.history:
            role = msg["role"]
            content = msg["content"]
            blocks.append(f"<|im_start|>{role}\n{content}<|im_end|>")
        return "\n".join(blocks)

    @staticmethod
    def _clean_response(text):
        text = text.strip()
        if "<|im_end|>" in text:
            text = text.split("<|im_end|>")[0]
        for pattern, replacement in CLEANUP_PATTERNS:
            text = pattern.sub(replacement, text)
        return text.strip()

    def _build_prompt(self, system: str, user_input: str) -> str:
        history = self._format_history_as_chat()
        history = self._truncate(history, config.CTX_BUDGET_HISTORY)
        sep = "\n" if history else ""
        return (
            f"<|im_start|>system\n{system}<|im_end|>\n"
            f"{history}{sep}"
            f"<|im_start|>user\n{user_input}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    def generate(self, system: str, user_input: str) -> str:
        prompt = self._build_prompt(system, user_input)
        prompt = self._truncate(prompt, config.N_CTX - config.CTX_BUDGET_RESPONSE)
        response = self.llm.generate(prompt)
        response = self._clean_response(response)
        self.short_memory.add_message("user", user_input)
        self.short_memory.add_message("assistant", response)
        return response

    def chat_stream(self, user_input: str):
        prompt = self._build_prompt("You are Stella, a companion.", user_input)
        full_response = ""
        for token in self.llm.stream(prompt):
            full_response += token
            yield token
        full_response = self._clean_response(full_response)
        self.short_memory.add_message("user", user_input)
        self.short_memory.add_message("assistant", full_response)
