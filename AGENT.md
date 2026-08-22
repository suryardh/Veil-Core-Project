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
