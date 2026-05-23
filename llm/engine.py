from llama_cpp import Llama
import config


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
        for prefix in ["Stella:", "User:", "stella:", "user:"]:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        return text

    def stream(self, prompt, **kwargs):
        params = self._default_params(max_tokens=config.MAX_TOKENS_STREAM, stream=True, **kwargs)
        return self.model(prompt, **params)

    def generate(self, prompt, **kwargs):
        params = self._default_params(stream=False, **kwargs)
        response = self.model(prompt, **params)
        return self._sanitize(response["choices"][0]["text"])

