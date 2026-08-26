# Veil Core — TODO

> Detailed execution checklist. Follow the order unless `PLAN.md` is updated.
> `PLAN.md` explains priorities and rationale. `AGENT.md` remains the source of
> truth for architecture and engineering rules.
>
> Status:
> - `[ ]` Not started
> - `[~]` In progress
> - `[x]` Complete
> - `[!]` Blocked / needs investigation

---

# 🔴 0. Safety & Baseline

## STATE-001 — Backup `state.json` before major changes

**Goal:** protect accumulated relationship/state data before model and runtime changes.

**Why:** `state.json` is persistent project data, not disposable configuration.

**Likely files/areas:**
- `state.json`
- state persistence code
- CLI/runtime entry point

**Tasks**
- [x] Identify the current state file path. (`data/state.json` via `personality/persistence.py:DEFAULT_PATH`)
- [x] Verify which runtime components write to it. (only `personality/core.py` → `save_state`)
- [x] Create a manual export/backup command or documented procedure. (`tools/state_backup.py export`)
- [x] Include timestamp/schema version in exported backup metadata.
- [x] Restore a backup into a temporary copy. (`restore` without `--apply` verifies only)
- [x] Verify the restored state loads successfully. (loads via `load_state`, prints state summary)
- [x] Document the procedure. (README → "Backup & Restore State")

**Acceptance criteria**
- A complete state backup can be created without modifying the original.
- A backup can be restored successfully.
- The backup contains enough information to recover relationship state.

**Do not**
- Automatically delete old state.
- Rewrite the state schema in the same task.
- Make backup creation depend on the LLM.

---

## BASE-001 — Capture the current baseline

**Goal:** know what "better" means before changing the model.

**Result:** captured in `BASELINE.md` (2026-08-23). Runtime is CPU-only — the
installed llama-cpp-python wheel has no CUDA support and `_setup_cuda_paths()`
points to a nonexistent `venv\` dir. Fixing GPU belongs to MODEL-003 setup.

**Tasks**
- [x] Record current model name and quantization.
- [x] Record current context limit/config.
- [x] Record system/history/response token budgets. (actual: 2500/2500/800 chars — docs synced)
- [x] Record average response latency. (avg 5.88s, 13-prompt bench)
- [x] Record RAM/VRAM usage if measurable. (RAM ~2.87 GB footprint; VRAM n/a, CPU build)
- [x] Save 10–20 representative conversations/prompts. (13 prompts + responses in `tools/bench.py` / `BASELINE.md`)
- [x] Include casual Indonesian, emotional interaction, memory recall, and character-boundary cases.
- [x] Record known current failures. (5 concrete cases in `BASELINE.md`)

**Acceptance criteria**
- A reproducible baseline exists before model migration.

---

# 🔴 1. Model Migration — Qwen 7B

## MODEL-001 — Inventory current model integration

**Goal:** understand exactly what must change.

**Result:** documented as "Model Integration Map" in `README.md`. Known
migration-relevant issues: CPU-only wheel installed, `_setup_cuda_paths()` uses
wrong env dir, CUDA wheel index URL in README was outdated (fixed path noted in
`CANDIDATES.md`), char-based budgets unvalidated against token counts.

**Tasks**
- [x] Locate model configuration. (`config.py`)
- [x] Locate model loading/inference code. (`llm/engine.py`)
- [x] Locate model path configuration. (`config.MODEL_PATH` → `core/bootstrap._build_agent`)
- [x] Locate generation parameters. (`config.SAMPLING` → `engine._default_params`)
- [x] Locate context-length configuration. (`config.N_CTX`, `CTX_BUDGET_*` in `core/agent.py`)
- [x] Document assumptions specific to the current 3B model. (README integration map)

**Acceptance criteria**
- [x] A new contributor can identify the model integration path from the documentation.

---

## MODEL-002 — Evaluate Qwen 7B candidates

**Goal:** choose a concrete model rather than treating "Qwen 7B" as one behavior.

**Requirement added 2026-08-23:** candidate must be uncensored (refusal-free) —
refusal/assistant leakage is a documented baseline failure. Evaluation recorded
in `CANDIDATES.md`.

**Candidates**
- [x] Qwen 2.5 7B GGUF candidate. (huihui-ai Qwen2.5-7B-Instruct-abliterated-v2)
- [x] Qwen 3.x 7B-class candidate if compatible with the current runtime. (DavidAU Heretic Qwen3-8B; needs `<think>` handling)
- [x] Other suitable Qwen 7B GGUF candidate if technically justified. (Huihui-Qwen3-8B-abliterated-v2)

**For each candidate record** — see `CANDIDATES.md`
- [x] Exact model/revision.
- [x] Quantization.
- [x] Context length.
- [x] License.
- [x] GGUF source.
- [x] RAM/VRAM requirement.
- [x] Expected inference speed.
- [x] Known roleplay/Indonesian behavior.

**Acceptance criteria**
- [x] One candidate is explicitly selected. (huihui Qwen2.5-7B-Instruct-abliterated-v2, Q4_K_M)
- [x] The old 3B model remains available for rollback.

---

## MODEL-003 — Install Qwen 7B Q4-class GGUF

**Result (2026-08-26):** done — GPU enabled + model swapped in one pass.
Details and comparison numbers in `BASELINE.md` ("Post-migration results").

**Tasks**
- [x] Download model. (`mradermacher i1-Q4_K_M`, 4.68 GB, byte-count verified)
- [x] Verify file integrity. (Content-Length match; SHA check optional later)
- [x] Store model outside source-controlled files. (`models/`, gitignored)
- [x] Update local model configuration. (`config.py`; 3B kept as rollback)
- [x] Confirm model loads. (~6.5s load, full GPU offload)
- [x] Run one minimal generation test. (+ full 13-prompt bench vs baseline)

**Acceptance criteria**
- [x] Model loads and generates a valid response through the existing runtime.

**Do not**
- [x] Commit multi-GB model files.
- [x] Remove the old working model yet.

---

## MODEL-004 — Retest context budgeting

**Goal:** replace assumptions inherited from the 3B configuration with measured values.

**Result (2026-08-26):** measured via `tools/ctx_report.py` using the real
Qwen2.5 tokenizer. Indonesian averages **~4.1 chars/token**. System prompt is
202–267 tokens; worst-case assembled prompt ≈ 2,100 tokens vs 3,796 available
(N_CTX 4096 − response reserve) — fits with ~1,700 tokens spare. The old
budgets were CHARACTERS misread as token limits; a hard guard
(`CTX_PROMPT_CHAR_LIMIT`) now replaces the left-truncating formula that could
destroy the system block on oversized input. Dead config
(`CTX_BUDGET_SYSTEM/RESPONSE`) removed.

```text
measured (chars/tokens):
system prompt      865-1157 / 202-267
history worst      6647 / 1663  (before soft-budget truncation)
observation max     500 / 139
hard guard        CTX_PROMPT_CHAR_LIMIT ≈ 14.5k chars
```

**Tasks**
- [x] Measure actual system prompt size. (865–1157 chars / 202–267 tokens)
- [x] Measure character prompt size. (identity blob 669 chars, inside system)
- [x] Measure state injection. (~200 chars natural language)
- [x] Measure memory injection. (emotional summary ≤5×60 chars; bounded)
- [x] Measure history. (worst legal: 16×500c → truncated to budget)
- [x] Determine actual model context limit. (N_CTX=4096 active; 32k train headroom unused)
- [x] Define response reserve. (MAX_TOKENS_STREAM 400 folded into hard limit)
- [x] Add safety headroom. (64 tokens)
- [x] Update `config.py`. (CTX_PROMPT_CHAR_LIMIT ≈ 14.5k chars, unit-documented)
- [x] Test short conversation. (bench + suite LLM section)
- [x] Test long conversation. (16-message history guard tests)
- [x] Test memory-heavy conversation. (ctx_report scenario rows)
- [x] Test truncation behavior. (6 deterministic guard tests — oldest dropped first, system never cut)

**Acceptance criteria**
- [x] No expected prompt path overflows.
- [x] Character-critical instructions remain intact.
- [x] History truncation is deterministic.
- [x] Memory injection is bounded.

---

## MODEL-005 — Seven-day character evaluation

**Goal:** collect concrete failures instead of relying on vague impressions.

**Status: [~] IN PROGRESS (started 2026-08-26).** Automated via
`tools/daily_eval.py` + Task Scheduler job `VeilSevenDayEval` (daily 21:00,
self-deletes after day 7). Runs 12 probes daily against a sandboxed state in
`data/eval_sandbox/` that persists across days; real `state.json` untouched.
Outputs in `logs/eval/`: daily `.md` report, `responses.jsonl`,
`state_history.csv`, and a pre-formatted `failures.md` to fill manually.
Day-1 finding already captured: memory seed acknowledged then forgotten two
turns later (memory/state inconsistency).

**For every significant failure record**
```text
Date:
Conversation/trigger:
Expected behavior:
Actual behavior:
Category:
Severity:
Reproducible:
Potential runtime/prompt cause:
```

**Categories**
- [ ] Character leakage.
- [ ] Assistant-style leakage.
- [ ] Unnecessary disclaimer/refusal.
- [ ] Stiff/translated Indonesian.
- [ ] Personality inconsistency.
- [ ] Emotional inconsistency.
- [ ] Memory/state inconsistency.
- [ ] Other.

**Acceptance criteria**
- Approximately one week of normal use has been observed.
- Failures are specific enough to reproduce or investigate.
- No LoRA decision is made from subjective impressions alone.

---

# 🔴 2. State Versioning & Recovery

## STATE-002 — Document `state.json` schema

**Tasks**
- [ ] List every top-level field.
- [ ] Document field types.
- [ ] Identify required vs optional fields.
- [ ] Identify fields related to relationship state.
- [ ] Identify fields related to emotion/mode.
- [ ] Record current schema version.

---

## STATE-003 — Version future schema changes

**Goal:** establish a repeatable migration pattern.

**Progress (2026-08-26):** v2 → v3 precedent created while adding conflict
dynamics fields (`_register(2)` in `persistence.py`, setdefault-only migration,
legacy payload tested). Remaining gap: explicit validation pass *before*
migrating.

**Tasks**
- [x] Confirm existing v1 → v2 migration pattern.
- [x] Extract reusable approach. (`_register` decorator + `_run_migrations`)
- [x] Define v3 migration convention. (setdefault-safe fields only)
- [ ] Add validation before migration.
- [x] Write migrated state to a safe target. (in-memory at load; atomic save)
- [x] Preserve original on failure. (backup tool + non-destructive load path)
- [x] Add migration tests. (legacy-v2 payload test)

**Acceptance criteria**
- [x] A schema migration can fail without destroying the original state.

---

# 🟠 3. Phase 6 — Emotional Depth

## EMO-001 — Relationship drift detection

**Goal:** distinguish temporary mood changes from gradual relationship changes.

**Result (2026-08-26):** implemented in `personality/conflict.py` +
`StellaState.drift_window` (persisted, schema v3). Significant valences
(confidence ≥ 0.4) fill a 10-slot window; `compute_drift()` classifies it as
positive / stable / negative / insufficient (min 5 samples, ±0.15 band).
Logged at debug level each turn.

**Tasks**
- [x] Inventory current relationship/state variables. (5-dim + mode system, `personality/state.py`)
- [x] Identify variables allowed to drift. (all five dims, clamped [0..1])
- [x] Define drift threshold. (±0.15 average valence)
- [x] Define observation window. (10 samples, ≥5 to classify)
- [x] Define positive drift. (avg > +0.15)
- [x] Define negative drift. (avg < −0.15)
- [x] Define neutral/noise behavior. ("stable" band + "insufficient" guard)
- [x] Add deterministic tests. (drift + full cycle suite)
- [x] Add debug logging. (`core.handle` → log.debug per turn)

**Acceptance criteria**
- [x] Repeated interaction patterns can produce gradual relationship changes.
- [x] A single unusual message cannot permanently distort relationship state.

---

## REL-001 — Define conflict triggers

**Result:** `detect_conflict()` in `personality/conflict.py`. Categories:
insult / abandonment / rejection. Severity ∈ [0..1] from base weights plus an
intensifier boost (+0.15 for `!!`, CAPS). False-positive guards: plain insults
require a second-person marker ("kamu bego" ≠ "bos gw bego"); sub-threshold
events (<0.25) ignored. Repeated conflict during cooldown escalates +0.15.

**Tasks**
- [x] Inventory current emotional signals. (`personality/analyzer.py` lexicon)
- [x] Define conflict categories. (insult, abandonment, rejection)
- [x] Define severity levels. (weighted lexicon, clamped [0..1])
- [x] Define false-positive examples. (third-party venting, self-directed, neutral chat — all tested)
- [x] Define repeated-trigger behavior. (escalation step while cooling down)
- [x] Add test fixtures. (`test_agent.py` Conflict Dynamics section)

**Acceptance criteria**
- [x] Conflict detection has documented rules/examples.
- [x] Tests cover both positive and negative cases.

---

## REL-002 — Conflict cooldown

**Result:** on accepted conflict: penalty applied to trust/affection/comfort/
attachment, `cooldown_until = now + COOLDOWN_BASE_S × severity` (15 min × sev),
mode forced to withdrawn (strength ≥ 0.4). While cooling: positive deltas
damped ×0.35. Persisted via schema v3. Ceiling: cooldown clock resets on app
restart if the saved timestamp has passed — acceptable for chat pacing.

**Tasks**
- [x] Define cooldown state. (`cooldown_until`, persisted)
- [x] Define duration. (900 s × severity)
- [x] Define decay during cooldown. (positive-gain damping 0.35)
- [x] Define repeated-conflict behavior. (escalation + fresh timer)
- [x] Persist cooldown state if necessary. (schema v3)
- [x] Add tests.

---

## REL-003 — Recovery curve

**Result:** conflicts snapshot the damage into `pending_recovery` gaps. Once
cooldown expires, each qualifying turn (valence ≥ 0.2) heals a fraction of the
remaining gap (25%, scaled up by valence, ×2 after apology) — never overshooting
the pre-conflict value; a turn can never fully heal. Gap < 0.01 counts as
healed and clears the cycle.

**Tasks**
- [x] Identify affected state variables. (trust, affection, comfort, attachment)
- [x] Define initial recovery value. (gap snapshot at conflict time)
- [x] Define recovery rate. (fraction-of-gap per turn)
- [x] Define modifiers. (valence scaling, apology bonus)
- [x] Prevent instant reset. (tested: one turn heals < 75% of gap)
- [x] Add tests for multiple time steps. (30-turn loop to full heal)

---

## REL-004 — Reconciliation

**Result:** apology markers (`maaf`, `sorry`, `aku salah`, …) halve an ACTIVE
cooldown (relative to the moment of apology) and double the recovery fraction.
Only the first two apologies per cycle are effective; further apologies do
nothing until the cycle resets — anti-spam guard.

**Tasks**
- [x] Define reconciliation triggers. (apology lexicon)
- [x] Define required conditions. (active cooldown or pending recovery)
- [x] Define partial recovery. (accelerated fraction per turn)
- [x] Define full recovery. (asymptotic heal + snap at epsilon)
- [x] Define repeated failed reconciliation. (max 2 effective apologies)
- [x] Add tests.

---

## EMO-002 — Long-term emotional arcs

**Goal:** represent slow relationship tendencies without rewriting the character's core personality.

**Tasks**
- [ ] Decide whether attachment traits are character-level, relationship-level, or both.
- [ ] Define slow-changing variables.
- [ ] Separate attachment from current mood.
- [ ] Define update rules.
- [ ] Define decay.
- [ ] Persist state.
- [ ] Add long-horizon tests.

**Do not**
- Replace the existing personality definition with mutable emotional state.
- Let temporary mood permanently rewrite character identity.

---

## PREF-001 — User preference learning

**Goal:** learn stable user preferences over repeated interactions.

**Tasks**
- [ ] Define explicit preference.
- [ ] Define inferred preference.
- [ ] Define confidence.
- [ ] Define confirmation threshold.
- [ ] Define correction/update behavior.
- [ ] Define forgetting behavior.
- [ ] Integrate with future memory subsystem.
- [ ] Add tests.

---

# 🟠 4. Phase 8 — Memory Evolution

## MEM-001 — Establish current retrieval baseline

**Goal:** measure keyword retrieval before replacing it.

**Tasks**
- [ ] Collect representative memory queries.
- [ ] Mark expected relevant memories.
- [ ] Run current keyword retrieval.
- [ ] Record recall/precision where practical.
- [ ] Record false positives.
- [ ] Record semantic misses.

**Acceptance criteria**
- A fixed memory benchmark exists.

---

## MEM-002 — Research local embedding models

**Goal:** identify an embedding model suitable for the target environment.

**Tasks**
- [ ] Find small embedding candidates.
- [ ] Check Indonesian support.
- [ ] Check multilingual performance.
- [ ] Check license.
- [ ] Check RAM/VRAM requirements.
- [ ] Measure embedding latency.
- [ ] Test on Veil-specific memory examples.
- [ ] Compare against keyword baseline.

**Decision gate**
- [ ] Continue only if embeddings show meaningful retrieval improvement.

---

## MEM-003 — Embedding abstraction

**Goal:** prevent the memory engine from becoming tied to one embedding implementation.

**Example interface**
```python
class Embedder(Protocol):
    def embed(self, text: str) -> list[float]:
        ...
```

**Tasks**
- [ ] Define interface.
- [ ] Add local implementation.
- [ ] Add mock implementation.
- [ ] Define embedding metadata/version.
- [ ] Add tests.

---

## MEM-004 — Semantic memory retrieval

**Goal:** retrieve memories by meaning rather than exact keywords.

**Target flow**
```text
query
  ↓
embedding
  ↓
candidate retrieval
  ↓
similarity
  + importance
  + recency
  + relationship relevance
  ↓
rank
  ↓
top-K memories
```

**Tasks**
- [ ] Define similarity threshold.
- [ ] Define top-K.
- [ ] Add hybrid keyword + semantic retrieval.
- [ ] Add ranking.
- [ ] Add memory filtering.
- [ ] Add tests.
- [ ] Benchmark against MEM-001.

**Acceptance criteria**
- Semantic/hybrid retrieval demonstrably improves the benchmark.
- Entire memory store is never injected by default.

---

## MEM-005 — Emotional ↔ factual memory cross-reference

**Goal:** preserve both factual information and its emotional context.

**Example**
```text
FACT:
User likes coffee.

EMOTIONAL:
User talked about coffee during a stressful event.
```

**Tasks**
- [ ] Define memory relationships.
- [ ] Define confidence.
- [ ] Prevent emotional memories from overwriting facts.
- [ ] Add retrieval behavior.
- [ ] Add tests.

---

## MEM-006 — Dream/consolidation cycle

**Goal:** consolidate redundant memories while protecting important history.

**Tasks**
- [ ] Define consolidation trigger.
- [ ] Define candidate selection.
- [ ] Define merge rules.
- [ ] Define importance adjustment.
- [ ] Define conflict resolution.
- [ ] Define protected memories.
- [ ] Implement dry-run mode.
- [ ] Test dry-run output.
- [ ] Only then consider automatic writes.

**Acceptance criteria**
- Consolidation can be inspected before mutating persistent memory.
- Protected memories cannot be silently deleted.

---

# 🟡 5. Phase 7 — Platform

## PLATFORM-001 — Select one platform

**Candidates**
- [ ] Web UI
- [ ] WhatsApp
- [ ] Discord

**Decision criteria**
- actual usage
- implementation cost
- authentication complexity
- 1-on-1 vs multi-user semantics
- persistence requirements
- maintenance burden

**Tasks**
- [ ] Compare candidates.
- [ ] Choose one.
- [ ] Document decision.
- [ ] Move the others to backlog.

**Do not**
- Implement all three simultaneously.

---

## PLATFORM-002 — Audit conversation scope

**Goal:** prevent a multi-user platform from corrupting personal relationship state.

**Current assumption**
```text
User
  ↕
PersonalityCore
```

**Potential model**
```text
User A ─┐
User B ─┼─ Conversation/Session ─ Character
User C ─┘
```

**Tasks**
- [ ] Identify 1-on-1 assumptions.
- [ ] Define user identity.
- [ ] Define conversation/session identity.
- [ ] Define memory ownership.
- [ ] Define relationship ownership.
- [ ] Add multi-user tests if applicable.

---

## PLATFORM-003 — TTS backlog

**Tasks**
- [ ] Define TTS adapter interface.
- [ ] Define voice configuration.
- [ ] Define emotion → voice mapping.
- [ ] Measure latency.
- [ ] Implement only after platform/core priority is stable.

---

## PLATFORM-004 — Mobile app evaluation

**Tasks**
- [ ] Validate actual need.
- [ ] Compare Web/PWA vs native.
- [ ] Estimate maintenance cost.
- [ ] Make explicit go/no-go decision.

---

# 🟢 6. Fine-Tuning — Stretch Goal

## TUNE-001 — Establish trigger

**Do not start training yet.**

Training is allowed only when:

```text
7B model
 +
prompt/context optimization
 +
runtime improvements
 ↓
specific persistent failures
```

**Tasks**
- [ ] Review seven-day failure log.
- [ ] Categorize failures.
- [ ] Attempt prompt fixes.
- [ ] Attempt context fixes.
- [ ] Attempt runtime/state fixes.
- [ ] Document failures that remain.

**Acceptance criteria**
- Each proposed training target has a concrete example and measurable failure condition.

---

## TUNE-002 — Stella dialogue dataset

**Tasks**
- [ ] Collect high-quality dialogue.
- [ ] Keep Indonesian/casual style consistent.
- [ ] Remove contradictory character behavior.
- [ ] Remove accidental assistant-style answers.
- [ ] Deduplicate.
- [ ] Separate training and evaluation sets.
- [ ] Preserve a held-out benchmark.

---

## TUNE-003 — LoRA experiment

**Tasks**
- [ ] Define target behavior.
- [ ] Select base model.
- [ ] Define LoRA configuration.
- [ ] Train small experiment.
- [ ] Compare against untuned model.
- [ ] Run fixed benchmark.
- [ ] Measure resource requirements.
- [ ] Decide keep/reject.

**Acceptance criteria**
- LoRA is retained only if it improves the target failure without unacceptable regressions.

---

## TUNE-004 — CPT

- [x] Keep out of current scope.

**Reason:** the project is optimizing character behavior/conditioning, not adding missing domain knowledge.

---

# ⚪ 7. Cross-Cutting Validation

## TEST-001 — Character regression suite

**Tasks**
- [ ] Personality consistency.
- [ ] Indonesian naturalness.
- [ ] Emotional responsiveness.
- [ ] Relationship behavior.
- [ ] Memory recall.
- [ ] State persistence.
- [ ] Character leakage.
- [ ] Assistant leakage.
- [ ] Long conversation behavior.

---

## TEST-002 — State regression

- [ ] Save/load state.
- [ ] Backup/restore.
- [ ] Schema migration.
- [ ] Failed migration recovery.
- [ ] Relationship persistence.

---

## TEST-003 — Memory regression

- [ ] Keyword baseline.
- [ ] Semantic retrieval.
- [ ] Hybrid retrieval.
- [ ] Memory ranking.
- [ ] Memory persistence.
- [ ] Consolidation dry-run.

---

# ⚪ 8. Backlog / Non-Goals

- [ ] CI/CD.
- [ ] Separate `ARCHITECTURE.md`.
- [ ] Full multi-platform rollout.
- [ ] Mobile app before need is proven.
- [ ] TTS-first development.
- [ ] CPT.
- [ ] Large vector database before benchmark evidence.
- [ ] Full autonomous-agent system.
- [ ] Complex multi-agent orchestration.

---

# Definition of Done — Current Roadmap

The roadmap's current core milestone is complete when:

- [ ] State has a tested backup/export path.
- [ ] 7B model has been evaluated against the 3B baseline.
- [ ] Context budgeting has been recalibrated using measurements.
- [ ] A concrete seven-day behavior log exists.
- [ ] Emotional relationship dynamics have explicit testable transitions.
- [ ] Semantic memory has been benchmarked against keyword retrieval.
- [ ] The selected memory approach is evidence-based.
- [ ] One platform has been selected rather than prematurely implementing several.
- [ ] Fine-tuning decisions are based on documented persistent failures.
- [ ] Regression benchmarks exist for character, state, and memory.

---

# Immediate Next Actions

Follow this exact order unless `PLAN.md` changes:

```text
STATE-001
   ↓
BASE-001
   ↓
MODEL-001
   ↓
MODEL-002
   ↓
MODEL-003
   ↓
MODEL-004
   ↓
MODEL-005
   ↓
EMO-001 / REL-001..004
   ↓
MEM-001
   ↓
MEM-002
   ↓
MEM-003 / MEM-004
   ↓
MEM-005 / MEM-006
   ↓
PLATFORM-001
   ↓
TUNE-001
   ↓
TUNE-002 / TUNE-003
```

**Do not start LoRA before TUNE-001's decision gate is satisfied.**
