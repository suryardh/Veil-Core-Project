import re

from llama_cpp import Llama
import config

CLEANUP_PATTERNS = [
    (re.compile(r"<\|im_start\|>\s*(?:assistant|user|system)?", re.I), ""),
    (re.compile(r"<\|im_end\|>"), ""),
    (re.compile(r"^\s*(?:assistant|user|system)\s*", re.I), ""),
]


class LLMEngine:
    def __init__(self, model_path):
        self.model = Llama(
            model_path=model_path,
            n_ctx=config.N_CTX,
            n_threads=config.N_THREADS,
            verbose=False,
        )

    @staticmethod
    def _default_params(**kwargs):
        params = {
            **config.SAMPLING,
            "max_tokens": config.MAX_TOKENS,
            "stop": config.STOP_TOKENS,
        }
        params.update(kwargs)
        return params

    @staticmethod
    def _sanitize(text):
        text = text.strip()
        if "<|im_end|>" in text:
            text = text.split("<|im_end|>")[0]
        for pattern, replacement in CLEANUP_PATTERNS:
            text = pattern.sub(replacement, text)
        return text.strip()

    @staticmethod
    def _sanitize_token(token):
        return token.replace("<|im_start|>", "").replace("<|im_end|>", "")

    def stream(self, prompt, **kwargs):
        params = self._default_params(max_tokens=config.MAX_TOKENS_STREAM, stream=True, **kwargs)
        for chunk in self.model(prompt, **params):
            token = chunk["choices"][0]["text"]
            cleaned = self._sanitize_token(token)
            if cleaned:
                yield cleaned

    def generate(self, prompt, **kwargs):
        params = self._default_params(stream=False, **kwargs)
        response = self.model(prompt, **params)
        return self._sanitize(response["choices"][0]["text"])

