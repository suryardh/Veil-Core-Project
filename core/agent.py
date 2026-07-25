from llm.engine import LLMEngine
from memory.long_term import LongTermMemory
from memory.short_term import ShortTermMemory
from utils.text import sanitize_llm_output
import config


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
    def _build_full_input(user_input: str, observation: str = "") -> str:
        full_input = user_input
        if observation:
            full_input += f"\n\n{observation[:500]}"
        return full_input

    def _build_prompt(self, system: str, user_input: str, observation: str = "") -> str:
        history = self._format_history_as_chat()
        history = self._truncate(history, config.CTX_BUDGET_HISTORY)
        sep = "\n" if history else ""
        full_input = self._build_full_input(user_input, observation)
        return (
            f"<|im_start|>system\n{system}<|im_end|>\n"
            f"{history}{sep}"
            f"<|im_start|>user\n{full_input}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    def generate(self, system: str, user_input: str, observation: str = "") -> str:
        prompt = self._build_prompt(system, user_input, observation)
        budget = config.CTX_BUDGET_SYSTEM + config.CTX_BUDGET_HISTORY + len(user_input) + 500
        prompt = self._truncate(prompt, budget)
        response = self.llm.generate(prompt)
        response = sanitize_llm_output(response)
        full_input = self._build_full_input(user_input, observation)
        self.short_memory.add_message("user", full_input)
        self.short_memory.add_message("assistant", response)
        return response

    def chat_stream(self, user_input: str):
        prompt = self._build_prompt("You are Stella, a companion.", user_input)
        full_response = ""
        for token in self.llm.stream(prompt):
            full_response += token
            yield token
        full_response = sanitize_llm_output(full_response)
        self.short_memory.add_message("user", user_input)
        self.short_memory.add_message("assistant", full_response)