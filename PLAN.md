# Veil Core — Plan

> Living document. Update whenever priorities or architectural decisions change.
> `AGENT.md` remains the source of truth for engineering rules and architecture.
> This document defines **what we prioritize and why**.
>
> **Current roadmap status:** Phase 0 — Repository Audit is the active priority. Existing roadmap phases remain preserved, but work that changes models or architecture should wait until the audit exit criteria are met.
>
> **Phase 0 status as of 2026-10-15: INCOMPLETE.** Of the seven Phase 0 exit
> criteria, six are **met** and one is **not met** (#3, AUDIT-004). A post-C1
> behavioural benchmark was executed successfully (13/13 prompts, process exit
> code 0, 105.4 s, `VEIL_TEMP=0.7`, CPU-only). Per-prompt expected behaviour
> (AUDIT-004 #1) and a positive long-term recall test (AUDIT-004 #2) are both
> complete. **AUDIT-004 remains not met** for two reasons: the long-conversation
> category is documented but not implemented in the runner, and no run has been
> scored against the B-01…B-13 criteria because `tools/bench.py` discards full
> responses. Phase 0 is **not** closed.
> See [Discrepancy register](#discrepancy-register-phase-0),
> [Post-C1 benchmark evidence](#post-c1-benchmark-evidence) and
> [AUDIT-006](#audit-006--smallest-safe-next-change-decided-2026-10-15).

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
- [x] Define the smallest safe next change. — see [AUDIT-006 decision record](#audit-006--smallest-safe-next-change-decided-2026-10-15)
- [x] Record rollback steps and data-protection requirements. — see [AUDIT-006 decision record](#audit-006--smallest-safe-next-change-decided-2026-10-15) §Rollback plan
- [ ] Update this plan only where audit evidence justifies a change.

**Output:** a short decision record explaining what will change, what will remain, why, and how to roll back.

> The two boxed items are answered by [AUDIT-006 decision record](#audit-006--smallest-safe-next-change-decided-2026-10-15),
> which records the smallest safe next change and its `git revert` rollback
> procedure. **That record is a decision only — the proposed `tools/bench.py`
> `--output` capture is not implemented**, and its implementation needs separate
> authorization. The remaining items above are still genuinely open.

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

### Exit criteria status (re-verified 2026-10-15)

| # | Criterion | State | Evidence |
|---|---|---|---|
| 1 | Model/runtime configuration verified | **MET** | measured at runtime: 7B, `N_CTX=4096`, `CTX_PROMPT_CHAR_LIMIT=14528`, effective temp **0.7** (see D-2) |
| 2 | Request-lifecycle diagram | **MET** | `README.md` Architecture section; traced through `personality/core.py` → `core/agent.py` → `llm/engine.py` |
| 3 | Tests + behavior benchmark recorded | **NOT MET** | 141 deterministic assertions pass in the isolated verification run; `tools/bench.py` **has now been executed** on the current 7B model — post-C1 run 2026-10-15, 13/13 prompts, exit code 0 (see [Post-C1 benchmark evidence](#post-c1-benchmark-evidence)). Expected behaviour for all 13 prompts is now specified (`BASELINE.md` §Benchmark specification), but the long-conversation category is documented-not-implemented and **no run has been assessed against the criteria** — retained outputs are 110-char previews only |
| 4 | Backup/restore path verified | **MET** | checksummed envelope, tamper + future-schema rejection, v2→v3 migration — covered by the suite |
| 5 | Module dispositions | **MET** | `README.md` structure + `AGENT.md` §Discrepancies |
| 6 | Conflicts recorded | **MET** | this section |
| 7 | Next step evidence-backed + rollback | **MET** | AUDIT-006 records the smallest safe next change (`tools/bench.py` full-response capture), its evidence (`tools/bench.py:105-106` discards full text; nothing imports the module), and a `git revert` rollback procedure — see [AUDIT-006](#audit-006--smallest-safe-next-change-decided-2026-10-15). Implementation still needs its own authorization and D-2 remains open |

### Discrepancy register (Phase 0)

| ID | Finding | Severity | Status | Owning phase |
|---|---|---|---|---|
| D-1 | `core/bootstrap.py` error text said "Download Qwen2.5-**3B**" while the configured path is the **7B** model | Low | **Fixed in working tree, uncommitted** — message now derives the filename from `config.MODEL_PATH`; not present in `e827a8e` | Phase 0 |
| D-2 | `.env` (gitignored) sets `VEIL_TEMP=0.7`, making the tuned `0.6` default unreachable. Effective runtime temperature is **0.7**. Decide the intended value before recording a behavioural baseline | Medium | **Open — needs a decision.** Precedence verified: OS env > `.env` > code default. See §External references for a caution about unratified temperature values | Phase 1 |
| D-3 | `BASELINE.md` "Model & Runtime Config" described the 3B/CPU reference, not current config | Medium | **Fixed** in `e827a8e` | Phase 0 |
| D-4 | `core/agent.py` omitted a 1-char separator from context accounting; assembled prompt could reach `limit + 1` | Low | **Fixed in working tree, uncommitted** — worst case now exactly `limit` (14528); not present in `e827a8e` | Phase 2 |
| D-5 | Context-guard tests used a 216-char system marker, so the binding branch was never exercised | Low | **Fixed in working tree, uncommitted** — 3 boundary assertions added to `test_agent.py` at realistic system size; not present in `e827a8e` | Phase 2 |
| D-6 | `AGENT.md` prohibits a PersonalityCore god object; `personality/core.py` owns emotion, conflict, inactivity, memory, tools, prompting and persistence | Medium | **Open — documented gap** | Phase 4 / 5 |
| D-7 | `AGENT.md`/`DESIGN.md` require YAML-driven characters; Stella is hardcoded in `personality/stella.py` and imported by the core | Medium | **Open — documented gap.** See §External references for a precedent that data-driven persona config is low-risk | Phase 6 |
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

## AUDIT-006 — Smallest safe next change (decided 2026-10-15)

### Recommendation

**Persist full prompt/response records from `tools/bench.py` to an explicit,
gitignored output path.**

### Problem it addresses

`tools/bench.py:105-106` keeps only a character count and a truncated preview:

```python
preview = " ".join(response.split())[: args.preview_chars]   # default 110
rows.append((category, prompt, dt, len(response), preview))
```

The runner writes **no file at all** — output is stdout-only, and nothing
imports `tools/bench.py`. Verified: `app.py`, `app_tui.py` and `core/bootstrap.py`
do not reference it, and no module imports it. So after any run the full response
text is **unrecoverable**.

That is the concrete reason the post-C1 run could not be scored against the
per-prompt criteria in `BASELINE.md` §Benchmark specification. Three of the 13
responses exceeded the 110-character preview (B-10 = 385, B-08 = 163,
B-01 = 122), so whole-response criteria were undecidable and behavioural
assessment was recorded as `Not assessed`.

This blocks **exit criterion 3**, the last NOT MET criterion, and it also blocks
any future assessment of long-conversation behaviour, which cannot be judged from
110-character snippets.

### Smallest plausible scope

Append one JSONL record per prompt containing at minimum
`{id, category, prompt, latency, chars, response}` beside the existing stdout
report, written to a path supplied by a new `--output` flag. Nothing else in the
runner changes. No prompt, no prompt ordering, no warmup, no sampling.

### Files likely to change

| File | Change |
|---|---|
| `tools/bench.py` | add `--output` argument; append the full `response` to a JSONL record |

### Files that must remain untouched

`config.py`, `.env`, `personality/*`, `core/*`, `memory/*`, `llm/*`, `tools/bench.py`'s
prompt list and warmup logic, `data/`, `memory/*.json`, `logs/`, `models/`.

### Prerequisites

1. Commit the currently unstaged work (`BASELINE.md`, `PLAN.md`, and the D-1/D-4/D-5
   fixes) so the tree is checkpointed. This is hygiene, not part of the change.
2. **Owner decision on D-2** — the run must use a ratified temperature, otherwise
   the captured responses inherit the same unratified-0.7 caveat.
3. A GGUF run needs explicit authorization, as with the post-C1 run.

### Acceptance criteria

1. A run writes one JSONL line per prompt containing the complete response text.
2. Each record round-trips: `response` length equals the reported `Chars`.
3. Output path is supplied by flag and defaults to nowhere — without `--output`
   the runner behaves exactly as today.
4. Output lands under a `.gitignore`d path (`tmp/` or `temp/` are already listed)
   and **never** under `logs/`, `data/`, or `memory/`.
5. `python -B test_bench_reaction_guard.py` still passes 15/15 — the C1 guard is
   untouched.
6. A subsequent authorized run can score all 13 prompts against B-01…B-13.

### Risks and benefits

**Risk — low.** One file, additive, no runtime path (`tools/bench.py` is imported
by nothing). Worst case is an extra file in a gitignored directory. The main
hazard is choosing an output path inside `logs/`, which is protected; the
acceptance criteria forbid that explicitly.

**Benefit — unblocks the last failing exit criterion** and makes every future
benchmark scorable instead of unassessable. It also becomes the prerequisite for
scoring long-conversation behaviour, whatever form that eventually takes.

### Why this rather than the alternatives

| Alternative | Why deferred |
|---|---|
| Implement the long-conversation category | Larger: needs scenario grouping, session control and cross-turn assertion points in the runner. It is also **unassessable without this change first**, since cross-turn behaviour cannot be judged from truncated previews. Build the capture, then the category. |
| Run `tools/ctx_report.py` to close D-8 | Owned by Phase 2 and does not move exit criterion 3. It also `chdir`s to the repository root at `tools/ctx_report.py:12` and constructs `LLMEngine` at line 33, so it needs a GGUF authorization and carries a production-write path that the sandbox wrapper must contain. |
| Resolve D-2 | **Needs owner decision.** It is a product decision about the intended temperature, not a code change. `config.py` is protected audit scope and `.env` is gitignored (`.gitignore:14`). The audit must not make this call. |
| Fix D-10 | Same `config.py` protection. **Needs owner decision.** Confirmed still live: `float(os.getenv("VEIL_TEMP", "0.6"))` raises `ValueError` when the variable is set but empty. |
| D-12 / D-13 | Phase 5 product decisions. Neither blocks exit criterion 3, and D-13 did not affect the recall result (the query shared tokens with the fact, so the absent relevance floor was not exercised). Defer deliberately. |
| Commit pending work | Necessary as a prerequisite checkpoint, but it is not itself a change to the codebase. |

### Rollback plan

1. **Checkpoint.** Record the pre-change HEAD SHA before starting. The change must
   land as exactly one commit touching exactly one file. No `git reset --hard`, no
   `git clean`, no deletion of untracked files.
2. **Identify the change.** `git show --stat <sha>` must list only
   `tools/bench.py`. If it lists anything else, the commit is not the audited
   change and must not be reverted as if it were.
3. **Revert.** `git revert --no-edit <sha>` — this adds a new commit and leaves
   history intact. No force, no amend, no rebase, no reset. Reverting the single
   file restores byte-identical previous behaviour, including stdout-only output.
4. **Verify unrelated work is intact.** `git status --short` must still show the
   untracked user files (`problem.md`, `test_agent_audit.py`,
   `test_bench_reaction_guard.py`, `test_memory_extraction_guard.py`,
   `veil_personality_benchmark.json`) and any intentionally unstaged edits.
5. **Validate after rollback.** `python -B test_bench_reaction_guard.py` → 15/15;
   re-hash the protected files (`config.py`, `.env`, `data/state.json`,
   `memory/long_term.json`, `logs/`) against their recorded baselines.
6. **Persistent data.** The change writes only to a gitignored path, so rollback
   is code-only. Any benchmark run itself still writes `data/state.json` and
   `logs/`; those writes must be contained by the existing sandbox wrapper
   (`%TEMP%\veil-audit\run_bench_sandbox.py`), which confines CWD and refuses to
   run when sandbox state has drifted. No configuration or memory-store change is
   involved, so nothing needs restoring there.

## External references

> **These are not repository evidence.** Everything in this section comes from a
> third-party public repository, not from Veil. It carries no weight in any exit
> criterion and must not be treated as verification. It is recorded only so that
> the reasoning behind D-2 and D-7 is auditable.

### `rayenfeng/riko_project` (MIT, 1.2k stars, 5 commits)

An anime voice companion: OpenAI API (`gpt-4.1-mini`), GPT-SoVITS for TTS,
Faster-Whisper for ASR. **Four Python files, ~6.4 KB in total.**

Two points were relevant to Veil:

- **D-7 precedent.** The project loads its persona from `character_config.yaml`
  at import time, proving the data-driven-character pattern is simple and
  widely used. It is **not** a template for Veil: the file is 562 bytes with a
  single flat preset, whereas `AGENT.md` requires layered
  `characters/stella/{character,personality,lore,rules}.yaml`. The value of the
  reference is that it lowers the perceived risk of the fix, nothing more.
- **D-2 caution.** `server/process/llm_funcs/llm_scr.py` hardcodes
  `temperature=1, top_p=1` with no recorded rationale. That is precisely the
  unratified-value failure mode D-2 concerns, and it argues that Veil's
  temperature decision should be justified rather than inherited.

**What it does not provide.** Riko has no long-term memory, no extraction, no
relevance ranking, no relationship state, no context budget or truncation, and
no benchmark, evaluation harness or tests. It therefore offers nothing for
AUDIT-004, AUDIT-006, D-8, D-10 or D-13 — it simply does not implement the
subsystems those items concern.

**Popularity is not an architectural argument.** The star count reflects
interest in a voice-companion demo, not in character-runtime design. Veil has 44
Python modules, five-dimensional relationship state, conflict dynamics,
multi-store memory and 141 deterministic assertions; Riko has none of these.
This reference must not be used to justify simplifying Veil.

## Remaining Phase 0 work

Phase 0 cannot close until these are done. Ordered by dependency:

1. **AUDIT-004 specification** — **partially done 2026-10-15.** The
   long-conversation category and the per-prompt expected-behaviour criteria
   (B-01…B-13) are now specified in `BASELINE.md` §Benchmark specification.
   Still outstanding: the category is **documented but not implemented** — the
   runner is a flat loop with no scenario grouping or session control — and no
   run has been assessed against the criteria, because only 110-character
   previews survive. Exit criterion 3 stays **NOT MET**.
2. **AUDIT-004 positive long-term recall** — **done 2026-10-15.** An isolated
   integration test stored a synthetic fact and recalled it through the real
   pipeline with short-term history empty: STORE / RETRIEVAL / INJECT / ANSWER
   all passed, and a negative control with an empty store confirms the recall
   is attributable to long-term memory. Details and limits in `BASELINE.md`
   §Positive long-term recall. It is **not** wired into `tools/bench.py`, so it
   does not by itself lift exit criterion 3.
3. **D-2 temperature decision** — `PLAN.md` §Phase 1 requires this resolved
   *before* a behavioural baseline is treated as authoritative. The 0.7 used
   above is unratified.
4. **AUDIT-006** — **decided 2026-10-15.** The smallest safe next change is to
   persist full responses from `tools/bench.py` to a gitignored path; see
   [AUDIT-006](#audit-006--smallest-safe-next-change-decided-2026-10-15) for the
   decision and rollback plan. Implementation is **not** authorized by that
   decision — it needs its own go-ahead.
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
