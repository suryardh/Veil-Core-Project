# Veil 2.0 — Character Runtime Plan

> Status: Planning
> Goal: Rework Veil from a Stella-specific AI companion into a reusable character-first runtime for persistent roleplay characters and AI VTuber-style personalities.

## 1. Product Direction

Veil is a character runtime, not merely an LLM wrapper. The LLM provides language/reasoning; Veil owns character identity, memory, emotional state, relationships, continuity, behavior, and presentation-neutral runtime logic.

Core principles:

```text
Character > model
Memory > chat history
State > static prompt
Runtime > one-off chatbot
```

A character should remain recognizable when the underlying model changes.

## 2. Target Architecture

```text
                    VEIL RUNTIME
                         |
        +----------------+----------------+
        |                |                |
   Character         Memory           State / Emotion
     Engine           Engine              Engine
        |                |                |
        +----------------+----------------+
                         |
                  Context Builder
                         |
                  Conversation Core
                         |
              +----------+----------+
              |                     |
         LLM Runtime          Cognition / Tools
              |                     |
              +----------+----------+
                         |
                 Response Evaluator
                         |
                  Runtime Response
                         |
              +----------+----------+
              |          |          |
             CLI        Web      VTuber/Voice
```

Core subsystems must be replaceable and independently testable.

## 3. Character Abstraction

Remove Stella-specific assumptions from generic runtime code.

Target structure:

```text
characters/
  stella/
    character.yaml
    personality.yaml
    lore.yaml
    rules.yaml
  loader.py
```

A character definition should contain:

- identity
- personality traits
- speech style
- lore/world knowledge
- behavioral rules
- boundaries
- relationship defaults
- optional emotional configuration

Stella becomes a character profile loaded by Veil, not the identity of Veil itself.

## 4. Runtime State

Separate immutable character definition from mutable interaction state.

### Character definition

Stable traits such as:

- warmth
- humor
- curiosity
- teasing
- values
- speech style

### Character state

Dynamic values such as:

- mood
- energy
- affection
- trust
- attachment
- comfort
- current conversational context
- temporary emotional intensity

State transitions should be deterministic and testable where practical.

## 5. Memory 2.0

Memory remains external to the model.

Recommended categories:

- `fact` — stable user information
- `preference` — likes/dislikes
- `event` — meaningful past events
- `relationship` — relationship-relevant history
- `emotional` — emotionally salient interactions
- `conversation` — short-term context
- `lore` — character/world information

Target pipeline:

```text
Conversation
    |
Memory Extraction
    |
Validation / Importance
    |
Persistence
    |
Retrieval / Ranking
    |
Context Builder
```

Keep the current persistence mechanism where practical. Move to SQLite and semantic/hybrid retrieval only when measurements justify the added complexity.

## 6. Emotion & Relationship

Keep the existing deterministic emotional system as a baseline, but move it behind clear service boundaries.

```text
User Input
    |
Emotion Interpreter
    |
Relationship Update
    |
State Transition
    |
Context
```

The current keyword analyzer can remain as a cheap fallback. Future implementations may use a small classifier or LLM-assisted interpretation.

Do not require a trained emotion model for the first milestone.

## 7. Context Builder

The LLM should receive only context relevant to the current turn:

```text
Character Definition
+ Current State
+ Relevant Memories
+ Recent Conversation
+ Cognition / Tool Results
+ Current User Input
        |
       LLM
```

Never dump the entire memory store into every prompt.

## 8. LLM Abstraction

Veil must not depend on one model family.

Provide a stable interface for local and remote backends, such as:

- llama.cpp / GGUF
- OpenAI-compatible APIs
- other local inference servers

Model fine-tuning is optional and must never be a runtime requirement.

## 9. Fine-Tuning Strategy

Do **not** begin with CPT/SFT/LoRA.

First establish a baseline using:

1. character definition
2. memory
3. state
4. context construction
5. response evaluation

Only then benchmark tuning.

Possible later path:

```text
Character conversations
        |
Dataset cleaning
        |
SFT / LoRA experiment
        |
Character consistency benchmark
        |
Optional character adapter
        |
Veil LLM backend
```

CPT should only be considered when there is a clear domain/style corpus large enough to justify continued pretraining.

## 10. Response Evaluation

Add a lightweight evaluator after generation.

Evaluate:

- character consistency
- speech-style consistency
- lore consistency
- state consistency
- memory consistency
- unwanted prompt/model drift

The evaluator may request regeneration, but retries must be bounded.

## 11. VTuber Readiness

The runtime should eventually be able to emit structured response metadata:

```json
{
  "text": "...",
  "emotion": "happy",
  "intensity": 0.7,
  "expression": "smile",
  "action": "wave"
}
```

This allows later adapters for:

- TTS
- STT
- Live2D
- VRM
- streaming overlays
- Discord/Telegram/Web clients

The core runtime must remain usable without an avatar.

## 12. Migration Phases

### Phase 0 — Architecture Freeze

- Document subsystem boundaries and contracts.
- Add/repair tests around existing behavior.
- Avoid unrelated feature work while core boundaries are changing.

### Phase 1 — Character Runtime

- Introduce generic character schema.
- Extract Stella into a character profile.
- Remove Stella-specific imports from generic core modules.
- Add character loader and validation.

### Phase 2 — State & Relationship Service

- Separate identity from mutable state.
- Extract state transitions from `PersonalityCore`.
- Preserve useful existing decay and relationship behavior.
- Add deterministic unit tests.

### Phase 3 — Memory 2.0

- Define unified memory schema.
- Keep emotional and factual memories distinct.
- Add retrieval/ranking interfaces.
- Introduce semantic retrieval only after a measurable baseline.

### Phase 4 — Conversation / Context Pipeline

- Introduce a dedicated conversation coordinator.
- Build context through explicit stages.
- Keep tools/cognition separate from character-facing output.
- Make context assembly independently testable.

### Phase 5 — Character Consistency

- Add evaluator interface.
- Build a small benchmark dataset.
- Measure personality, lore, state, and memory consistency.
- Add bounded regeneration.

### Phase 6 — Model Layer

- Formalize the LLM backend interface.
- Keep llama.cpp working.
- Add another backend only when useful for comparison.

### Phase 7 — Training Experiments

- Create reproducible dataset/evaluation tooling.
- Compare base model vs LoRA/SFT.
- Keep training assumptions outside runtime architecture.

### Phase 8 — Voice & Presence

- TTS adapter.
- STT adapter.
- Structured emotion/expression output.
- Idle/initiative events.

### Phase 9 — VTuber / Platform Adapters

- Live2D/VRM adapter.
- Web UI.
- Discord/Telegram adapters.
- Streaming integration.

## 13. Definition of Done for Veil 2.0 Core

- A character can be loaded without changing runtime source code.
- Stella is only one character profile.
- Character state survives process restarts.
- Important memories survive process restarts.
- Relevant memories can be retrieved without injecting the entire store.
- The LLM backend can be replaced behind an interface.
- Core logic is testable without a live model.
- Character consistency has a measurable benchmark.
- Tools/cognition do not leak implementation details into character responses.
- The runtime can emit structured emotion/action metadata without requiring a VTuber frontend.

## 14. Non-Goals for the First Core Milestone

Do not prioritize:

- full autonomous agents
- multi-agent orchestration
- unrestricted computer control
- full model pretraining
- full CPT pipelines
- complex planning DAGs
- avatar rendering inside the core
- a massive vector database before retrieval needs are proven

## 15. Engineering Rules

- Prefer simple, observable systems over clever abstractions.
- Keep character data separate from runtime logic.
- Keep memory separate from prompts and model weights.
- Keep state transitions deterministic where possible.
- Every major subsystem needs a clear interface and tests.
- Measure before replacing a working subsystem.
- Do not introduce fine-tuning merely because prompting feels imperfect.
- Preserve backwards compatibility where practical during migration.
| Invisible Search Cognition | OK | `core/cognition.py` |
| Tool Routing | OK | `core/orchestrator.py` (termasuk `is_..._query` functions) |
| Tool Resilience (with_retry) | OK | `utils/async_utils.py` |
| **Memory** | OK | |
| Scoring-based Recall (LTM) | OK | `memory/long_term.py` |
| Short-Term Memory (STM) | OK | `memory/short_term.py` |
| **User Interface** | OK | |
| CLI + TUI Entry Points | OK | `app.py`, `app_tui.py` |
| **Utilities** | OK | |
| Structured Logging | OK | `utils/logger.py` (sekarang pakai `RichHandler`) |
| Text Sanitization | OK | `utils/text.py` (baru, sentralisasi) |
| **Testing** | PARTIAL | 44/45 passing (1 expected LLM-dependent failure) |

---

## Future Roadmap: Human-like AI

Tujuan utama: Membuat AI terasa seperti manusia.

### Phase 6 -- Foundation Upgrade (Quick Wins)

Tujuan: Meningkatkan fondasi inti untuk mendukung pengalaman yang lebih mirip manusia.

| Feature | Description | Status | Priority |
|---|---|---|---|
| **Context Window Full Utilization** | Memanfaatkan kapasitas penuh `n_ctx` model (32k) untuk pemahaman konteks jangka panjang yang lebih baik. | NOT STARTED | High |
| **User Profile Auto-Building** | Otomatis mengekstrak dan menyimpan profil terstruktur user (hobi, pekerjaan, preferensi, dll.) dari percakapan. | NOT STARTED | Medium |
| **Semantic Memory Retrieval** | Mengganti sistem pencarian memori berbasis keyword dengan metode semantik (e.g., embeddings) untuk recall yang lebih relevan. | NOT STARTED | Medium |
| **Personality Drift Engine** | Mengembangkan sistem agar trait kepribadian Stella (humor, warmth, dll.) dapat beradaptasi dan berubah secara halus berdasarkan interaksi. | NOT STARTED | Medium |
| **Implicit & Explicit Feedback Loop** | Memungkinkan user memberi rating respons dan Stella secara otomatis belajar dari reaksi user. | NOT STARTED | Medium |

### Phase 7 -- Voice & Presence

Tujuan: Memberikan Stella "suara" dan kehadiran yang lebih nyata.

| Feature | Description | Status | Priority |
|---|---|---|---|
| **Local TTS Integration** | Integrasi Text-to-Speech lokal (e.g., Piper, Coqui) agar Stella dapat merespons dengan suara. | NOT STARTED | High |
| **Speech Recognition** | Integrasi Speech-to-Text lokal (e.g., Whisper) untuk input suara dari user. | NOT STARTED | High |
| **Background Idle Chatter** | Saat tidak ada interaksi, Stella sesekali mengeluarkan komentar spontan (nguap, observasi) untuk menciptakan rasa kehadiran. | NOT STARTED | Medium |
| **Active Notification System** | Stella dapat memicu percakapan atau memberi notifikasi aktif berdasarkan informasi yang ia proses (selain dari inactivity). | NOT STARTED | Low |

### Phase 8 -- Desktop Companion & Environmental Awareness

Tujuan: Menjadikan Stella bagian dari lingkungan desktop user.

| Feature | Description | Status | Priority |
|---|---|---|---|
| **Desktop Overlay** | Antarmuka visual sederhana (e.g., floating window) untuk menampilkan avatar atau mood Stella di desktop. | NOT STARTED | Medium |
| **Screen Context Awareness** | Kemampuan untuk memproses screenshot periodik untuk memahami apa yang sedang user lihat/kerjakan. | NOT STARTED | Medium |
| **Mouse/Keyboard Observation** | Mendeteksi aktivitas user (idle vs. aktif) melalui input mouse/keyboard untuk interaksi yang lebih alami. | NOT STARTED | Low |
| **Basic Computer Control** | Stella dapat melakukan tugas-tugas sederhana di komputer (membuka aplikasi, mencari file, membaca clipboard). | NOT STARTED | Low |

### Phase 9 -- Autonomy & Advanced Adaptation

Tujuan: Membangun otonomi dan kemampuan adaptasi yang lebih kompleks.

| Feature | Description | Status | Priority |
|---|---|---|---|
| **Multi-threaded Conversation** | Stella dapat mengelola beberapa topik atau tugas secara bersamaan dalam satu percakapan. | NOT STARTED | Medium |
| **Adaptive Personality Calibration** | Fine-tune kepribadian secara dinamis berdasarkan interaksi jangka panjang dengan user. | NOT STARTED | Low |
| **Self-Improvement Loop** | Sistem di mana Stella dapat mengevaluasi kualitas responsnya sendiri dan belajar dari kesalahan. | NOT STARTED | Low |

### Phase 10 -- Platform Expansion & Visual Presence

Tujuan: Membawa Stella ke berbagai platform dan menambahkan aspek visual yang lebih kaya.

| Feature | Description | Status | Priority |
|---|---|---|---|
| **Discord/Telegram Integration** | Menjadikan Stella sebagai bot di platform chat populer. | NOT STARTED | Medium |
| **VRM/Live2D Avatar** | Integrasi avatar visual (2D/3D) untuk tampilan yang lebih menarik dan ekspresif. | NOT STARTED | Low |

---

## Technical Debt & Refinement Backlog

Daftar hal-hal yang perlu diperbaiki atau ditingkatkan secara teknis.

| Item | Description | Priority |
|---|---|---|
| **Fragile LLM Test** | Test `calculator via orch` di `test_agent.py` terlalu kaku dan sering gagal karena sifat model. Perlu diubah untuk memeriksa *intent* (apakah tool dipanggil) bukan output. | Medium |
| **Hardcoded CUDA Paths** | `_setup_cuda_paths()` di `llm/engine.py` kurang portabel. Cari cara yang lebih robust untuk mendeteksi path CUDA. | Low |
| **API Key Validation** | Tidak ada validasi untuk `TAVILY_API_KEY` saat startup. Tambahkan warning jika kosong. | Low |
| **`with_retry` Utility** | `utils/async_utils.py` adalah implementasi custom. Pertimbangkan untuk menggantinya dengan library standar seperti `tenacity` jika kebutuhan retry menjadi lebih kompleks. | Very Low |
| **Cache TTL Logic** | `_CachedMixin` di `tools/web/search.py` adalah implementasi custom. Jika butuh cache yang lebih canggih, pertimbangkan `cachetools` (membutuhkan dependensi baru). | Very Low |

---

## Refactoring & Cleanup Log 

- **DELETED**: `vision/` directory (semua file stub).
- **DELETED**: `tools/registry.py` (legacy code).
- **DELETED**: `core/setup.py` (digantikan `core/bootstrap.py`).
- **REFACTORED**: `app.py` & `app_tui.py` sekarang menggunakan `core/bootstrap.py` untuk startup.
- **REFACTORED**: `memory/emotional.py` & `personality/persistence.py` sekarang menggunakan `memory.store.JSONStore` untuk file I/O.
- **REFACTORED**: `utils/logger.py` sekarang menggunakan `rich.logging.RichHandler` untuk output console.
- **CREATED**: `utils/text.py` untuk sentralisasi `sanitize_llm_output`.
- **MOVED**: Logic `is_..._query` dari `personality/core.py` ke `core/orchestrator.py`.

---

## Archived Phases

- **Phase 2: Agentification**
- **Phase 3: Proto-Agent**
- **Phase 4: Overengineering Era**

(Detail dari fase-fase ini bisa dilihat di versi lama workplan jika dibutuhkan, tapi sudah dihapus dari dokumen ini untuk kejelasan.)
