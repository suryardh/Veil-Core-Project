import os
import re

import config

_USE_GPU = config.USE_GPU

def _setup_cuda_paths():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    site_pkg = os.path.join(base, "venv", "Lib", "site-packages")
    for d in [
        os.path.join(site_pkg, "nvidia", "cublas", "bin"),
        os.path.join(site_pkg, "nvidia", "cuda_runtime", "bin"),
    ]:
        if os.path.isdir(d):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")

_setup_cuda_paths()

from llama_cpp import Llama

CLEANUP_PATTERNS = [
    (re.compile(r"<\|im_start\|>\s*(?:assistant|user|system)?", re.I), ""),
    (re.compile(r"<\|im_end\|>"), ""),
    (re.compile(r"^\s*(?:assistant|user|system)\s*", re.I), ""),
]


class LLMEngine:
    def __init__(self, model_path):
        kwargs = dict(
            model_path=model_path,
            n_ctx=config.N_CTX,
            n_threads=config.N_THREADS,
            verbose=False,
        )
        if _USE_GPU:
            kwargs["n_gpu_layers"] = -1
        self.model = Llama(**kwargs)

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

