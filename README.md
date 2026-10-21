# Veil Core

Veil is a **personality-centric local AI companion runtime** built on llama.cpp and GGUF models.

It is designed as a persistent character system with emotional continuity, not just an agent framework with a prompt wrapper.

```
personality system with capabilities
beyond an agent with personality
```

---

# Project Status

> **Current phase: Phase 0 — Repository Audit (COMPLETE).** All seven exit
> criteria are MET. See `PLAN.md` for exit criteria and `BASELINE.md` for
> what is measured vs. historical.
>
> **AUDIT-004 criterion 3 is MET.** Four 13-prompt benchmark runs were
> executed (VEIL_TEMP=0.7, 13/13 each, exit 0) and scored against B-01..B-13.
> Final: 12 PASS, 1 FAIL (B-11 only) under the corrected B-09 criterion.
> B-09 corrected: honest AI admission is desired behavior, not a failure.
> B-11 (companion register for factual answers) is a documented known
> limitation of the current 7B quantized model, accepted as a documented
> exception per owner decision. Code-level guard is in place and tested.
> Long-conversation is implemented and exercised (2 scenarios, 8 turns) but
> cross-turn behavioral acceptance is tracked as a separate follow-up.
>
> The AUDIT-006 full-response capture (`tools/bench.py --output`) is
> implemented and committed locally (not pushed). Run summary integrity
> change is uncommitted.
>
> Implemented ≠ verified. The deterministic test suite passes **141**
> assertions (`test_agent.py`); bench guard runners (88 + 52 + 15 + 33 + 17
> = 205) are counted separately below. The 3 LLM-dependent end-to-end
> assertions have not been run in the audit.
>
> **Phase 0 is COMPLETE.** All seven exit criteria are MET. Phase 1 may
> proceed.

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
- **Conflict dynamics** — directed insults trigger cooling, withdrawn mode, gradual recovery, reconciliation halving; third-party venting and neutral chat are ignored
- **Persona rules v3.1** — centralized rules (`personality/rules.py`) with pseudo-memory and relationship-inference guards (Stella never invents experiences her memory doesn't support or assumes feelings about the user without evidence)
- **Trust default 0.35** — prevents premature guarded mood after first decay

## Memory System

- **Short-term memory** — recent conversation with 8-message / chat-template budget, ignore/truncate rules
- **Long-term memory** — persistent JSON (up to 500 facts), relevance-scored injection (top 10), dedup, keyword-importance extraction
- **Fact extraction** — `memory/extractor.py` turns *explicit* seeds ("inget ya, ulang tahun aku bulan depan") into importance-weighted facts. Since 2026-10-15 a `ya`/`bahwa`/`kalau` particle is required, so a recall question such as "inget ga kemarin kita bahas apa?" is no longer misread as a save command. A bare imperative without the particle is currently not captured — tracked as `PLAN.md` D-12
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

## Behavioral Evaluator (deterministic)

`core/evaluator.py` — pure, no-LLM metrics for regression and nightly eval:

- **Phrase echo** — user's distinctive words reused instead of clarified (opening mirror, same-stem repeats, hyphen-reduplication)
- **Question persistence** — asking again right after a complaint
- **Closure adherence** — short reply, no new question when the user says goodbye
- **Pet-name frequency** — "sayang" capped per message

`core/constraints.py` — hard reply requirements (no questions, forced closure) with turn-based TTL expiry.

## Evaluation Harness (nightly)

`tools/daily_eval.py` — scheduled 7-day eval (the personality core runs in an isolated sandbox with its own memory/state):

- **Probes** — casual, emotional, memory seed+recall, tool accuracy, boundary-AI, refusal, assistant-trap, conflict, complaint, repair, closure
- **Behavioral metrics** — question persistence, closure adherence, phrase echo
- **LLM-vs-LLM sim session** — optional; drives an "opponent" (OpenAI-compatible endpoint via `.env`) through banter turns to test long-session stability
- **State snapshot** — drift window, relationship dims, mode/stage before/after

`tools/sim_live.py` — manual single-turn banter against any OpenAI-compatible model.

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
flowchart LR
    Input([User Input]) --> Analyzer[analyzer.py<br/>emotion detection]
    Analyzer --> State[state.py<br/>relationship update + decay]
    State --> React{reaction<br/>override?}
    React -->|yes| Out([Return reaction])
    React -->|no| CogCheck{cognition<br/>needed?}
    CogCheck -->|yes| Cognition[cognition.py<br/>search - extract - summarize]
    CogCheck -->|no| ToolCheck{tool<br/>needed?}
    ToolCheck -->|calc/datetime/tavily| Tool[orchestrator.py<br/>run_tool]
    ToolCheck -->|no| Direct[direct chat]
    Cognition --> Prompt[prompting.py<br/>state to natural language]
    Tool --> Prompt
    Direct --> Prompt
    Prompt --> Agent[agent.py<br/>build prompt + history]
    Agent --> LLM[engine.py<br/>llama.cpp]
    LLM --> OutFinal([Response])
```

---

# Project Structure

```text
Veil/
├── app.py                          ← CLI entry point
├── app_tui.py                      ← TUI entry point (rich, split-panel)
├── config.py                       ← all tunables + .env
├── test_agent.py                   ← 141 deterministic assertions + 3 LLM-dependent
├── test_bench_reaction_guard.py    ← reaction-guard regressions (C1, 15 assertions)
├── test_memory_extraction_guard.py ← memory-extraction regressions (C2, 33 assertions)
│
├── core/
│   ├── bootstrap.py            ← App startup consolidation
│   ├── cognition.py            ← invisible search→extract→summarize
│   ├── orchestrator.py         ← pure infra boundary (run_tool)
│   ├── evaluator.py            ← behavioral metrics (phrase echo, closure, questions)
│   ├── constraints.py          ← hard reply requirements with TTL expiry
│   ├── formatter.py            ← tool-result formatting (text/json)
│   └── agent.py                ← LLM wrapper + history
│
├── llm/
│   └── engine.py               ← llama.cpp wrapper + sanitize
│
├── memory/
│   ├── emotional.py            ← valence/arousal records, salience filter
│   ├── extractor.py            ← keyword importance scoring + seed pairs
│   ├── short_term.py           ← 8-msg budget, chat-template format
│   ├── long_term.py            ← JSON, 500-fact cap, relevance injection
│   └── store.py                ← atomic persistence
│
├── personality/
│   ├── core.py                 ← coordinator: analyze → state → memory → tools → prompt → generate
│   │                             (owns emotion, conflict, inactivity, memory, tool routing,
│   │                              prompting and state persistence — see AGENT.md §Discrepancies)
│   ├── state.py                ← StellaIdentity + StellaState (5-dim, decay)
│   ├── analyzer.py             ← keyword → EmotionAnalysis
│   ├── prompting.py            ← state → natural language descriptor
│   ├── stella.py               ← identity constants (base, rules, safety) — hardcoded, see AGENT.md
│   ├── rules.py                ← centralized personality rules (v3.1)
│   ├── conflict.py             ← insult detection, cooling, recovery, drift
│   ├── persistence.py          ← save/load state.json (schema v3)
│   ├── inactivity.py           ← absence detection + relationship deltas
│   ├── initiative.py           ← probabilistic openers on user return
│   └── rhythm.py               ← priority matrix + mode modulation + reactions
│
├── tools/
│   ├── base.py                 ← BaseTool + ToolResult + ToolContext
│   ├── state_backup.py         ← manual backup/restore data/state.json
│   ├── bench.py                ← fixed-prompt benchmark (baseline comparison) — requires the GGUF
│   ├── ctx_report.py           ← context budget measurement (tokenizer-based)
│   ├── daily_eval.py           ← scheduled 7-day eval (probes + sim + metrics)
│   ├── sim_live.py             ← manual opponent banter (OpenAI-compatible)
│   ├── web/
│   │   └── search.py           ← Tavily REST + _CachedMixin
│   └── system/
│       ├── calculator.py       ← safe eval
│       └── datetime.py         ← WIB locale
│
├── utils/
│   ├── logger.py               ← structured logging
│   ├── async_utils.py          ← with_retry (used by search)
│   └── text.py                 ← LLM output sanitization (unicode, orphan punct, pet-name damper)
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
`nvidia-smi` header). Then ensure `VEIL_USE_GPU=1` — the default comes from
`config.py` (`USE_GPU`), not from `.env`.

If a bare `import llama_cpp` fails with *"Could not find module ... llama.dll"*,
that is the CUDA wheel's DLL dependency chain, not a missing model. It is normal
only if you never import `llm.engine`, which calls `_setup_cuda_paths()` first
to register the CUDA bin directories.

---

# Model Setup

Active model: **Qwen2.5-7B-Instruct-abliterated-v2 Q4_K_M GGUF**
(Rollback baseline: `qwen2.5-3b-instruct-q4_k_m.gguf`, see `BASELINE.md`.)

Place inside `models/`:
```
models/qwen2.5-7b-instruct-abliterated-v2-q4_k_m.gguf
```

Inference backend: llama.cpp via `llama-cpp-python`

## Model Integration Map

Where the model touches the codebase:

```text
config.py                    ← all model knobs
├── MODEL_PATH               models/qwen2.5-7b-instruct-abliterated-v2-q4_k_m.gguf
├── N_CTX=4096  N_THREADS    loaded by llm/engine.py LLMEngine.__init__
├── USE_GPU                  → n_gpu_layers=-1 when enabled (default on)
├── SAMPLING / MAX_TOKENS    merged in engine._default_params()
├── STOP_TOKENS              ["<|im_end|>"]
└── CTX_PROMPT_CHAR_LIMIT    char guard applied in core/agent.py (≈14.5k chars)

Call chain (one generation):
personality/core.py PersonalityCore.handle(user_input)
  → core/agent.py VeilAgent.generate(system, user_input, observation)
      builds raw ChatML (<|im_start|>system/user/assistant<|im_end|>)
      truncates history/prompt via _truncate() + CTX_PROMPT_CHAR_LIMIT
  → llm/engine.py LLMEngine.generate(prompt)
      llama_cpp.Llama(...) call with SAMPLING params (see "Temperature" below)

Persistence around it:
  state: personality/persistence.py ↔ data/state.json (schema v3)
  short-term memory: memory/short_term.py (8 messages, 500 chars/msg)
  long-term memory: memory/long_term.py ↔ memory/long_term.json
```

### Runtime notes

- **Temperature — configured default vs effective value (verified 2026-10-11).**
  `config.py` defaults `VEIL_TEMP` to `0.6`, chosen on 2026-08-26 after a live-sim
  showed word salad at 0.7 (MODEL-005). However a local `.env` currently sets
  `VEIL_TEMP=0.7`, and `.env` is gitignored — so on a machine carrying that file
  the **effective runtime temperature is 0.7, not the tuned 0.6**. The `0.6`
  default is unreachable there. Confirm which is in effect before recording any
  behavioural baseline.
- ChatML `/` matches Qwen2 template — any Qwen2-family GGUF is drop-in; other families need prompt-format changes.
- Context budget is enforced in **characters** (~4.0–4.1 chars/token for Indonesian), measured by `tools/ctx_report.py` — the assembled prompt stays under `CTX_PROMPT_CHAR_LIMIT` so prompt + streaming response fit `N_CTX` with headroom.
- N_CTX=4096 vs the model's larger trained context — headroom chosen for CPU/GPU speed on limited VRAM.

---

# Configuration

Main config in `config.py`:
- CPU thread allocation
- Sampling parameters (default temp 0.6 — **see "Temperature" in Runtime notes**;
  top_p 0.9, min_p 0.05, repeat_penalty 1.15)
- Context size (4096)
- Context guard (`CTX_PROMPT_CHAR_LIMIT` ≈ 14.5k chars, history soft budget 2.5k)
- Max tokens: 300 (normal), 400 (stream)
- Memory limits (8-message short-term, 500-fact long-term)
- Search timeout & cache size
- GPU mode toggle (`USE_GPU`, default yes)

Environment overrides:
```bash
USE_GPU=1              # GPU mode (default from config.py, not .env) | 0 = CPU-only
VEIL_TEMP=0.6          # .env wins over the code default when present
TAVILY_API_KEY=tvly-...
SIM_API_KEY=...        # OpenAI-compatible key for the eval sim opponent
SIM_BASE_URL=...       # e.g. https://api.groq.com/openai/v1
SIM_MODEL=...          # model name served by that endpoint
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

### Nightly evaluation
```bash
python tools/daily_eval.py --now          # run today's day immediately
python tools/daily_eval.py --schedule 21:00   # register a daily Windows task
```

Reports and data land in `logs/eval/`:
- `day_NN_YYYY-MM-DD.md` — human-readable report with probes, metrics, sim transcript, state before/after
- `responses.jsonl` — full per-probe rows (append-only, day-queried)
- `state_history.csv` — relationship dimension traces

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

**Verified 2026-10-15: 141 deterministic assertions pass.** The count rose from
138 when three context-boundary assertions were added. The suite is
self-contained — no network and no GGUF required for the deterministic portion.
That count was obtained from an isolated run with the model binding blocked and
writes redirected to a sandbox, **not** by running `test_agent.py` directly
against the production configuration.

- tool system — calculator + datetime
- long-term memory + fact extraction
- short-term memory overflow
- emotional analysis + state + emotional memory
- state backup/restore (checksum, tamper rejection, schema-version guard, v2→v3 migration)
- context budget guard
- conflict/cooldown/recovery + sanitizer + evaluator + constraints/TTL

The 3 **LLM-dependent end-to-end assertions** (chat, calculator-via-orchestrator,
streaming) require the GGUF and were **not run** during the Phase 0 audit; they
are reported separately rather than counted as passing.

## Regression runners (Phase 0)

Two narrower suites guard defects found during the Phase B benchmark investigation.
Both are **explicit runners**, not pytest modules — they define no `test_*`
functions and must be invoked directly:

```bash
python test_bench_reaction_guard.py     # 15 assertions, exit 0
python test_memory_extraction_guard.py  # 33 assertions, exit 0
```

Each `chdir`s into a fresh `%TEMP%` sandbox before importing, so relative paths in
`config` resolve outside the repository; both block `llama_cpp` so no GGUF is
opened, and both assert by digest that `memory/long_term.json`, `data/state.json`
and `logs/veil.log` are unchanged afterwards. Importing either module has no side
effects, so pytest collection runs nothing. **pytest is not installed in this
environment and `--collect-only` has not been run** — import safety was
verified by importing the modules directly, and the 15/15 and 33/33 results come
from manual invocation.

A third Phase 0 runner, `test_bench_output_guard.py`, guards the AUDIT-006
`--output` JSONL capture added to `tools/bench.py` — **88 assertions pass, 1
skipped** (the OS refused native symlink creation, so that branch is covered with
faked `os.path.islink` probes instead). A fourth, `test_bench_run_summary_guard.py`,
pins the `run` summary record and the close-then-append integrity rule —
**52 assertions pass**: a detected flush, close or append failure writes no `run`
record and exits 6. A fifth, `test_persona_guard.py`, covers the B-08 memory-
honesty guard, B-04/B-11/B-13 style rules, and `reset_session()` — **17
assertions pass**. All five are explicit runners, block `llama_cpp`, sandbox to
`%TEMP%`, run no inference, and do not evaluate any B-01…B-13 criterion.

`tools/bench.py` (13 fixed prompts, baseline comparison) requires the GGUF. It
**was executed against the current 7B model on 2026-10-15** — 13/13 prompts,
exit code 0 — from an isolated sandbox with production state, memory and logs
untouched. Its latency is monitor-contaminated; see `BASELINE.md` before using
the numbers.

---

# License

MIT License