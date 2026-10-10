# Veil Core — Plan

> Living document. Update whenever priorities or architectural decisions change.
> `AGENT.md` remains the source of truth for engineering rules and architecture.
> This document defines **what we prioritize and why**.
>
> **Current roadmap status:** Phase 0 — Repository Audit is the active priority. Existing roadmap phases remain preserved, but work that changes models or architecture should wait until the audit exit criteria are met.

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

# Phase 0 — Repository Audit (ACTIVE PRIORITY)

## Goal

Establish an evidence-based picture of the current repository, runtime behavior, data safety, and measured baseline before selecting the next implementation task.

This phase does **not** cancel the existing roadmap. It validates its assumptions and determines whether Phase 1 should proceed as written or be adjusted.

## Constraints

- Do not rewrite working systems merely to match a proposed architecture.
- Do not replace the current model during the audit.
- Do not delete, reset, or migrate real user state as part of testing.
- Keep `state.json`, memory stores, model files, and local changes recoverable.
- Avoid adding TTS, Live2D, or new platform dependencies before the core interfaces are understood.
- Treat `DESIGN.md` as a proposed target design pending audit, not as proof that the repository already follows it.
- Keep `AGENT.md` as the source of truth for engineering rules and architecture.

## AUDIT-001 — Capture the Current Baseline

- [ ] Record repository status, current branch, and uncommitted changes.
- [ ] Identify the actual Python/runtime environment and supported target environment.
- [ ] Record model file, model variant, quantization, context length, and generation settings.
- [ ] Verify which model the runtime actually loads; reconcile discrepancies between code, config, and documentation.
- [ ] Record inference backend and available CPU/GPU acceleration.
- [ ] Run existing tests and record failures without silently fixing unrelated issues.
- [ ] Run the existing smoke test, if available.
- [ ] Record latency, memory use, and representative conversation behavior where practical.
- [ ] Compare the observed setup with `BASELINE.md` and document stale or conflicting claims.

**Output:** a dated baseline note with environment, model/config, test results, known limitations, and measurements.

## AUDIT-002 — Trace the Current Request Lifecycle

- [ ] Trace the actual entry point into the runtime.
- [ ] Follow a user message through prompt/context construction and the LLM call.
- [ ] Identify where character identity and instructions are defined.
- [ ] Identify where dynamic state and relationship variables are read and updated.
- [ ] Identify how short-term history is assembled and truncated.
- [ ] Identify how long-term memories are stored, selected, and injected.
- [ ] Identify tools, evaluators, post-processing, and output handling.
- [ ] Record important implicit assumptions, including single-user/session assumptions.
- [ ] Draw an as-is flow diagram from the code, not from intended architecture.

**Output:** a short request-lifecycle diagram and a list of responsibilities, dependencies, and observed coupling.

## AUDIT-003 — Protect Persistent Data

- [ ] Locate all persistent state and memory files.
- [ ] Document current schemas and version fields.
- [ ] Create a backup/export of relevant persistent data before any potentially destructive test.
- [ ] Verify that a backup can be restored to a temporary location.
- [ ] Inspect migration behavior and determine whether failures preserve the original source.
- [ ] Identify unsafe direct-write paths and missing validation.
- [ ] Do not perform experimental migrations on the only copy of real data.

**Output:** a data inventory, verified backup/restore procedure, and list of persistence risks.

## AUDIT-004 — Establish a Regression Baseline

- [ ] Collect a small set of representative prompts and expected behavior.
- [ ] Include Indonesian naturalness, character adherence, emotional context, memory, long conversations, and assistant-style leakage.
- [ ] Record current outputs before changing prompts, model, state logic, or retrieval.
- [ ] Separate reproducible failures from subjective impressions.
- [ ] Keep test inputs free of secrets and unnecessary personal data.

**Output:** a small repeatable benchmark and a log of current failures.

## AUDIT-005 — Classify Existing Modules

For each important module, choose one disposition:

- **KEEP** — working and appropriately scoped.
- **REFACTOR** — useful behavior, but boundaries or implementation need improvement.
- **REPLACE** — evidence shows the current implementation cannot meet requirements.
- **DEFER** — not needed for the current goal.

Review at minimum:

- [ ] Bootstrap and configuration.
- [ ] LLM engine/model loading.
- [ ] Character identity and prompt construction.
- [ ] Emotional state and relationship logic.
- [ ] Short-term conversation history.
- [ ] Long-term memory storage and retrieval.
- [ ] Persistence and migrations.
- [ ] Tests, benchmark scripts, and documentation.
- [ ] Platform-specific code and assumptions.

**Output:** a module disposition table with evidence, risk, and suggested next action for each major area.

## AUDIT-006 — Decide the Migration Path

- [ ] Compare the existing implementation with the proposed boundaries in `DESIGN.md`.
- [ ] Identify which roadmap assumptions remain valid.
- [ ] Decide whether the next step is incremental improvement, targeted replacement, or a larger refactor.
- [ ] Define the smallest safe next change.
- [ ] Record rollback steps and data-protection requirements.
- [ ] Update this plan only where audit evidence justifies a change.

**Output:** a short decision record explaining what will change, what will remain, why, and how to roll back.

## Phase 0 Exit Criteria

Phase 0 is complete when:

- [ ] The actual model/runtime configuration is verified.
- [ ] A current request-lifecycle diagram exists.
- [ ] Existing tests and a small behavior benchmark have recorded results.
- [ ] Persistent state and memory have a verified backup/restore path.
- [ ] Major modules have KEEP / REFACTOR / REPLACE / DEFER dispositions.
- [ ] Conflicts between code, config, `BASELINE.md`, `AGENT.md`, and other docs are recorded.
- [ ] The next implementation step is supported by evidence and has a rollback path.

**Until these criteria are met, do not start a model migration or broad architecture rewrite.** Small, non-destructive fixes needed to run the audit are allowed and should be documented.

---

# Phase 1 — Model Migration

## Qwen 7B Evaluation

Move from the current 3B model to a suitable Qwen 7B GGUF candidate, initially targeting Q4_K_M-class quantization.

The exact model variant must be selected through evaluation rather than assuming that every Qwen 7B variant behaves identically.

**Dependency:** Begin only after Phase 0 verifies the actual current model/configuration, establishes a usable baseline, and confirms a safe rollback path.

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

Budgets are CHARACTERS enforced via a hard prompt limit (measured against the real tokenizer in `tools/ctx_report.py` — Indonesian ≈ 4.1 chars/token). Worst-case assembled prompt ≈ 2,100 tokens vs ~3,800 available at N_CTX=4096. See `BASELINE.md` and `config.py` for current values.

**Audit note:** These are existing documented measurements, not yet re-verified against the current checkout/model. Confirm them during Phase 0 before relying on them.

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

- [ ] Phase 0 audit exit criteria are satisfied.
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

Do not skip ahead. The first goal is to establish the actual repository state without destabilizing working behavior.

```text
1. Check git status, branch, and local changes
        ↓
2. Inventory model/runtime/config and reconcile docs
        ↓
3. Trace the current request lifecycle
        ↓
4. Back up persistent state and verify restore to a temporary location
        ↓
5. Run tests/smoke test and capture a small behavior baseline
        ↓
6. Classify modules and record architecture risks
        ↓
7. Decide the smallest safe next change
        ↓
8. Resume Phase 1: evaluate Qwen 7B candidate
        ↓
9. Recalibrate context budget using measured tokenizer/runtime data
        ↓
10. Begin one-week behavior log
        ↓
11. Emotional depth improvements
        ↓
12. Embedding research + retrieval benchmark
        ↓
13. Semantic memory implementation, only if benchmark supports it
        ↓
14. Choose one platform
        ↓
15. Reassess whether LoRA is actually necessary
```

## Change Log

- Added Phase 0 repository audit as the active priority before model migration or broad refactoring.
- Preserved the existing roadmap phases and their acceptance criteria.
- Clarified that baseline values and the proposed design must be verified against the actual repository before being treated as current facts.
