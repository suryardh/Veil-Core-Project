# Veil Agent Architecture

## Overview

Veil is a **stateful local AI agent runtime** built for:

* orchestration
* personality injection
* external memory systems
* tool execution
* session state tracking
* reference resolution
* local LLM inference

The project focuses on building a scalable AI agent architecture instead of a simple chatbot wrapper.

Veil treats the language model as only one component inside a larger controllable system.

---

# Core Philosophy

Veil follows this principle:

```text
Keep the model simple.
Make the system intelligent.
```

The LLM is treated as:

* language generation engine
* reasoning component
* conversational layer

Everything else is externalized:

* memory
* orchestration
* session state
* tools
* routing
* persistence
* runtime behavior

This allows:

* controllable behavior
* model swapping without memory loss
* lower resource usage
* easier debugging
* system-level scalability

---

# Why Veil Avoids Heavy AI Frameworks

Veil intentionally avoids heavyweight orchestration frameworks.

Reasons:

* lower runtime overhead
* easier debugging
* explicit execution flow
* fewer hidden abstractions
* easier experimentation
* simpler dependency graph
* more control over prompting and memory

The goal is architecture clarity over framework magic.

---

# High-Level Architecture

```text
User
 ↓
IntentRouter
 ↓
StateManager
 ├─ SessionState
 └─ resolve_reference()
 ↓
Orchestrator
 ├─ Tool Execution
 ├─ Formatter Layer
 └─ Prompt Builder
 ↓
Agent Layer (Stella)
 ↓
LLM Engine
 ↓
Response
```

---

# Core Components

## 1. app.py

Application entry point.

Responsibilities:

* CLI runtime loop
* logger initialization
* tool registration
* graceful shutdown handling
* exception handling

Architecture notes:

* lightweight entrypoint
* no orchestration logic
* test-friendly structure via `main()` guard

Status:

* IMPLEMENTED

---

## 2. Orchestrator (`core/orchestrator.py`)

Thin coordinator layer (~40 lines). Delegates to IntentRouter + StateManager.

Responsibilities:

* coordinate intent → tool → format → LLM flow
* tool execution with `_run_tool()`
* invoke formatters per tool type
* pass formatted result to `chat_with_context()`

Key design:

* no intent logic (delegated to IntentRouter)
* no state logic (delegated to StateManager)
* formatters are stateless functions in a dict

```python
class Orchestrator:
    def __init__(self, agent, tools_registry=None):
        self.agent = agent
        self.tools = tools_registry or {}
        self.intent = IntentRouter()
        self.state = StateManager()
```

Status:

* IMPLEMENTED

---

## 3. IntentRouter (`core/intent_router.py`)

Rule-based intent detection, extracted from the old monolithic Orchestrator.

Detected intents:

| Intent | Trigger keywords |
|--------|-----------------|
| `web_search` | search, cari, browse, google, ddg |
| `datetime` | jam berapa, tanggal berapa, hari ini, what time |
| `calculator` | math expressions, hitung, sqrt, persen |
| `memory_write` | startswith "ingat ", "ingatkan ", "remember " |
| `chat` | fallback (no intent matched) |

Architecture:

* pure function, no state
* easily testable in isolation
* regex patterns in `CALC_PATTERNS`

Status:

* IMPLEMENTED

---

## 4. StateManager + SessionState (`core/state_manager.py`)

Cross-turn conversation state for reference resolution and tool chaining.

### SessionState

```python
@dataclass
class SessionState:
    last_search_results: list[dict]
    last_tool: str | None
    active_topic: str | None
    tool_history: list[dict]
```

### Reference Resolution

`resolve_reference()` detects Indonesian references to prior search results:

| Input | Resolves to |
|-------|------------|
| `nomor 2` | `last_search_results[1]` |
| `yang pertama` | `last_search_results[0]` |
| `buka link ketiga` | `last_search_results[2]` |
| `no 3` | `last_search_results[2]` |
| `#1` | `last_search_results[0]` |

When a reference is resolved, Orchestrator auto-triggers `web_extract` on the URL.

Status:

* IMPLEMENTED

---

## 5. Agent Layer (`core/agent.py`)

Prompt assembly and response coordination layer.

Responsibilities:

* build prompts
* inject memory
* inject tool results
* sanitize model output
* update memory systems

Key methods:

* `_build_prompt()`
* `_clean_response()`
* `chat_with_context()`
* `chat_stream()`

Important behaviors:

* removes hallucinated `Stella:` prefixes
* shared prompt builder eliminates duplicated logic
* streaming saves memory only after completion

Architecture philosophy:

* agent layer handles orchestration-facing behavior
* raw inference stays isolated in `llm/engine.py`

Status:

* IMPLEMENTED

---

## 6. Personality System (`personality/`)

Stella is the default personality runtime.

Responsibilities:

* identity shaping
* tone control
* language rules
* behavioral boundaries
* mode switching

Implemented modes:

* casual
* serious
* flirty
* dark
* roleplay

Design philosophy:

* personality is externalized from the model
* prompt layering instead of model fine-tuning
* lightweight enough for small GGUF models

Key behavior:

* Indonesian-first responses
* casual internet-native language
* natural conversation flow
* no robotic assistant tone

Status:

* IMPLEMENTED

---

## 7. LLM Engine (`llm/engine.py`)

Low-level inference wrapper around llama.cpp.

Responsibilities:

* raw inference
* token streaming
* parameter management
* output sanitization

Features:

* streaming generation
* configurable sampling
* repetition control
* stop token management

Key parameters:

* `top_p = 0.95`
* `repeat_penalty = 1.1`

Important architecture rule:

* no memory logic
* no orchestration logic
* no personality logic

LLM engine should remain inference-only.

Status:

* IMPLEMENTED

---

## 8. Prompt Utilities (`llm/prompt.py`)

Shared utilities for prompt safety and formatting.

Responsibilities:

* sanitize external content
* format memory context
* inject tool outputs
* truncate oversized context

Key protections:

* escapes `User:` and `Stella:` inside external content
* prevents simple role confusion injection
* character-budget context trimming

Important philosophy:

* prompt injection resistance starts before inference
* external tool output should never be trusted directly

Status:

* IMPLEMENTED

---

# Memory System

Veil does not rely on model-side memory.

Memory is:

* externalized
* structured
* retrievable
* persistent
* controllable

This allows:

* persistence across sessions
* model swapping without memory loss
* better scalability
* memory inspection/debugging
* controllable retrieval

---

## 9. Short-Term Memory (`memory/short_term.py`)

Recent conversational context system.

Features:

* configurable history limit
* context budget trimming (4000 chars)
* useless-message filtering (< 30 tokens)
* long-message truncation (> 500 chars)

Key protections:

* ignores low-value messages (`wkwk`, `iya`, `lol`, etc.)
* prevents prompt flooding from huge pasted text
* drops oldest context first when exceeding limits

Status:

* IMPLEMENTED

---

## 10. Long-Term Memory (`memory/long_term.py`)

Persistent fact storage system.

Storage format:

```json
{
  "category": "fact",
  "content": "User likes coding",
  "importance": 3,
  "timestamp": 1712345678.9
}
```

Features:

* JSON-backed persistence
* timestamped memories
* importance scoring (1-3)
* deduplication
* retrieval filtering
* capped storage (500 facts, injects 10)

Memory ranking:

* importance DESC
* recency DESC

Architecture philosophy:

* small curated memory > giant unfiltered memory dump

Status:

* IMPLEMENTED

---

## 11. JSON Store (`memory/store.py`)

Persistent storage layer.

Features:

* atomic save system
* autosave toggle
* batch operation support
* crash-safe writes

Implementation:

```text
write temp file
→ flush
→ os.replace()
```

Benefits:

* zero corrupted JSON risk on crashes
* safer persistence behavior

Status:

* IMPLEMENTED

---

# Tool System

Veil uses external tools instead of relying entirely on model hallucination.

Architecture goals:

* deterministic operations
* reusable execution layer
* modular extensibility
* safe execution boundaries

All tools return a normalized `ToolResult` dataclass.

---

## 12. BaseTool + ToolResult (`tools/base.py`)

```python
@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None
    source: str = ""
    meta: dict = field(default_factory=dict)

    @classmethod
    def ok(cls, data, source="") -> ToolResult: ...
    @classmethod
    def fail(cls, error, source="") -> ToolResult: ...
```

```python
class BaseTool(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs) -> ToolResult: ...
```

Benefits:

* uniform return type across all tools
* no mixed `str | dict` returns
* clear success/failure semantics
* formatters access `result.data`, `result.error`, `result.source`
* future-proof for async, TTS, Discord, Web UI renderers

Status:

* IMPLEMENTED

---

## 13. WebSearchTool (`tools/web/search.py`)

Tavily REST API (primary and only backend).

Architecture:

* `POST /search` with Bearer auth
* `search_depth="basic"`, `max_results=5`
* MD5 query caching with TTL (3600s)
* Returns `ToolResult.ok({"query": ..., "results": [...]})`

Previous DDG scraper was removed due to ISP blocking + anti-bot JS challenges.

Cache:

* `_CachedMixin` — shared TTL cache mixin
* evicts oldest entry (not `clear()`)
* configurable `WEB_SEARCH_CACHE_SIZE = 32`

Setup:

```bash
# No additional package needed — calls REST directly via `requests`
# Get key at https://tavily.com
TAVILY_API_KEY=tvly-...
```

Status:

* IMPLEMENTED

---

## 14. WebExtractTool (`tools/web/search.py`)

Scrape URL content via Tavily `/extract` endpoint.

Architecture:

* `POST /extract` with Bearer auth
* `extract_depth="basic"`, `format="markdown"`
* Returns `ToolResult.ok({"urls": [...], "results": [...], "failed_results": [...]})`
* Cached per unique URL set with TTL

This is the foundation for RAG pipeline (search → extract → LLM summarize).

Status:

* IMPLEMENTED

---

## 15. TavilyUsageTool (`tools/web/search.py`)

Check Tavily API quota and account details.

Architecture:

* `GET /usage` with Bearer auth
* Returns `ToolResult.ok({"raw": {...}})`
* Shows plan, key usage, per-endpoint breakdown, PayGo

Status:

* IMPLEMENTED

---

## 16. CalculatorTool (`tools/system/calculator.py`)

Safe deterministic calculator.

Features:

* restricted eval
* math function whitelist (`sqrt`, `sin`, `cos`, `tan`, `log`, etc.)
* percentage parsing ("15% of 200", "15 persen dari 200")
* injection blocking
* numeric validation

Blocked patterns:

* `import`
* `eval`
* `lambda`
* `__`
* `{}` / `[]`

Architecture philosophy:

* deterministic operations should not use the LLM

Status:

* IMPLEMENTED

---

## 17. DateTimeTool (`tools/system/datetime.py`)

Local time retrieval tool.

Features:

* WIB timezone (UTC+7)
* Indonesian localization (Senin, Selasa, ..., Januari, ..., etc.)
* dependency-free timezone handling

Implementation:

```python
datetime.now(timezone(timedelta(hours=7)))
```

Status:

* IMPLEMENTED

---

# Execution Flow

```text
1. User sends message

2. Reference resolver checks input
   → "nomor 2" detected?
   → yes → auto-trigger web_extract(URL)

3. Intent detection runs
   → IntentRouter.detect()

4. Tool routing (if needed)
   → tool.execute()
   → try/except
   → ToolResult

5. Session recording
   → StateManager.record(tool, query, result)

6. Formatter renders ToolResult → string

7. Memory retrieval
   → short-term memory
   → long-term memory

8. Prompt assembly
   → personality
   → memory
   → tool context
   → user message

9. LLM inference
   → stream or blocking

10. Response sanitization

11. Memory update
```

---

# Prompt Injection Philosophy

Veil assumes external content is unsafe by default.

Protections currently implemented:

* role escaping
* prompt sanitization
* tool result wrapping
* restricted tool execution
* isolated orchestration flow

Current limitations:

* no true sandboxing
* no semantic injection detection
* no adversarial filtering yet

---

# Security / Safety Notes

Current protections:

* calculator blocks dangerous patterns
* prompt sanitization reduces role confusion
* atomic persistence prevents corruption
* tool exceptions are isolated

Known risks:

* prompt injection resistance is basic
* tools are not sandboxed
* model hallucination still possible

---

# Performance Philosophy

Veil prioritizes:

* efficient orchestration
* lightweight runtime
* smaller local models
* explicit system design

Core idea:

```text
Better orchestration + smaller models
can outperform
larger models with weak system design.
```

---

# Development Roadmap

## Phase 1 — Raw LLM Chat
- local inference
- basic prompting
- CLI chat

## Phase 2 — Tool-Enabled Chatbot
- web search (DDG scraper — later removed)
- calculator
- datetime
- regex intent routing

## Phase 3 — Memory + Personality
- short-term memory (4k budget)
- long-term memory (JSON, importance)
- Stella personality system
- structured prompt injection

## Phase 4 — Stateful Tool Agent
- IntentRouter + StateManager split
- SessionState + reference resolver
- Tavily REST (DDG removed)
- ToolResult dataclass
- Formatter layer
- TTL caching (_CachedMixin)

## Phase 5 — Planner (NEXT)
- multi-tool chains
- execution graph
- search → extract → summarize pipeline

## Phase 6 — Semantic Memory
- embeddings
- vector retrieval
- context similarity

## Phase 7 — Autonomous Loop
- plan → act → observe → reflect
- agent self-improvement
- async runtime

---

# Current State

## Complete

* local LLM inference with streaming
* Stella personality runtime (5 modes)
* short-term memory (4k budget, ignore/truncate rules)
* long-term memory (JSON, importance scoring, dedup, 500 facts)
* atomic persistence (tempfile + os.replace)
* IntentRouter (regex-based, testable in isolation)
* StateManager + SessionState (cross-turn reference resolution)
* Thin orchestrator coordinator
* ToolResult dataclass (uniform tool returns)
* Tavily REST integration (search, extract, usage)
* TTL caching (_CachedMixin, evict oldest)
* Formatter layer per tool
* Structured logging
* Automated testing (30 assertions)

## In Progress

* Planner system (multi-tool chains)
* Chat template (Qwen Instruct format)
* Semantic memory (embeddings + vector retrieval)
* Async tool execution

---

# Recommended Model

Recommended:

* Qwen2.5-3B-Instruct GGUF (Q4_K_M)

Inference backend:

* llama.cpp
* llama-cpp-python

---

# Final Notes

Veil is a research-oriented modular local AI runtime.

Behavior quality depends heavily on:

* orchestration quality
* memory structure
* prompt design
* retrieval quality
* model alignment

The long-term goal is not to create a chatbot.

The goal is to build a controllable local AI agent system.
