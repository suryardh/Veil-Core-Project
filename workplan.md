# Veil Roadmap — Full Phase Timeline

> Semua fase di bawah mencerminkan apa yang benar-benar terjadi pada proyek ini.
> Fase yang ditandai 🗑️ adalah dead code yang sudah dihapus di rewrite.

---

## Phase 1 — Foundation ✅

**Goal:** local AI companion minimum viable yang bisa ngobrol + pakai tools dasar.

### 1.0 — Core Skeleton
- `app.py`
- CLI loop
- basic local LLM wrapper
- chat history memory
- config/env loading

### 1.1 — Tool System
- Tool registry
- Base tool abstraction
- Calculator tool
- Datetime tool
- Web search tool

### 1.2 — Formatting Layer
- `formatter.py`
- standardized tool outputs
- tool result rendering

### 1.3 — Memory v1
- short-term memory
- long-term factual memory
- memory extraction
- JSON persistence awal

### 1.4 — Personality Wrapper v1
- Stella personality prompt
- mode system (casual, flirty, dark, serious, roleplay)

---

## Phase 2 — Agentification 🗑️

**Goal:** bikin assistant terasa "agentic".

Semua file di fase ini **dihapus total** di Phase 5 rewrite. Tidak ada satupun yang dipakai di arsitektur saat ini.

- `intent_router.py` — diganti analyzer keyword-based
- `state_manager.py` — tidak ada state management terpusat lagi
- `router.py` — routing logic dipindah ke PersonalityCore
- `runtime.py` — runtime orchestration dihapus
- `ToolContext` injection — diganti inline tool routing

---

## Phase 3 — Proto-Agent 🗑️

**Goal:** multi-step reasoning sederhana — **tidak pernah stabil, diganti cognition**.

### 3.0 — Planner v1 (deleted)
### 3.1 — Sequential Execution (deleted)
### 3.2 — Search Quality (retries dipindah ke search.py)
### 3.3 — MCP Integration (cancelled — never implemented)

---

## Phase 4 — Overengineering Era 🗑️

**Goal:** full autonomous agent framework — **gagal total, dihapus semua**.

Semua komponen di bawah ini dihapus di Phase 5 rewrite:
- `planner.py` (DAG planning, JSON schema, step references)
- Reflection layer
- Async / parallel execution
- Structured synthesis & execution traces
- Router/runtime abstraction
- Planner stabilization

Pelajaran: complexity tanpa personality system tidak menghasilkan companion yang baik.

---

## Phase 5 — Personality System Rewrite ✅

**Major pivot:**

```
agent framework with personality
  → personality system with capabilities
```

Semua dikerjakan ulang dari nol. File baru, arsitektur baru.

---

### 5.0 — Architecture Rewrite ✅

**New files:**
- `personality/core.py` — thin coordinator
- `personality/state.py` — StellaState (5-dim relationship)
- `personality/analyzer.py` — keyword → emotion
- `personality/prompting.py` — state → natural language
- `personality/cognition.py` — invisible search→extract→summarize
- `memory/emotional.py` — valence/arousal records

**Deleted:**
- `planner.py`, `intent_router.py`, `runtime.py`, `router.py`, `state_manager.py`

---

### 5.1 — Persistence ✅

- `data/state.json`
- Schema versioning (v1→v2)
- baseline_mood, emotional_mode, mode_strength
- Migration registry dengan `_register()` decorator

---

### 5.2 — Temporal Awareness ✅

- Initiative system — probabilistic openers, relationship-aware
- Inactivity evolution — yearning/withdrawn/soft/guarded, severity-scaled
- Initiative throttle (300s cooldown)

---

### 5.3 — Rhythm Layer ✅

- RhythmConfig (verbosity, cadence, energy, tone)
- Reaction override — instant response tanpa LLM
- Emotional modes — comforting/yearning/excited/withdrawn/soft, decay ×0.85/turn

---

### 5.4 — Search & Cognition Stabilization ✅

- Proper ChatML roles untuk search results
- TavilyUsage tool + quota checking
- Emotional gate — skip search untuk high-valence/arousal input
- Multi-pass `_clean_query()` untuk nested prefix stripping

---

### 5.5 — Stabilization Pass ✅

Bugfixes (pre-CoRT):
- Initiative timer reset
- Inactivity stacking guard
- Cognition eagerness (emotional gate)
- Absence re-trigger loops

---

### 5.6 — CoRT Quality Sprint ✅

**Chain of Recursive Thinking — systematic bug hunt, 3 passes.**

| Pass | Temuan | Status |
|------|--------|--------|
| 1 | 51 bugs (5 high, 12 medium, 34 low) | Semua high+medium fixed |
| 2 | 2 regressions dari pass 1 | Fixed |
| 3 | 0 residual | Clean |

**Key fixes:**
- Observation context antar turn (agent.py)
- Negation override hanya jika neg_count >= non_neg_count (analyzer.py)
- Multi-pass query cleaning (search.py)
- Valence/arousal update on recurrence (emotional.py)
- print() → log.warning() (store.py)
- "User:" prefix stripped sebelum IGNORE_MESSAGES (short_term.py)
- +10 lainnya

---

### 5.7 — Post-CoRT Quality Sprint ✅

**Config & Bootstrap**
- MAX_TOKENS: 150→300, MAX_TOKENS_STREAM: 200→400
- CTX_BUDGET_HISTORY: 1500→2500, CTX_BUDGET_SYSTEM: 2000→2500
- Model file existence check

**Tool Resilience**
- with_retry di semua path `_route_tool()`

**Memory**
- Scoring-based recall: `match_ratio × 0.7 + importance × 0.3`
- Top 10 results (dulu binary filter + 5+5 quota)

**Lexicon**
- 27→57 entries: semangat, hebat, keren, takut, cemas, bosan, dll
- Multi-word negation: gak mau, ga peduli

**Persistence**
- Migration registry with `_register()` decorator

**TUI**
- `app_tui.py` — rich-based split-panel
- Emotional state header, colored conversation history

**Testing**
- 38→43 assertions, all passing

---

### 5.8 — Optional Presence Layer ❌ (optional)

Screen capture + OCR + activity understanding.
Belum dikerjakan — murni optional.

---

### 5.9 — Platform Expansion ❌

| Platform | Status |
|----------|--------|
| Discord | ❌ |
| Telegram | ❌ |
| TTS (Piper / Coqui) | ❌ |

---

## Phase 6 — Long-Term Companion Intelligence 🔄

(Future / experimental)

| Area | Status |
|------|--------|
| Emotional arc system (loneliness, closeness, drifting) | 🔄 partial foundation |
| Memory consolidation (emotional→factual) | ❌ |
| Routine modeling | ❌ |
| Adaptive speech evolution | ❌ |
| Local multimodal (voice + vision + screen) | ❌ |

---

# Current State

| Area | Status |
|------|--------|
| Emotional state (5-dim + decay + stage) | ✅ |
| Emotional memory (salience filter, recurrence) | ✅ |
| Persistence + schema migration | ✅ |
| Initiative + throttle | ✅ |
| Inactivity evolution | ✅ |
| Rhythm layer + reaction override | ✅ |
| Emotional modes (6 modes, decay 0.85) | ✅ |
| Search cognition (invisible search→extract) | ✅ |
| Temporal layering (instan / cross-turn / long-term) | ✅ |
| CoRT bug hunt (51 bugs fixed) | ✅ |
| Lexicon (57 entries, multi-word negation) | ✅ |
| Scoring-based memory recall | ✅ |
| Tool retry resilience | ✅ |
| CLI + TUI | ✅ (app.py + app_tui.py) |
| Automated tests | ✅ 43/43 passing |
| Screen awareness / vision | ❌ optional |
| Discord / Telegram | ❌ |
| Voice / TTS | ❌ |
| Long-term emotional arcs | 🔄 partial |
