# Veil Core

Veil is a **stateful local AI agent runtime** built on llama.cpp and GGUF models.

It is designed as an extensible conversational system with:

* personality systems
* memory layers
* tool orchestration
* session state tracking
* reference resolution
* local LLM inference
* modular agent architecture

Veil focuses on lightweight orchestration instead of heavyweight AI frameworks.

---

# Features

## Local LLM Runtime

* llama.cpp backend
* GGUF model support
* streaming token generation
* configurable sampling parameters
* low dependency overhead

## Agent System

Veil uses a three-layer orchestration architecture:

| Layer | Component | Role |
|-------|-----------|------|
| Routing | **IntentRouter** | Regex-based intent detection |
| State | **StateManager** | SessionState + reference resolver |
| Coordinator | **Orchestrator** | Thin coordinator, tool execution, formatting |

## Session State & Reference Resolution

Veil maintains cross-turn conversation state:

* `last_search_results` — auto-saved from web searches
* `tool_history` — past tool executions
* `active_topic` — current conversation subject
* `resolve_reference()` — understands "nomor 2", "yang pertama", "buka link ketiga"
* References auto-trigger `web_extract` on prior results

## Personality Engine

Stella is the default persona system:

* Indonesian-first conversation style
* adaptive tone & mood
* casual natural responses
* multiple behavior modes:

  * casual
  * serious
  * flirty
  * dark
  * roleplay

## Memory System

### Short-Term Memory

* recent conversation history
* automatic trimming
* 4000-char context budget management
* ignores low-value messages (< 30 tokens)
* long-message truncation (> 500 chars)

### Long-Term Memory

* persistent JSON-based memory
* timestamped memories (Unix epoch)
* importance scoring (1–3)
* deduplication
* capped at 500 facts, injects max 10
* sorted by importance + recency

### Storage Layer

* atomic JSON saving (tempfile → `os.replace`)
* crash-safe persistence
* optional autosave batching

## Tool System

All tools return a normalized `ToolResult` dataclass with `.success`, `.data`, `.error`, `.source`.

| Tool | Endpoint | Description |
|------|----------|-------------|
| `web_search` | Tavily `/search` | Web search, Bearer auth, TTL cache |
| `web_extract` | Tavily `/extract` | Scrape URL content (RAG foundation) |
| `tavily_usage` | Tavily `/usage` | Check quota & plan details |
| `calculator` | safe eval | Math + percentage, injection blocked |
| `datetime` | WIB | Indonesian day/month names |

Caching: `_CachedMixin` — TTL-based (3600s), evicts oldest entry, no `clear()`.

---

# Architecture

```text
User
 ↓
IntentRouter        ← regex intent detection
 ↓
StateManager        ← SessionState + reference resolution
 ↓
Orchestrator        ← tool routing + execution
 ├─ Tool Result
 ├─ Formatter Layer
 └─ Prompt Builder
 ↓
LLM Engine
 ↓
Response
```

---

# Project Structure

```text
Veil/
├── app.py                      ← entry point
├── config.py                   ← all tunables + .env
├── test_agent.py               ← 30 assertions
│
├── core/
│   ├── orchestrator.py         ← thin coordinator
│   ├── intent_router.py        ← rule-based intent
│   └── state_manager.py        ← SessionState + resolve
│
├── llm/
│   ├── engine.py               ← llama.cpp wrapper
│   └── prompt.py               ← sanitize + format
│
├── memory/
│   ├── short_term.py           ← 4k budget
│   ├── long_term.py            ← JSON, importance
│   └── store.py                ← atomic persistence
│
├── personality/
│   ├── stella.py               ← Stella persona
│   └── rules.py                ← mode definitions
│
├── tools/
│   ├── base.py                 ← BaseTool + ToolResult
│   ├── web/
│   │   └── search.py           ← Tavily REST + _CachedMixin
│   └── system/
│       ├── calculator.py       ← safe eval
│       └── datetime.py         ← WIB locale
│
├── utils/
│   └── logger.py               ← structured logging
│
├── requirements.txt
├── .env.example
├── README.md
└── AGENT.md
```

---

# Installation

```bash
git clone https://github.com/suryardh/Veil.git
cd Veil

python -m venv .venv
```

## Activate Virtual Environment

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Model Setup

Recommended model:

```text
Qwen2.5-3B-Instruct Q4_K_M GGUF
```

Place your model inside:

```text
models/
```

Example:

```text
models/qwen2.5-3b-instruct-q4_k_m.gguf
```

Inference backend:

* llama.cpp
* llama-cpp-python

---

# Configuration

Main configuration lives in:

```text
config.py
```

Includes:

* dynamic CPU thread allocation
* sampling parameters (temp, top_p, repeat_penalty)
* context size (2048)
* memory limits
* search timeout & cache size
* logging settings

Environment overrides:

```bash
VEIL_TEMP=0.9
TAVILY_API_KEY=tvly-...
```

---

# Run

```bash
python app.py
```

---

# Testing

```bash
python test_agent.py
```

Current coverage (30 tests):

* calculator (6)
* datetime (4)
* long-term memory (6)
* short-term memory (4)
* intent detection (7)
* LLM integration (3)

---

# Current Limitations

* **No planner** — only 1 tool per intent, no multi-step reasoning
* **No chat template** — plain-text prompt (`User: ...\nStella: ...`), not Qwen Instruct format
* **No async** — all tools are blocking
* **Keyword memory** — no semantic embeddings, no vector retrieval
* **2k context** — model supports up to 32k, currently limited to 2048

---

# License

MIT License
