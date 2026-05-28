# Veil Architecture

## Overview

Veil is a **personality-centric local AI companion runtime**. It is designed as a persistent character system with emotional continuity.

The project shifted from an agent-framework approach (Phase 4.x) to a character-first architecture (Phase 5). The LLM is treated as a language generation engine; everything else — emotion, memory, cognition, state — is externalized.

---

# Core Philosophy

```
Character identity > capability
Capability is invisible
```

Key principles:

- **Personality is not a wrapper** — it is the main interface
- **Tools are subconscious** — executed behind the character, never visible
- **Emotional continuity** — state decays naturally, relationship progresses weighted by emotional depth
- **No mode switching** — dynamic state modulation replaces rigid mode toggles
- **No numeric values in prompts** — emotional state mapped to natural language descriptors

---

# High-Level Architecture

```mermaid
flowchart TB
    U["User Input"] --> PC["PersonalityCore"]

    subgraph PC["PersonalityCore (coordinator)"]
        direction TB
        AN["analyzer\nkeyword → valence/arousal"] --> ST["state\n5-dim relationship + decay"]
        ST --> EM["emotional\nsalience filter + record"]

        EM --> DEC{"should use\ncognition?"}

        DEC -->|yes| COG["cognition\nsearch → extract → summarize"]
        DEC -->|no| ROUTE{"tool\nneeded?"}

        ROUTE -->|calculator/datetime| ORCH["orchestrator\nrun_tool → ToolResult"]
        ROUTE -->|no| NONE[""]

        COG --> PR["prompting\nstate → nat lang"]
        ORCH --> PR
        NONE --> PR
    end

    PR --> AG["Agent.generate(system, input)"]
    AG --> LLM["LLM Engine\nllama.cpp + Qwen 3B"]
    LLM --> RES["Response"]

    style AG fill:#f3e5f5
    style LLM fill:#fce4ec
    style RES fill:#e8f5e9
    style COG stroke-dasharray:5 5
```

---

# Core Components

## 1. PersonalityCore (`personality/core.py`)

Thin coordinator — the "conscious mind" of the companion.

**Responsibilities:**
- Run emotion analysis on user input
- Update relationship state (affection, trust, attachment, comfort, dependency)
- Apply state decay
- Record emotional memory (if salience threshold met)
- Decide whether cognition (tools) is needed
- Route to cognition or direct tool call
- Compose final prompt via prompting module
- Call agent to generate response

**Flow:**
```python
class PersonalityCore:
    def handle(self, user_input: str) -> str:
        analysis = analyze(user_input)
        self.state.update_from_interaction(analysis.emotion, analysis.arousal, analysis.confidence)
        self.state.decay()
        if analysis.confidence >= 0.4:
            self.emotional_memory.record(...)
        self._update_baseline_mood()
        self._update_emotional_mode(analysis)
        rhythm = compute_rhythm(self.state, analysis)
        # Tool routing BEFORE cognition — calculator et al take priority
        if is_emotional: pass
        else:
            tool_result = self._route_tool(user_input)
            if tool_result:
                ctx = tool_result
            elif Cognition.can_handle(user_input):
                ctx = self.cognition.process(user_input)
        system = build_prompt(identity, state, emotional_summary, inactivity_ctx, rhythm)
        return self.agent.generate(system, user_input, ctx)
```

**Status:** IMPLEMENTED

---

## 2. State Machine (`personality/state.py`)

Two dataclasses: **StellaIdentity** (fixed traits) and **StellaState** (dynamic).

### StellaIdentity (permanent)
```python
@dataclass
class StellaIdentity:
    humor: float = 0.7
    warmth: float = 0.8
    teasing: float = 0.5
    emotional_openness: float = 0.6
    protectiveness: float = 0.7
```

### StellaState (per interaction)
```python
@dataclass
class StellaState:
    affection: float      # 0.0 → 1.0
    trust: float = 0.35   # 0.0 → 1.0; 0.35 prevents premature guarded
    attachment: float     # 0.0 → 1.0
    comfort: float        # 0.0 → 1.0
    dependency: float     # 0.0 → 1.0
    baseline_mood: str    # "warm" | "subdued" | "neutral" (from trailing 5 emotional records)
    emotional_mode: str   # "comforting" | "withdrawn" | "yearning" | "excited" | "soft" | "neutral"
    mode_strength: float  # 0.0 → 1.0; decays ×0.85/turn; resists overwrite when > 0.5
```

### State update rules
- **Positive** interaction → affection + trust + attachment + comfort + dependency increase
- **Intimate** interaction → stronger boost (especially attachment + affection)
- **Negative** interaction → affection - trust - comfort decrease
- **Confidence < 0.4** → no state update (ambiguity guard)

### Decay
Each dimension decays at a different rate per turn:
- `affection *= 0.998` — warms up fast, cools slow
- `trust *= 0.9995` — very slow to erode
- `comfort *= 0.997` — fades quickest
- Prevents permanent maxed state

### Stage label (derived, not linear)
```python
combined = (affection + trust*0.8 + attachment*0.6 + comfort*0.4 + dependency*0.3) / 3.1
# < 0.2 = kenalan
# < 0.4 = akrab
# < 0.6 = dekat
# < 0.8 = sayang
# >= 0.8 = istimewa
```

### Mood (emergent)
```python
dominant_mood() → "warm" | "playful" | "guarded" | "yearning" | "neutral"
```

Mood is derived from state combination, not set manually.

**Status:** IMPLEMENTED

---

## 3. Emotion Analyzer (`personality/analyzer.py`)

Keyword-based valence/arousal detection. Designed for deterministic, fast, cheap operation on local models.

### Output
```python
@dataclass
class EmotionAnalysis:
    emotion: str     # "positive" | "negative" | "intimate" | "neutral"
    valence: float   # -1.0 to 1.0
    arousal: float   # 0.0 to 1.0
    confidence: float # 0.0 to 1.0
```

### Detection method
- **Lexicon** — regex patterns mapped to emotion + valence + arousal
- **Negation patterns** — "ga sayang" overrides "sayang" (negative instead of intimate)
- **Emoji** — ❤, 😊, 😢, etc. with valence mapping
- **Intensifiers** — `!`, `??`, ALL CAPS boost arousal
- **Confidence** — proportion of words matched; low confidence → skip state update

### Example outputs
| Input | Emotion | Valence | Arousal |
|-------|---------|---------|---------|
| "hai apa kabar" | neutral | 0.0 | 0.1 |
| "aku sayang kamu" | intimate | 0.8 | 0.7 |
| "makasih ya" | positive | 0.6 | 0.3 |
| "kesel ah" | negative | -0.7 | 0.7 |
| "kamu ga sayang aku" | negative | -0.05 | 0.7 |

**Status:** IMPLEMENTED

---

## 4. Emotional Memory (`memory/emotional.py`)

Stores interactions with emotional weight. Separate from factual long-term memory.

### Schema
```python
@dataclass
class EmotionalRecord:
    type: str        # "interaction" | "compliment" | "conflict" | ...
    content: str
    valence: float
    arousal: float
    timestamp: float
    recurrence: int
```

### Salience filter
Only records where `abs(valence) * arousal * (1 + 0.2 * recurrence) >= 0.25` are stored. Prevents memory pollution from low-emotion chit-chat. Recurrence boost means repeated topics are weighted higher.

### Recurrence merging
If the same content appears within 1 hour, recurrence counter increments instead of creating a duplicate.

### Recall
- `recall_recent(n=5)` — most recent emotional records
- `recall_by_valence(min_valence)` — filter by emotional tone
- `emotional_summary()` — formatted for prompt injection

**Status:** IMPLEMENTED

---

## 5. Cognition (`core/cognition.py`)

Invisible search→extract→summarize subsystem. Replaces the old Planner with a much simpler design.

**What it does:**
- Triggered by keywords (rangkum, cari, jelaskan, search, etc.)
- Runs `web_search` → optionally `web_extract` → returns synthesized text
- Returns `str | None` — no DAG, no JSON, no ToolContext exposure
- Search query auto-cleaned via `_clean_query()` (`rfind`-based prefix stripping)

**What it does NOT do:**
- No visible execution traces
- No dependency graph
- No parallel levels
- No JSON planning
- No step enumeration

Cognition is called by PersonalityCore AFTER tool routing (calculator/datetime/tavily take priority). The result is injected after the user question as `Hasil pencarian:` — the LLM sees it as natural knowledge, not tool output.

**Status:** IMPLEMENTED

---

## 6. Orchestrator (`core/orchestrator.py`)

Pure infrastructure boundary. No personality, no cognition, no routing logic.

```python
class Orchestrator:
    def register_tool(self, name: str, func)
    def run_tool(self, name: str, input_: str = "") -> ToolResult
```

Methods return `ToolResult` directly. No formatting, no `chat_with_context`, no state recording. The Orchestrator is the stable backend API for future integrations (Discord, Web UI, TTS, etc.).

**Status:** IMPLEMENTED

---

## 7. Agent Layer (`core/agent.py`)

Prompt assembly and LLM interaction layer.

**Responsibilities:**
- Build prompt in Qwen Instruct format (`<|im_start|>`)
- Format history as chat-template blocks
- Context budgeting (system: 2k, history: 1.5k, response: 800)
- Sanitize model output (regex + split on first `<|im_end|>`)
- Update short-term memory

**Key methods:**
- `generate(system: str, user_input: str) → str` — takes fully composed system prompt, generates response
- `chat_stream(user_input: str)` — streaming with token yield

**Removed from agent:**
- `chat_with_context()` — replaced by `generate()`
- `ToolContext` injection — moved to PersonalityCore + Cognition
- `mode` parameter — replaced by dynamic state
- `_build_raw_metadata()` — no longer needed

**Status:** IMPLEMENTED

---

## 8. Personality Identity (`personality/stella.py`)

Module-level constants only. No class, no `build_prompt()`.

```python
BASE_IDENTITY      — "You are Stella, a human-like AI companion..."
LANGUAGE_RULES     — Indonesian-first, casual internet style
BEHAVIOR_RULES     — Natural flow, adaptive tone, NSFW allowed, no AI mention
```

Used as reference by `prompting.py` when composing the final prompt with dynamic state context.

**Status:** IMPLEMENTED

---

## 9. Prompt Composition (`personality/prompting.py`)

Builds the final system prompt from components:

```python
def build_prompt(identity_blob, state, emotional_context, user_input, cognition_context) -> str
```

- **`describe_state(state)`** — state → natural language (no numeric values)
  - `"Stella feels warm and affectionate right now. You are at the 'sayang' stage."`
- **Mood descriptors** — maps `dominant_mood()` to a natural sentence
- **Cognition injection** — "Relevant factual context:" block (only if tools were used)
- **Emotional context** — "Recent emotional context:" block with summary

Max 3-5 dynamic variables injected to prevent prompt drift on Qwen 3B.

**Status:** IMPLEMENTED

---

## 10. Memory Extractor (`memory/extractor.py`)

Structured fact extraction from natural language before storage.

### `extract_fact(text)`
```python
>>> extract_fact("tolong ingat kalau aku suka kopi")
{"type": "preference", "content": "Aku suka kopi", "importance": 3, "tags": ["preference"]}
```

### Classification
| Type | Keywords |
|------|----------|
| `personal_info` | nama, umur, alamat, name, age |
| `preference` | suka, cinta, favorit, like, love |
| `reminder` | besok, meeting, jam, remind |
| `general` | fallback |

### Importance scoring
| Level | Criteria |
|-------|----------|
| 4 | Personal info (nama, umur, alamat) |
| 3 | Preferences (suka, cinta, favorite) |
| 2 | Reminders + dispreferences |
| 1 | General + short statements |

**Status:** IMPLEMENTED

---

## 11. Long-Term Memory (`memory/long_term.py`)

Persistent JSON-backed fact storage.

Features:
- timestamped memories
- importance scoring (1–4, from extractor)
- deduplication
- capped at 500 facts, injects max 10
- per-tier quota: 5 most important + 5 most recent (prevents importance shadowing)
- explicit `importance` parameter

**Status:** IMPLEMENTED

---

## 12. Short-Term Memory (`memory/short_term.py`)

Recent conversation history management.

Features:
- 4k character budget
- Ignores low-value messages (< 30 chars, no alpha chars, generic greetings after first)
- Truncates long messages (> 500 chars)
- Chat-template format output

**Status:** IMPLEMENTED

---

# Tool System

## 13. BaseTool + ToolResult + ToolContext + ToolRegistry (`tools/base.py`)

### ToolResult
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

### ToolContext (internal only)
```python
@dataclass
class ToolContext:
    tool: str
    formatted: str
    raw: Any = None
    success: bool = True
    source: str = ""
    error: str | None = None

    @classmethod
    def from_result(cls, tool, result, *, label="") -> ToolContext: ...
    @classmethod
    def from_error(cls, tool, error, *, label="") -> ToolContext: ...
```

### ToolRegistry
```python
class ToolRegistry:
    def register(self, tool: BaseTool)
    def describe_for_planner(self) -> str  # dynamic tool descriptions
```

**Status:** IMPLEMENTED

## 14-17. Web Tools (`tools/web/search.py`)

- `WebSearchTool` — Tavily `/search`, Bearer auth, TTL cache, retry wrapper
- `WebExtractTool` — Tavily `/extract`, URL content extraction
- `TavilyUsageTool` — Tavily `/usage`, quota check

All use `_CachedMixin` (TTL 3600s) and `with_retry()` (1 retry, 1s backoff).

**Status:** IMPLEMENTED

## 18. CalculatorTool (`tools/system/calculator.py`)

Safe eval: restricted globals, math function whitelist, percentage parsing, injection blocking.

## 19. DateTimeTool (`tools/system/datetime.py`)

WIB (UTC+7), Indonesian locale (Senin, Selasa, ..., Januari, ...).

---

# Execution Flow

```mermaid
flowchart LR
    USER["User"] --> PC["PersonalityCore.handle()"]

    PC --> A["inactivity effect\nabsence → trust/attachment delta"]
    A --> B["analyze()\n→ EmotionAnalysis"]
    B --> C["state.update()\n+ decay()"]
    C --> D{"salience\n>= 0.25?"}
    D -->|yes| E["emotional.record()\n+ recurrence boost"]
    D -->|no| F["_update_baseline_mood()\n_update_emotional_mode()"]
    E --> F

    F --> G["is_emotional?\nvalence/arousal gate"]
    G -->|yes| H["skip search"]
    G -->|no| I["_route_tool()\ncalc → datetime → tavily"]
    I -->|hit| J["Tool result → ctx"]
    I -->|miss| K["Cognition.can_handle()"]
    K -->|yes| L["cognition.process()\ninvisible search→extract"]
    K -->|no| M[""]

    J --> N["build_prompt()\nstate → nat lang + rhythm"]
    L --> N
    M --> N

    N --> O["Agent.generate()"]
    O --> P["LLM inference"]
    P --> Q["_clean_response()"]
    Q --> R["short_memory.add()"]
    R --> S["Response"]

    style L stroke-dasharray:5 5,fill:#fff3e0
    style Q fill:#e1f5fe
    style P fill:#fce4ec
    style S fill:#e8f5e9
```

---

# Key Differences from Phase 4.x

| Aspect | Phase 4.x (Agent Framework) | Phase 5 (Companion) |
|--------|----------------------------|---------------------|
| Entry point | `Orchestrator.handle()` | `PersonalityCore.handle()` |
| Tool routing | IntentRouter (regex) | Analyzer + Cognition |
| Planner | DAG, JSON planning, parallel | Invisible cognition |
| Modes | casual / flirty / dark / ... | Dynamic state modulation |
| Emotional model | None (factual only) | Valence/arousal + relationship state |
| Tool visibility | `=== Planner execution ===` | Never visible |
| Orchestrator role | Coordinator + personality | Pure infra boundary |
| State management | SessionState + ref resolution | Relationship state + emotional memory |
| Test count | 30 | 38 (all passing) |

---

# Development Roadmap

## Phase 5 (Current) — Personality-Centric Rewrite
- [x] Emotion analyzer (keyword → valence/arousal)
- [x] State machine (identity + relationship dynamics)
- [x] Emotional memory (salience filter, recurrence)
- [x] Cognition (invisible search→extract→summarize)
- [x] Prompt composer (state → natural language)
- [x] PersonalityCore coordinator
- [x] Orchestrator as pure infra boundary
- [x] Remove IntentRouter, Planner, StateManager

## Phase 6 — Emotional Depth
- Relationship drift detection
- Conflict/reconciliation dynamics
- Long-term emotional arcs (attachment styles)
- User preference learning

## Phase 7 — Multi-Platform
- Discord integration
- TTS voice
- Web UI
- Mobile app

## Phase 8 — Memory Evolution
- Semantic memory (embeddings)
- Emotional→factual memory cross-reference
- Dream/consolidation cycles

---

# Current State

## Complete
- Local LLM inference with streaming
- Stella identity (Indonesian-first companion)
- Emotion analysis (4 emotions, valence/arousal)
- Relationship state (5 dimensions, decay, stage label)
- Mood modulation (5 moods, emergent)
- Emotional mode system (6 modes, mode_strength decay 0.85, overwrite guard > 0.5)
- Emotional memory (salience filter 0.25, recurrence boost, recurrence merging)
- Short-term memory (ignore/truncate)
- Long-term memory (JSON, per-tier quota 5+5, dedup)
- Fact extraction (type, importance, framing strip)
- Inactivity effects (severity-scaled trust/attachment deltas, absence bucket guard)
- Initiative system (probabilistic openers, 5 relationship-aware branches)
- Rhythm system (7-priority matrix, mode modulation, reaction cooldowns)
- Baseline mood (trailing 5 emotional records, time-weighted)
- Cognition (invisible search→extract→summarize, rfind-based query cleaning)
- Tool routing priority (calculator/datetime/tavily before cognition)
- Orchestrator (pure infra boundary)
- ToolContext + ToolResult + ToolRegistry
- Web search (Tavily, TTL cache, retry, prefix stripping)
- Calculator (+ sqrt/sin/cos/%, injection blocked)
- Datetime (WIB Indonesian locale)
- Prompt composition (state → natural language, rhythm style, inactivity context)
- Agent layer (Qwen format, context budgeting, response cleanup)
- Schema-versioned persistence (v2, baseline_mood migration)
- Automated testing (38 assertions passing)

## In Progress
- Emotional depth (arcs, attachment, conflict)
- Multi-platform (Discord, TTS)
- Semantic memory

---

# Recommended Model

**Qwen2.5-3B-Instruct GGUF (Q4_K_M)**

Inference backend: llama.cpp + llama-cpp-python

---

# Final Notes

Veil is a research-oriented modular local AI companion runtime.

The shift from agent-framework to character-first architecture reflects the understanding that **for companion AI, identity is more important than capability**. Capability exists to serve the character, not the other way around.

The long-term goal is a persistent emotional entity that lives locally, respects privacy, and evolves naturally through interaction.
