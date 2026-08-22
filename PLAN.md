# Veil Core — Plan

> Living document. Update whenever priorities or architectural decisions change.
> `AGENT.md` remains the source of truth for engineering rules and architecture.
> This document defines **what we prioritize and why**.

---

## Product Direction

Veil Core is a reusable character runtime for persistent roleplay / AI companion experiences, with future support for AI VTuber-style presentation.

The immediate objective is not to build every platform or train a model. It is to make the existing character brain substantially better:

```text
Model quality
    ↓
Emotional depth
    ↓
Memory quality
    ↓
Character consistency
    ↓
Platform / presentation
```

The runtime should remain model- and platform-independent where practical.

---

## Priority Principles

1. **Brain before surface** — mature personality, emotional state, relationship, and memory before adding platforms or presentation layers.
2. **High ROI first** — prioritize changes that directly improve companion quality.
3. **Cheap and reversible before expensive and irreversible** — prompting and runtime improvements before fine-tuning.
4. **Measure before optimizing** — qualitative observations should become specific, reproducible failure cases where possible.
5. **Protect relationship data** — `state.json` and future persistent memory represent accumulated interaction history and must be treated as valuable data.
6. **Incremental migration** — improve the existing implementation rather than rewriting working systems without evidence.
7. **Model independence** — the character runtime must not become tightly coupled to one model.
8. **Presentation independence** — TTS, avatars, Web UI, Discord, WhatsApp, and mobile clients should consume the runtime rather than own its character logic.

---

# Phase 1 — Model Migration

## Qwen 7B Evaluation

Move from the current 3B model to a suitable Qwen 7B GGUF candidate, initially targeting Q4_K_M-class quantization.

The exact model variant must be selected through evaluation rather than assuming that every Qwen 7B variant behaves identically.

### Why first?

All later work depends on the model's baseline ability to:

- follow character instructions
- produce natural Indonesian
- maintain roleplay
- understand emotional context
- avoid unnecessary assistant-style behavior

Improving the state machine cannot fully compensate for a model that consistently breaks character.

### Tasks

- [ ] Inventory the current model/runtime configuration.
- [ ] Record current model name, quantization, context length, RAM/VRAM usage, and generation settings.
- [ ] Identify 2–3 viable Qwen 7B GGUF candidates.
- [ ] Record license/source for each candidate.
- [ ] Download the selected model.
- [ ] Verify model integrity before replacing the current model.
- [ ] Update model configuration.
- [ ] Preserve the existing 3B model/config as a rollback path.
- [ ] Run a smoke test.
- [ ] Retest context budgeting.
- [ ] Compare latency/resource usage against the 3B baseline.
- [ ] Start the one-week qualitative evaluation.

### Evaluation dimensions

```text
Character adherence
Indonesian naturalness
Roleplay quality
Emotional responsiveness
Assistant/refusal leakage
Memory/state coherence
Latency
Resource usage
```

### Acceptance criteria

The migration is not considered complete merely because the model loads.

It is complete when:

- the new model runs reliably;
- existing state/memory flow still works;
- context construction still fits the available budget;
- the model has been used for approximately one week under normal interaction;
- concrete failure cases have been recorded.

---

# Phase 2 — Context Budget Recalibration

## Why

The current context budget was designed around the 3B model. A larger model may have different context capacity, generation behavior, and memory pressure.

Do not blindly copy the old numbers.

### Current baseline

```text
System:   ~2,000 tokens
History:  ~1,500 tokens
Response:   ~800 tokens
```

### Tasks

- [ ] Identify actual context limit of selected model.
- [ ] Measure system prompt size.
- [ ] Measure average history size.
- [ ] Measure memory injection size.
- [ ] Measure maximum expected response size.
- [ ] Define reserved headroom.
- [ ] Update `config.py`.
- [ ] Test short conversations.
- [ ] Test long conversations.
- [ ] Test memory-heavy conversations.
- [ ] Verify truncation order.
- [ ] Verify important character instructions are never accidentally discarded.

### Target architecture

```text
Context Budget
├── Character/System
├── Dynamic State
├── Relevant Memories
├── Recent History
├── Tool Results
├── User Message
└── Response Reserve
```

### Acceptance criteria

- Context does not overflow under expected usage.
- Character-critical instructions remain present.
- History truncation is predictable.
- Memory retrieval does not consume the entire context budget.

---

# Phase 3 — State Protection & Versioning

## Why

`state.json` is not disposable configuration.

It represents accumulated relationship progress, emotional state, and potentially future memory.

Loss or corruption can destroy the project's most valuable persistent data.

### Tasks

- [ ] Document the current `state.json` schema.
- [ ] Add manual export/backup command.
- [ ] Define backup filename/version convention.
- [ ] Verify exported state can be restored.
- [ ] Add schema version field if not already present.
- [ ] Define migration pattern for future versions.
- [ ] Add v2 → v3 migration precedent/test.
- [ ] Ensure failed migration does not destroy the source state.
- [ ] Add validation before writing state.
- [ ] Consider atomic file replacement for writes.
- [ ] Add optional timestamped backups later.

### Desired flow

```text
state.json
    │
    ▼
validate
    │
    ▼
load
    │
    ▼
runtime
    │
    ▼
serialize
    │
    ▼
validate
    │
    ▼
atomic write
```

### Acceptance criteria

- A user can manually export state.
- An exported state can be restored.
- Schema changes have an explicit version.
- Migration failure leaves the original state recoverable.

---

# Phase 4 — Emotional Depth

> This phase continues the existing emotional state machine, salience filter, and mode system. Do not replace working foundations without evidence.

## 4.1 Relationship Drift Detection

### Goal

Detect gradual relationship changes rather than treating every interaction as an isolated state update.

### Tasks

- [ ] Define what constitutes relationship drift.
- [ ] Identify relevant state variables.
- [ ] Define drift thresholds.
- [ ] Distinguish temporary mood from persistent relationship change.
- [ ] Add regression tests.
- [ ] Add observation/debug output.

### Acceptance criteria

Repeated interaction patterns can produce gradual relationship changes without permanently altering core personality traits.

---

## 4.2 Conflict Dynamics

Do not implement conflict/reconciliation as one large feature.

### REL-001 — Conflict Trigger Definition

- [ ] Define explicit conflict signals.
- [ ] Define severity.
- [ ] Define false-positive cases.
- [ ] Add tests.

### REL-002 — Cooldown

- [ ] Define cooldown state.
- [ ] Define duration.
- [ ] Define repeated-conflict behavior.
- [ ] Add tests.

### REL-003 — Recovery Curve

- [ ] Define recovery variables.
- [ ] Define recovery rate.
- [ ] Define conditions that accelerate/slow recovery.
- [ ] Prevent instant emotional reset.
- [ ] Add tests.

### REL-004 — Reconciliation

- [ ] Define reconciliation triggers.
- [ ] Distinguish apology from actual recovery.
- [ ] Define partial vs full recovery.
- [ ] Add tests.

### Target flow

```text
Interaction
    ↓
Conflict Detector
    ↓
Severity
    ↓
Relationship State
    ↓
Cooldown
    ↓
Recovery
    ↓
Reconciliation
```

---

## 4.3 Long-Term Emotional Arcs

### Goal

Represent emotional tendencies over long periods without hardcoding a permanent personality change.

Possible future state:

```text
Attachment Profile
├── security
├── trust tendency
├── sensitivity
├── dependency tendency
└── conflict response
```

### Tasks

- [ ] Define whether attachment is character-level, relationship-level, or both.
- [ ] Define slowly changing variables.
- [ ] Separate attachment traits from temporary mood.
- [ ] Add decay/update rules.
- [ ] Add persistence.
- [ ] Add tests for long-term drift.

---

## 4.4 User Preference Learning

### Goal

Allow the companion to gradually learn stable user preferences.

### Tasks

- [ ] Define preference candidates.
- [ ] Define confidence.
- [ ] Define confirmation threshold.
- [ ] Distinguish explicit preference from inferred preference.
- [ ] Add preference update rules.
- [ ] Add forgetting/correction behavior.
- [ ] Add tests.

---

# Phase 5 — Memory Evolution

## Why

Memory is one of the highest-ROI improvements for a persistent companion.

The current keyword-oriented extraction/retrieval approach can miss semantic relationships and nuanced statements.

## 5.1 Embedding Research

### Tasks

- [ ] Identify small local embedding models.
- [ ] Check supported languages, especially Indonesian.
- [ ] Measure RAM/VRAM requirements.
- [ ] Measure embedding latency on the target environment.
- [ ] Check licensing.
- [ ] Test a small sample of Veil memories.
- [ ] Compare semantic similarity quality against keyword matching.

Do not commit to a vector database before establishing whether embeddings actually improve retrieval.

---

## 5.2 Semantic Memory Retrieval

### Target

```text
User message
    ↓
Embedding
    ↓
Candidate memories
    ↓
Similarity
    +
Importance
    +
Recency
    +
Relationship relevance
    ↓
Ranked memories
```

### Tasks

- [ ] Define embedding interface.
- [ ] Add embedding generation.
- [ ] Add memory vector representation.
- [ ] Define retrieval threshold.
- [ ] Define top-K.
- [ ] Add hybrid keyword + semantic retrieval.
- [ ] Add ranking.
- [ ] Add tests.
- [ ] Benchmark recall against the existing implementation.

### Acceptance criteria

Semantic retrieval must demonstrate a measurable advantage on a fixed memory benchmark before becoming the default.

---

## 5.3 Emotional ↔ Factual Cross-Reference

Example:

```text
FACT:
User likes coffee.

EMOTIONAL:
User mentioned coffee while discussing a stressful day.

Cross-reference:
Coffee preference + emotional context
```

### Tasks

- [ ] Define relation between memory records.
- [ ] Define confidence.
- [ ] Prevent emotional context from overwriting factual preference.
- [ ] Add retrieval behavior.
- [ ] Add tests.

---

## 5.4 Dream / Consolidation Cycles

### Goal

Periodically consolidate redundant memories and strengthen important ones.

### Tasks

- [ ] Define consolidation trigger.
- [ ] Define candidate memories.
- [ ] Define merge rules.
- [ ] Define importance decay.
- [ ] Define conflict resolution.
- [ ] Define what must never be automatically deleted.
- [ ] Add dry-run mode.
- [ ] Add tests.
- [ ] Only then automate.

### Safety rule

Never allow an experimental consolidation process to destroy the only copy of persistent user state.

---

# Phase 6 — Platform Strategy

## Why

Platform work has lower ROI than improving the brain and creates maintenance overhead.

Do not implement Web + Discord + WhatsApp + mobile simultaneously.

## 6.1 Choose One Platform

Candidates:

```text
Web UI
Discord
WhatsApp
```

### Decision criteria

- actual usage
- implementation effort
- authentication requirements
- 1-on-1 vs multi-user assumptions
- persistence model
- streaming requirements
- maintenance burden

### Tasks

- [ ] Compare candidates.
- [ ] Choose exactly one.
- [ ] Document why.
- [ ] Define adapter boundary.

---

## 6.2 Conversation Scope Audit

This becomes mandatory if the selected platform supports multiple users/channels.

Current assumption:

```text
User
  ↕
PersonalityCore
```

Potential multi-user model:

```text
User A ─┐
User B ─┼─ Channel / Session ─ Character
User C ─┘
```

### Tasks

- [ ] Identify all assumptions of 1-on-1 conversation.
- [ ] Separate user identity from conversation identity.
- [ ] Define session scope.
- [ ] Define memory ownership.
- [ ] Define relationship ownership.
- [ ] Add tests for concurrent users if applicable.

---

## 6.3 TTS

Backlog until the selected platform and core runtime are stable.

### Future tasks

- [ ] Define TTS adapter.
- [ ] Define voice configuration.
- [ ] Map emotion/intensity to voice parameters.
- [ ] Add interruption/cancellation.
- [ ] Measure latency.

---

## 6.4 Mobile App

Backlog.

Before implementing:

- [ ] Validate actual usage need.
- [ ] Compare Web/PWA against native app.
- [ ] Estimate maintenance cost.
- [ ] Decide only after the platform experiment.

---

# Phase 7 — Fine-Tuning / LoRA

> Stretch goal. Do not start this phase simply because the model feels imperfect.

## Trigger

LoRA begins only when:

```text
Model migration
      +
Prompt/context optimization
      +
Runtime improvements
      ↓
specific reproducible failures remain
```

Examples of valid triggers:

```text
"Fails to maintain casual Indonesian after N turns."

"Repeatedly converts Stella into generic assistant behavior
under condition X."

"Fails to reproduce a specific stable speech pattern
despite adequate context."
```

Invalid trigger:

```text
"Sometimes the responses feel weird."
```

## Tasks

- [ ] Collect failure cases during the 7B evaluation.
- [ ] Categorize failures.
- [ ] Attempt prompting/context fixes.
- [ ] Record which failures remain.
- [ ] Define measurable LoRA objective.
- [ ] Build clean Stella dialogue dataset.
- [ ] Remove contradictory examples.
- [ ] Split train/evaluation data.
- [ ] Run a lightweight LoRA experiment.
- [ ] Compare against untuned model.
- [ ] Evaluate against the fixed benchmark.
- [ ] Keep the adapter optional at runtime.

## CPT

CPT remains out of scope because the primary problem is character behavior, consistency, and runtime conditioning rather than lack of domain knowledge.

---

# Phase 8 — Validation & Regression

This phase is cross-cutting and should happen throughout development.

## Tasks

- [ ] Maintain a small conversation benchmark.
- [ ] Add regression cases whenever a real failure is observed.
- [ ] Test state persistence after changes.
- [ ] Test memory retrieval after changes.
- [ ] Test character behavior after model changes.
- [ ] Track latency/resource changes.
- [ ] Record known limitations.

## Suggested benchmark categories

```text
Personality
Indonesian naturalness
Emotion
Relationship
Memory
Lore
State persistence
Conflict
Long conversation
Character leakage
Assistant leakage
```

---

# Backlog / Non-Goals

These are intentionally not current priorities.

- [ ] CI/CD
- [ ] Separate `ARCHITECTURE.md`
- [ ] Full multi-platform rollout
- [ ] Mobile app
- [ ] TTS-first development
- [ ] CPT
- [ ] Large vector database before retrieval is benchmarked
- [ ] Full autonomous-agent system
- [ ] Complex multi-agent orchestration

`AGENT.md` remains the architectural source of truth, so a separate `ARCHITECTURE.md` is unnecessary unless the project grows enough to justify it.

---

# Definition of Done — Current Roadmap

The current roadmap is considered healthy when:

- [ ] A 7B model has been evaluated against the current 3B baseline.
- [ ] Context budgeting is measured rather than inherited blindly.
- [ ] `state.json` has a reliable backup/export path.
- [ ] State schema changes are versioned and recoverable.
- [ ] Emotional relationship dynamics have explicit, testable transitions.
- [ ] Semantic memory has been benchmarked against keyword retrieval.
- [ ] Memory retrieval does not blindly inject the entire memory store.
- [ ] One platform has been selected based on actual use rather than implemented speculatively.
- [ ] Fine-tuning decisions are based on documented failures.
- [ ] Core behavior has a regression benchmark.

---

# Immediate Execution Order

Do not skip ahead.

```text
1. Backup/export state.json
        ↓
2. Inventory current 3B model/config
        ↓
3. Select and test Qwen 7B candidate
        ↓
4. Recalibrate context budget
        ↓
5. Begin one-week behavior log
        ↓
6. Emotional depth improvements
        ↓
7. Embedding research + retrieval benchmark
        ↓
8. Semantic memory implementation
        ↓
9. Choose one platform
        ↓
10. Reassess whether LoRA is actually necessary
```
