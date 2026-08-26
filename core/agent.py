from llm.engine import LLMEngine
from memory.long_term import LongTermMemory
from memory.short_term import ShortTermMemory
from utils.text import (sanitize_llm_output, collapse_sayang,
                        strip_emojis_from_source, fix_orphan_punct,
                        remove_pet_names)
import config


def _polish(response: str, user_text: str, prev_assistant: str = "") -> str:
    response = sanitize_llm_output(response)
    response = fix_orphan_punct(response)
    response = collapse_sayang(response)
    response = strip_emojis_from_source(response, user_text)
    if prev_assistant and "sayang" in prev_assistant.lower():
        response = remove_pet_names(response)
    return response


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

    def _assemble_prompt(self, system: str, user_input: str, observation: str = "") -> str:
        """Build the final prompt. The system block is never truncated; when
        space runs out, history is dropped oldest-first, then the user input
        is tail-capped. Deterministic (MODEL-004)."""
        full_input = user_input
        if observation:
            full_input += f"\n\n{observation[:500]}"

        sys_block = f"<|im_start|>system\n{system}<|im_end|>\n"
        limit = config.CTX_PROMPT_CHAR_LIMIT
        max_input = limit // 2
        if len(full_input) > max_input:
            full_input = "..." + full_input[-(max_input - 3):]
        user_block = f"<|im_start|>user\n{full_input}<|im_end|>\n<|im_start|>assistant\n"

        hist_budget = min(
            config.CTX_BUDGET_HISTORY,
            max(0, limit - len(sys_block) - len(user_block)),
        )
        history = self._truncate(self._format_history_as_chat(), hist_budget)
        sep = "\n" if history else ""
        return f"{sys_block}{history}{sep}{user_block}"

    def _last_assistant_text(self) -> str:
        if self.short_memory.history and self.short_memory.history[-1]["role"] == "assistant":
            return self.short_memory.history[-1]["content"]
        return ""

    def generate(self, system: str, user_input: str, observation: str = "") -> str:
        prompt = self._assemble_prompt(system, user_input, observation)
        response = self.llm.generate(prompt)
        full_input = user_input
        if observation:
            full_input += f"\n\n{observation[:500]}"
        response = _polish(response, full_input, self._last_assistant_text())
        self.short_memory.add_message("user", full_input)
        self.short_memory.add_message("assistant", response)
        return response

    def chat_stream(self, user_input: str):
        prompt = self._assemble_prompt("You are Stella, a companion.", user_input)
        full_response = ""
        for token in self.llm.stream(prompt):
            full_response += token
            yield token
        full_response = _polish(full_response, user_input, self._last_assistant_text())
        self.short_memory.add_message("user", user_input)
        self.short_memory.add_message("assistant", full_response)