# Veil Core — Plan

> Living document. Update whenever priorities or architectural decisions change.
> `AGENT.md` remains the source of truth for engineering rules and architecture.
> This document defines **what we prioritize and why**.
>
> **Current roadmap status:** Phase 0 — Repository Audit is the active priority. Existing roadmap phases remain preserved, but work that changes models or architecture should wait until the audit exit criteria are met.
>
> **Phase 0 status as of 2026-10-15: INCOMPLETE.** Of the seven Phase 0 exit
> criteria, five are **met**, one is **partial** (#7), and one is **not met**
> (#3, AUDIT-004). A post-C1 behavioural benchmark has now been **executed
> successfully** — 13/13 prompts, process exit code 0, 105.4 s, `VEIL_TEMP=0.7`,
> CPU-only — but **AUDIT-004 remains not met**: the benchmark has no
> long-conversation coverage, no documented expected behaviour per prompt, and
> positive long-term-memory recall is still untested. Phase 0 is **not** closed.
> See [Discrepancy register](#discrepancy-register-phase-0) and
> [Post-C1 benchmark evidence](#post-c1-benchmark-evidence).

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
- [x] A current request-lifecycle diagram exists.
- [ ] Existing tests and a small behavior benchmark have recorded results.
- [x] Persistent state and memory have a verified backup/restore path.
- [x] Major modules have KEEP / REFACTOR / REPLACE / DEFER dispositions.
- [x] Conflicts between code, config, `BASELINE.md`, `AGENT.md`, and other docs are recorded.
- [ ] The next implementation step is supported by evidence and has a rollback path.

**Until these criteria are met, do not start a model migration or broad architecture rewrite.** Small, non-destructive fixes needed to run the audit are allowed and should be documented.

### Exit criteria status (verified 2026-10-11)

| # | Criterion | State | Evidence |
|---|---|---|---|
| 1 | Model/runtime configuration verified | **MET** | measured at runtime: 7B, `N_CTX=4096`, `CTX_PROMPT_CHAR_LIMIT=14528`, effective temp **0.7** (see D-2) |
| 2 | Request-lifecycle diagram | **MET** | `README.md` Architecture section; traced through `personality/core.py` → `core/agent.py` → `llm/engine.py` |
| 3 | Tests + behavior benchmark recorded | **NOT MET** | 141 deterministic assertions pass in the isolated verification run; `tools/bench.py` **has now been executed** on the current 7B model — post-C1 run 2026-10-15, 13/13 prompts, exit code 0 (see [Post-C1 benchmark evidence](#post-c1-benchmark-evidence)). AUDIT-004 still unmet: no long-conversation coverage, no per-prompt expected behaviour, positive long-term recall untested |
| 4 | Backup/restore path verified | **MET** | checksummed envelope, tamper + future-schema rejection, v2→v3 migration — covered by the suite |
| 5 | Module dispositions | **MET** | `README.md` structure + `AGENT.md` §Discrepancies |
| 6 | Conflicts recorded | **MET** | this section |
| 7 | Next step evidence-backed + rollback | **PARTIAL** | the next step is gated on the model copy, which is not yet authorized |

### Discrepancy register (Phase 0)

| ID | Finding | Severity | Status | Owning phase |
|---|---|---|---|---|
| D-1 | `core/bootstrap.py` error text said "Download Qwen2.5-**3B**" while the configured path is the **7B** model | Low | **Fixed in working tree, uncommitted** — message now derives the filename from `config.MODEL_PATH`; not present in `e827a8e` | Phase 0 |
| D-2 | `.env` (gitignored) sets `VEIL_TEMP=0.7`, making the tuned `0.6` default unreachable. Effective runtime temperature is **0.7**. Decide the intended value before recording a behavioural baseline | Medium | **Open — needs a decision.** Precedence verified: OS env > `.env` > code default | Phase 1 |
| D-3 | `BASELINE.md` "Model & Runtime Config" described the 3B/CPU reference, not current config | Medium | **Fixed** in `e827a8e` | Phase 0 |
| D-4 | `core/agent.py` omitted a 1-char separator from context accounting; assembled prompt could reach `limit + 1` | Low | **Fixed in working tree, uncommitted** — worst case now exactly `limit` (14528); not present in `e827a8e` | Phase 2 |
| D-5 | Context-guard tests used a 216-char system marker, so the binding branch was never exercised | Low | **Fixed in working tree, uncommitted** — 3 boundary assertions added to `test_agent.py` at realistic system size; not present in `e827a8e` | Phase 2 |
| D-6 | `AGENT.md` prohibits a PersonalityCore god object; `personality/core.py` owns emotion, conflict, inactivity, memory, tools, prompting and persistence | Medium | **Open — documented gap** | Phase 4 / 5 |
| D-7 | `AGENT.md`/`DESIGN.md` require YAML-driven characters; Stella is hardcoded in `personality/stella.py` and imported by the core | Medium | **Open — documented gap** | Phase 6 |
| D-8 | `PLAN.md` "~2,100 tokens" context estimate is unverified | Info | **Open — evidence-limited.** Post-D-4 measured char worst case is 14528 (14529 before the fix); the ratio and the token figure both need `tools/ctx_report.py` | Phase 2 |
| D-9 | `tools/bench.py:118` referenced removed `CTX_BUDGET_SYSTEM` / `CTX_BUDGET_RESPONSE` | Medium | **Fixed** in `b53eafc` | Phase 0 |
| D-10 | `config.py` `float(os.getenv("VEIL_TEMP", ...))` raises `ValueError` if the variable is set but empty | Low | **Open — not fixed**; `config.py` is out of audit scope | Phase 0 |
| D-11 | `README.md` claimed "138 deterministic assertions" in two places while the suite runs **141** (138 + the 3 boundary assertions added for D-5) | Low | **Resolved 2026-10-15** — count corrected to 141 in `README.md` | Phase 0 |
| D-12 | `memory/extractor.py` requires a `ya`/`bahwa`/`kalau` particle before seeding a fact, so a **bare imperative** such as `ingat ulang tahun aku bulan depan` is no longer saved | Low | **Open — product decision needed.** Deliberate narrowing: the bare form previously seeded, and a recall question (`inget ga ...`) was wrongly saved as a fact. No test covers the bare form either way; `AGENT.md` defines no save marker | Phase 5 |
| D-13 | `LongTermMemory.get_relevant_facts()` returns `scored[:10]` with **no relevance floor**, so facts scoring zero against the query are still injected into the prompt | Medium | **Open.** Verified 2026-10-15: an unrelated query still returned a stored fact. Injection precision degrades as the store grows | Phase 5 |

**Merged: D-3 (`e827a8e`), D-9 (`b53eafc`). Fixed but uncommitted in the working
tree: D-1, D-4, D-5. Resolved in this documentation pass: D-11. Open: D-2, D-6,
D-7, D-8, D-10, D-12, D-13.**
D-1/D-4/D-5 are present only in the current working tree; they are **not** in the
`prototypev1` HEAD commit `e827a8e`.
The architectural requirements in `AGENT.md` and `DESIGN.md` stand as written;
D-6 and D-7 are recorded gaps between requirement and implementation, not licence
to weaken the requirement. D-2 and D-10 are left open deliberately: both would
require editing runtime configuration, which this audit must not do to make
documentation look consistent.

## Post-C1 benchmark evidence

Captured 2026-10-15 against the current checkout. Raw report:
`%TEMP%\veil-audit\POST_C1_BENCHMARK_REPORT.md`.

| Item | Value |
|---|---|
| Runs executed | exactly one |
| Process exit code | **0** (measured, not inferred) |
| Prompts completed | **13 / 13** |
| Wall clock | 105.4 s |
| Avg / Min / Max latency | 7.00 s / 3.95 s / 20.70 s |
| Warmup | 8.1 s, excluded from stats by design |
| Effective temperature | **0.7**, set in the child process environment only |
| Compute | CPU-only (`n_gpu_layers = 0`); Tavily disabled |
| Tracebacks | none; one benign `n_ctx_seq (4096) < n_ctx_train (32768)` notice |

### What this run proves

- **The canned-reaction defect is gone from the measured path.** The Phase B
  run returned `hmm iya juga` for prompt 5 in **0.02 s** — a
  `REACTION_TEMPLATES["pensive"]` string, never an inference. This run returns a
  real **7.08 s** generation for the same prompt, and the minimum latency moved
  from 0.02 s to 3.95 s.
- **The memory-extraction defect is gone in the live pipeline.**
  `memory/long_term.json` finished byte-identical to its empty seed. In the
  Phase B run it had grown to 246 B holding the corrupted fact
  `"Ga kemarin kita bahas apa?"`.
- Production was untouched: 7 protected files byte-identical, `protected
  differences : 0`, and the detection-only filesystem monitor recorded **zero**
  file changes across the whole run.

### What this run does **not** prove

1. **Latency is monitor-contaminated.** The filesystem monitor scanned ~3,843
   files every second *during* the run, competing for CPU. **7.00 s must not be
   presented as uncontaminated model latency**, nor compared directly against the
   Phase B average of 4.59 s, which was measured without a monitor.
2. **One run, one seed.** No variance, no repeat sampling. Temperature 0.7 is
   nondeterministic.
3. **Positive long-term recall is still untested.** Prompt 8 recalled from
   *emotional* memory (seeded with 8 historical records); the long-term store was
   empty and correctly stayed empty.
4. **AUDIT-004 gaps remain** — no long-conversation category, and no documented
   expected behaviour per prompt.
5. **VRAM (915 MB) and model footprint (~433 MB) figures are artifacts** and must
   not be cited as measurements.
6. **D-8 stays blocked** — `tools/ctx_report.py:33` constructs
   `LLMEngine(config.MODEL_PATH)`, so the token-side context estimate still
   requires a GGUF load.
7. **Known baseline behaviours reproduced:** prompt 9 admits being an AI, and
   prompt 13 appends an unsolicited "sayang!". Both are pre-existing findings
   (persona identity and persona-leak diagnostics), **not** new regressions.

## Remaining Phase 0 work

Phase 0 cannot close until these are done. Ordered by dependency:

1. **AUDIT-004 completion** — add a long-conversation prompt category and record
   the documented expected behaviour for each of the 13 prompts. Neither requires
   new source changes.
2. **AUDIT-004 positive long-term recall** — the current prompt set never plants
   a fact and asks for it back, so the recall path is unexercised in the
   positive direction.
3. **D-2 temperature decision** — `PLAN.md` §Phase 1 requires this resolved
   *before* a behavioural baseline is treated as authoritative. The 0.7 used
   above is unratified.
4. **AUDIT-006** — the smallest safe next change and its rollback path are still
   undefined, which is what keeps exit criterion 7 **PARTIAL**.
5. **D-8** — needs `tools/ctx_report.py` against the GGUF; blocked on a model
   load that has not been authorized.
6. **D-12 / D-13** — product decisions, Phase 5.
7. **Exit criterion 6** — `README.md` was corrected in this pass (D-11), but
   `PLAN.md` §Phase 0 status and `BASELINE.md` must be re-read together to
   confirm no further doc conflicts remain.

---

# Phase 1 — Model Migration

> **Note (2026-10-11): the migration described below was already performed on
> 2026-08-26** — the 3B → 7B switch, GPU wheel installation and one-week
> qualitative evaluation are recorded in `BASELINE.md` §Post-migration. The
> 3B model is retained as a rollback file. What remains open is
> **revalidation**: those results were captured against an earlier checkout and
> have not been re-verified since. Phase 0 is the gate; do not re-run the
> migration, re-verify the recorded baseline.

## Qwen 7B Evaluation

Move from the current 3B model to a suitable Qwen 7B GGUF candidate, initially targeting Q4_K_M-class quantization.

The exact model variant must be selected through evaluation rather than assuming that every Qwen 7B variant behaves identically.

**Dependency:** Begin only after Phase 0 verifies the actual current model/configuration, establishes a usable baseline, and confirms a safe rollback path.

**Status: migration done; revalidation blocked on AUDIT-004.** The acceptance criteria below that depend on measured behaviour (one week of use, recorded concrete failures) were met for the 2026-08-26 run and must be re-confirmed before Phase 1 can be considered revalidated. Resolve D-2 (temperature) before capturing that baseline.

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

- **2026-10-11 — docs:** reconciled roadmap with verified implementation. Recorded that the
  7B migration already happened (2026-08-26) and that Phase 1 now needs *revalidation*, not
  migration. Logged the Phase 0 discrepancy register (D-1…D-10) with owning phases.
- **2026-10-11 — fix (`b53eafc`):** `tools/bench.py` reported `config.CTX_BUDGET_SYSTEM` and
  `config.CTX_BUDGET_RESPONSE`, both removed in `3da72f9` when the three soft budgets were
  consolidated into `CTX_PROMPT_CHAR_LIMIT`. The line raised `AttributeError` *after* the full
  13-prompt benchmark, discarding a paid inference run. Now reports the current budget model.
  The obsolete sys/hist/resp framing was removed rather than mapped, because the three-way
  split no longer exists: there is no system cap (the system block is never truncated) and no
  character response reserve (folded in as `MAX_TOKENS_STREAM` tokens).
- Added Phase 0 repository audit as the active priority before model migration or broad refactoring.
- Preserved the existing roadmap phases and their acceptance criteria.
- Clarified that baseline values and the proposed design must be verified against the actual repository before being treated as current facts.
