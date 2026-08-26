# Veil Core

Veil is a **personality-centric local AI companion runtime** built on llama.cpp and GGUF models.

It is designed as a persistent character system with emotional continuity, not just an agent framework with a prompt wrapper.

```
personality system with capabilities
beyond an agent with personality
```

---

# Features

## Emotional Core

- **Emotion analysis** — keyword-based valence/arousal detection from user input
- **Relationship state** — 5-dimensional dynamic model (affection, trust, attachment, comfort, dependency)
- **Mood modulation** — warm, playful, guarded, yearning, neutral — shifts naturally per interaction
- **State decay** — prevents relationship from being permanently maxed out
- **Emotional mode** — comforting/withdrawn/yearning/excited/soft with mode_strength; resists overwrite when > 0.5
- **Emotional memory** — stores interactions with valence/arousal weight; salience filter prevents pollution

## Personality System

- **Stella** — Indonesian-first companion with natural conversational style
- **No mode switching** — dynamic state modulation replaces rigid mode toggles
- **Identity permanence** — humor, warmth, teasing, emotional openness, protectiveness as fixed traits
- **No numeric values in prompts** — state mapped to natural language descriptors
- **Trust default 0.35** — prevents premature guarded mood after first decay

## Memory System

- **Short-term memory** — recent conversation with 4k budget, chat-template format, ignore/truncate rules
- **Long-term memory** — persistent JSON, per-tier quota (5 importance + 5 recency), dedup, structured extraction
- **Emotional memory** — valence/arousal records with recurrence merging and salience filtering

## Tool System

Tools are executed **invisibly** behind the personality layer. Users see natural responses, not execution traces.

| Tool | Description |
|------|-------------|
| `web_search` | Tavily `/search` — web search with TTL cache; `rfind`-based prefix stripping |
| `web_extract` | Tavily `/extract` — URL content extraction |
| `calculator` | Safe eval — math + percentage + functions (sqrt, sin, cos), injection blocked |
| `datetime` | WIB Indonesian locale |

Tool routing runs **after** cognition — cognition tried first, then tool routing for calculator/datetime/tavily. This prevents "hari ini" (datetime trigger) from stealing search queries.

## Cognition (Subconscious)

- `core/cognition.py` — invisible search→extract→summarize pipeline
- No DAG, no JSON planning, no visible execution
- Triggered automatically when factuality is needed
- Results injected as natural context, not raw execution output
- Search query auto-cleaned: `"halo, cari kurs dollar"` → `"kurs dollar"`
- Uses Tavily `include_answer` + `search_depth=advanced` for richer results (AI answer + 3 snippets)
- Results injected as natural continuation in user message (no `=== Search Results ===` delimiter)

## TUI (Optional)

A rich-based split-panel TUI is available via `app_tui.py`:
- Emotional state header (mood, trust, attachment)
- Scrollable color-coded conversation history (green=user, cyan=Stella)
- Clean input prompt

```bash
pip install rich   # if not already installed
python app_tui.py
```

---

# Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#e1f5fe', 'primaryBorderColor': '#0288d1', 'tertiaryColor': '#fff'}}}%%
flowchart TB
    User([User Input])

    subgraph Emotion["Emotion Layer"]
        Analyzer[analyzer.py<br/>keyword - emotion detection]
        State[state.py<br/>relationship update + decay]
        Emotional[emotional.py<br/>memory record]
    end

    subgraph Decision["Decision Layer"]
        React{reaction<br/>override?}
        CogCheck{cognition<br/>needed?}
        ToolCheck{tool<br/>needed?}
    end

    subgraph Execution["Execution Layer"]
        Cognition[cognition.py<br/>search - extract - summarize]
        Tool[orchestrator.py<br/>run_tool]
        Direct[direct chat]
    end

    subgraph Response["Response Layer"]
        Prompt[prompting.py<br/>state to natural language]
        Agent[agent.py<br/>build prompt + history]
        LLM[engine.py<br/>llama.cpp]
    end

    User --> Analyzer
    Analyzer --> State
    State --> Emotional
    Emotional --> React

    React -->|yes| Return([Return reaction])
    React -->|no| CogCheck

    CogCheck -->|yes| Cognition
    CogCheck -->|no| ToolCheck
    ToolCheck -->|calc/datetime/tavily| Tool
    ToolCheck -->|no| Direct

    Cognition --> Prompt
    Tool --> Prompt
    Direct --> Prompt

    Prompt --> Agent
    Agent --> LLM
    LLM --> Response
```

---

# Project Structure

```text
Veil/
├── app.py                      ← CLI entry point
├── app_tui.py                  ← TUI entry point (rich, split-panel)
├── config.py                   ← all tunables + .env
├── test_agent.py               ← 55 assertions
│
├── core/
│   ├── bootstrap.py            ← App startup consolidation
│   ├── cognition.py            ← invisible search→extract→summarize
│   ├── orchestrator.py         ← pure infra boundary (run_tool)
│   └── agent.py                ← LLM wrapper + history
│
├── llm/
│   └── engine.py               ← llama.cpp wrapper + sanitize
│
├── memory/
│   ├── emotional.py            ← valence/arousal records, salience filter
│   ├── extractor.py            ← structured fact extraction
│   ├── short_term.py           ← 4k budget, chat-template format
│   ├── long_term.py            ← JSON, importance (explicit)
│   └── store.py                ← atomic persistence
│
├── personality/
│   ├── core.py                 ← thin coordinator (analyze → decide → respond)
│   ├── state.py                ← StellaIdentity + StellaState (5-dim, decay)
│   ├── analyzer.py             ← keyword → EmotionAnalysis
│   ├── prompting.py            ← state → natural language descriptor
│   ├── stella.py               ← identity constants (base, rules, safety)
│   ├── persistence.py          ← save/load state.json (schema v2)
│   ├── inactivity.py           ← absence detection + relationship deltas
│   ├── initiative.py           ← probabilistic openers on user return
│   └── rhythm.py               ← 7-priority matrix + mode modulation + reactions
│
├── tools/
│   ├── base.py                 ← BaseTool + ToolResult + ToolContext
│   ├── state_backup.py         ← manual backup/restore data/state.json
│   ├── bench.py                ← fixed-prompt benchmark (baseline comparison)
│   ├── web/
│   │   └── search.py           ← Tavily REST + _CachedMixin
│   └── system/
│       ├── calculator.py       ← safe eval
│       └── datetime.py         ← WIB locale
│
├── utils/
│   ├── logger.py               ← structured logging
│   ├── async_utils.py          ← with_retry (used by search)
│   └── text.py                 ← LLM output sanitization
│
├── requirements.txt
├── README.md
└── AGENT.md
```

---

# Installation

```bash
git clone https://github.com/suryardh/Veil-Core-Project.git
cd Veil-Core-Project

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

### GPU Acceleration (optional, NVIDIA CUDA)

For RTX 4050 / CUDA-equipped GPUs — install the CUDA-enabled llama-cpp-python wheel:
```bash
pip install llama-cpp-python==0.3.25 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu125
```
Pick the `cuXXX` suffix matching your driver's max CUDA runtime (see
`nvidia-smi` header). Then ensure `VEIL_USE_GPU=1` (default in `.env` or environment).

---

# Model Setup

Recommended: **Qwen2.5-3B-Instruct Q4_K_M GGUF**

Place inside `models/`:
```
models/qwen2.5-3b-instruct-q4_k_m.gguf
```

Inference backend: llama.cpp via `llama-cpp-python`

## Model Integration Map

Where the model touches the codebase (MODEL-001 inventory):

```text
config.py                    ← all model knobs
├── MODEL_PATH               models/qwen2.5-3b-instruct-q4_k_m.gguf
├── N_CTX=4096  N_THREADS    loaded by llm/engine.py LLMEngine.__init__
├── USE_GPU                  → n_gpu_layers=-1 when enabled
├── SAMPLING / MAX_TOKENS    merged in engine._default_params()
├── STOP_TOKENS              ["<|im_end|>"]
└── CTX_BUDGET_*             char budgets applied in core/agent.py

Call chain (one generation):
personality/core.py PersonalityCore.handle(user_input)
  → core/agent.py VeilAgent.generate(system, user_input, observation)
      builds raw ChatML (<|im_start|>system/user/assistant<|im_end|>)
      truncates history/prompt via _truncate() + CTX_BUDGET_*
  → llm/engine.py LLMEngine.generate(prompt)
      llama_cpp.Llama(...) call with SAMPLING params

Persistence around it:
  state: personality/persistence.py ↔ data/state.json (schema v2)
  short-term memory: memory/short_term.py (in-memory, cap limit×2 msgs, 500 chars/msg)
  long-term memory: memory/long_term.py ↔ memory/long_term.json
```

### Assumptions tied to the current 3B model

- Filename hardcoded in `config.MODEL_PATH` and in bootstrap's error message.
- ChatML `<|im_start|>/<|im_end|>` matches Qwen2 template — any Qwen2-family
  GGUF is drop-in; other families need prompt-format changes.
- Context budgets are **characters**, not tokens (~3.5–4 chars/token for
  Indonesian) — never validated against real tokenization (see MODEL-004).
- N_CTX=4096 vs model's 32k training context — large unused headroom.
- Installed wheel is CPU-only and `_setup_cuda_paths()` targets a nonexistent
  `venv\` dir — GPU is currently not used (details in `BASELINE.md`).

---

# Configuration

Main config in `config.py`:
- CPU thread allocation
- Sampling parameters (temp, top_p, repeat_penalty)
- Context size (4096)
- Context budgeting (system: 2.5k, history: 2.5k, response: 800)
- Max tokens: 300 (normal), 400 (stream)
- Memory limits
- Search timeout & cache size
- GPU mode toggle (`USE_GPU`)

Environment overrides:
```bash
USE_GPU=1              # GPU mode (default) | 0 = CPU-only
VEIL_TEMP=0.9
TAVILY_API_KEY=tvly-...
```

---

# Run

### CLI (default)
```bash
python app.py
```

### TUI (rich-based)
```bash
python app_tui.py
```

---

# Backup & Restore State

`data/state.json` holds accumulated relationship state — back it up before model or runtime changes.

```bash
# create a timestamped backup in data/backups/
python tools/state_backup.py export

# verify a backup against a temporary copy (live state untouched)
python tools/state_backup.py restore data/backups/<file>.json

# actually overwrite the live state file after verification
python tools/state_backup.py restore data/backups/<file>.json --apply
```

Backups are JSON envelopes containing the original payload plus `created_at`,
`schema_version`, and a SHA-256 checksum. Tampered backups and backups from a
newer schema version are rejected on restore. Old backups are never deleted
automatically.

---

# Testing

```bash
python test_agent.py
```

55 tests (passing):
- calculator (6)
- datetime (4)
- long-term memory (6)
- short-term memory (4)
- emotional analysis (11)
- state management (6)
- emotional memory (4)
- state backup/restore (10)
- orchestrator (1)
- LLM integration (3)

---

# License

MIT License
