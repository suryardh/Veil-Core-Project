import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Model Configuration ---
MODEL_PATH = os.path.join("models", "qwen2.5-3b-instruct-q4_k_m.gguf")
N_CTX = 4096
N_THREADS = max(1, (os.cpu_count() or 4) // 2)

# --- Inference Parameters ---
SAMPLING = {
    "temperature": float(os.getenv("VEIL_TEMP", "0.7")),
    "top_p": 0.95,
    "repeat_penalty": 1.1,
}
MAX_TOKENS = 150
MAX_TOKENS_STREAM = 200
STOP_TOKENS = ["<|im_end|>"]

# --- Context Budget (character proxies for token limits) ---
CTX_BUDGET_SYSTEM = 2000
CTX_BUDGET_HISTORY = 1500
CTX_BUDGET_RESPONSE = 800

# --- Memory Configuration ---
LONG_TERM_MEMORY_PATH = os.path.join("memory", "long_term.json")
SHORT_TERM_MEMORY_LIMIT = 8

# --- Logging ---
LOG_DIR = "logs"

# --- Web / Search ---
WEB_SEARCH_CACHE_SIZE = 32
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SEARCH_TIMEOUT = 10
