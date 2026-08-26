import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Model Configuration ---
# Active: huihui-ai/Qwen2.5-7B-Instruct-abliterated-v2 (uncensored, mradermacher i1-Q4_K_M quant)
# Rollback: models/qwen2.5-3b-instruct-q4_k_m.gguf (pre-migration baseline, see BASELINE.md)
MODEL_PATH = os.path.join("models", "qwen2.5-7b-instruct-abliterated-v2-q4_k_m.gguf")
N_CTX = 4096
N_THREADS = max(1, (os.cpu_count() or 4) // 2)
USE_GPU = os.getenv("VEIL_USE_GPU", "1") == "1"

# --- Inference Parameters ---
# Tuned 2026-08-26 after live-sim showed word salad at temp 0.7 (MODEL-005).
SAMPLING = {
    "temperature": float(os.getenv("VEIL_TEMP", "0.6")),
    "top_p": 0.9,
    "min_p": 0.05,
    "repeat_penalty": 1.15,
}
MAX_TOKENS = 300
MAX_TOKENS_STREAM = 400
STOP_TOKENS = ["<|im_end|>"]

# --- Context Budget (CHARACTERS, not tokens — measured in tools/ctx_report.py) ---
# Qwen2.5 tokenizer averages ~4.1 chars/token on Indonesian text.
# Hard guard: assembled prompt stays <= CTX_PROMPT_CHAR_LIMIT so that
# prompt tokens + streaming response fit inside N_CTX with 64-token headroom.
# History is truncated FIRST (oldest dropped); the system block is never cut.
CTX_PROMPT_CHAR_LIMIT = int((N_CTX - MAX_TOKENS_STREAM - 64) * 4.0)  # ≈ 14_544
CTX_BUDGET_HISTORY = 2500  # soft target for normal operation

# --- Memory Configuration ---
LONG_TERM_MEMORY_PATH = os.path.join("memory", "long_term.json")
SHORT_TERM_MEMORY_LIMIT = 8

# --- Logging ---
LOG_DIR = "logs"

# --- Web / Search ---
WEB_SEARCH_CACHE_SIZE = 32
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SEARCH_TIMEOUT = 10
