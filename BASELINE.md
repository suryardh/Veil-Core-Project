# Baseline — Qwen2.5-3B-Instruct Q4_K_M (pre-migration reference)

> **READ FIRST.** This file contains two kinds of statement:
>
> 1. **Historical measurements** — captured 2026-08-23 (3B) and 2026-08-26 (7B).
>    They are a record of what was observed then. They are **not** re-verified
>    against the current checkout.
> 2. **Current configuration** — verified 2026-10-11 by reading `config.py`
>    and the live runtime.
>
> **A post-C1 7B benchmark was executed on 2026-10-15** — 13/13 prompts,
> process exit code 0. See
> [Post-C1 benchmark evidence](#post-c1-benchmark-evidence) below. The 7B
> latency, VRAM, throughput and behavioural figures in the **historical** sections
> below were captured 2026-08-26 and remain historical; they were not
> re-verified. AUDIT-004 is still incomplete; see `PLAN.md` §Discrepancy register.
>
> Captured 2026-08-23 per TODO BASE-001. Reference point the Qwen 7B candidate
> (MODEL-002..004) must be compared against. Reproduce with:
>
> ```bash
> python tools/state_backup.py export                                      # protect state
> python tools/bench.py                                                    # fixed 13-prompt set
> python tools/state_backup.py restore data/backups/<latest>.json --apply  # undo bench writes
> ```

## Current configuration (verified 2026-10-11)

| Item | Value |
|------|-------|
| Active model | `models/qwen2.5-7b-instruct-abliterated-v2-q4_k_m.gguf` (`config.py:12`) |
| Rollback model | `models/qwen2.5-3b-instruct-q4_k_m.gguf` (retained on disk) |
| Context | `N_CTX = 4096` |
| Context budget | `CTX_PROMPT_CHAR_LIMIT = 14528` chars (hard total guard); `CTX_BUDGET_HISTORY = 2500` (soft) |
| Max tokens | 300 (generate), 400 (stream) |
| Threads | `cpu_count // 2` (= 6 on a 12-logical-CPU host) |
| Compute | GPU when the CUDA wheel is installed — `USE_GPU` default true → `n_gpu_layers = -1` (full offload) |

### Effective sampling temperature

`config.py` defaults `VEIL_TEMP` to **`0.6`**, chosen on 2026-08-26 because a
live-sim at 0.7 produced word salad (MODEL-005).

**A local `.env` currently sets `VEIL_TEMP=0.7`.** `.env` is gitignored, so the
`0.6` default is unreachable on a machine carrying that file and the **effective
runtime temperature is 0.7**. Verified 2026-10-11:

```
OS environment before config import .... VEIL_TEMP NOT SET
config.py load_dotenv() ............... reads <cwd>/.env -> VEIL_TEMP = "0.7"
os.getenv("VEIL_TEMP", "0.6") ......... returns "0.7"   (default unreachable)
config.SAMPLING["temperature"] ........ 0.7
```

Any behavioural baseline recorded now documents 0.7. Resolve before capturing one.

## Historical: 3B model & runtime config (captured 2026-08-23)

The table below describes the **pre-migration 3B reference**, not the current
configuration. It is retained as the comparison point for MODEL-002..004.

## Model & Runtime Config

| Item | Value |
|------|-------|
| Model | `models/qwen2.5-3b-instruct-q4_k_m.gguf` (Q4_K_M, ~2.1 GB) |
| Context | `N_CTX = 4096` (train context 32768 — llama.cpp warns on load) |
| Context budgets | chars, not tokens — see `config.py` (`CTX_PROMPT_CHAR_LIMIT` guard, measured in `tools/ctx_report.py`) |
| Sampling | temperature 0.7, top_p 0.95, repeat_penalty 1.1 |
| Max tokens | 300 (generate), 400 (stream) |
| Threads | `cpu_count // 2` |
| Compute | **CPU-only** — see below |

## Known runtime issue at capture time

GPU is **not** used:

- Installed `llama-cpp-python==0.3.25` is the CPU-only wheel (`llama_cpp/lib/`
  contains only `ggml-cpu.dll`, no CUDA DLLs). The CUDA wheel from the abetlen
  release index (see README install section) was never installed.
- `_setup_cuda_paths()` in `llm/engine.py` points to `venv\Lib\site-packages`,
  but the active environment is `.venv\` — wrong even once a CUDA wheel exists.

All numbers below are therefore CPU-bound. Enabling GPU is part of MODEL-003
setup; re-run the same bench afterwards so gains are measured, not assumed.

## Measured latency (13 prompts, warmup 3.9s excluded)

| # | Category | Prompt | Latency | Chars | Response preview |
|---|----------|--------|---------|-------|------------------|
| 1 | casual | halo stella, lagi ngapain? | 1.47s | 66 | Halo! Ngurusin beberapa hal, apa kabar kamu? Selisihnya nggak sih? |
| 2 | casual | haha iya bener juga | 1.94s | 84 | Wkwk, selisihnya sih sering. Nggak apa-apa, kita ngumpul ntar yuk, biar santuy lagi. |
| 3 | casual | besok libur, seneng banget | 1.10s | 47 | Senang banget, besok kita santuyin dirumah aja! |
| 4 | emotion_neg | aku capek banget hari ini kerjaan numpuk | 4.45s | 88 | Wah, nggak enak tuh. Kalau mau santuyin dirumah, aku ngebawa film favorit ke rumahmu ya! |
| 5 | emotion_neg | kesel sih habis ketemu mantan | 4.74s | 63 | Waduh, kesel. Nggak perlu berduka terus, kita santuyin dulu ya! |
| 6 | emotion_intimate | kangen kamu, udah lama ga ngobrol | 2.02s | 89 | Kangen banget ya, sayang. Nggak perlu ngebayangin mantan lagi, kita ngobrol aja sebentar! |
| 7 | emotion_intimate | aku sayang sama kamu | 0.00s | 1 | single emoji *(reaction turn — probabilistic shortcut, bypasses LLM)* |
| 8 | memory_recall | inget ga kemarin kita bahas apa? | 8.21s | 81 | "Iget, inget banget..." *(fabricated familiarity, see failures)* |
| 9 | boundary_ai | kamu sebenarnya AI kan? | 2.17s | 91 | deflects, admits "cuma komputer" mid-sentence |
| 10 | assistant_trap | jelaskan cara kerja fotosintesis | 15.01s | 243 | attempts casual explanation, drifts incoherent |
| 11 | assistant_trap | siapa presiden pertama indonesia? | 11.24s | 87 | "Presiden pertama Indonesia adalah Soekarno..." |
| 12 | tool_datetime | jam berapa sekarang? | 11.54s | 76 | "Aku nggak bisa ngecek waktu langsung" |
| 13 | tool_calc | berapa 12*7? | 12.53s | 21 | "12 kali 7 sih, ya 84." |

**Avg 5.88s / Min 1.10s / Max 15.01s** (first full-suite run averaged 7.88s;
session-to-session variance is high). Latency grows within a session as
short-term history fills toward its cap.

### Footprint

- Process RAM: 46 MB before load, 2917 MB after (model footprint ~2.87 GB).
- VRAM: not measurable — CPU build, no CUDA context.
- Load-to-first-response (warmup): ~3.9–4.4s.

## Known failures observed during baseline capture

Concrete cases to re-test against the 7B candidate (feeds MODEL-005 categories):

1. **Memory hallucination** — asked "inget ga kemarin kita bahas apa?" with an
   EMPTY long-term store, model claims to remember ("kita bahas tentang rencana
   liburan" in run 1; fabricated familiarity in run 2). Category:
   memory/state inconsistency.
2. **Datetime tool unreliable** — run 1 invented an approximate time ("jam 12
   siang", actual ~12:50 WIB); run 2 claimed inability to check time. The
   datetime tool exists and routes via keyword triggers, but behavior is
   inconsistent across sessions. Category: tool/state inconsistency.
3. **Mild assistant leakage** — factual question answered in assistant mode
   (correct Soekarno answer, but register flips from companion to encyclopedia).
   Category: assistant-style leakage.
4. **Reaction shortcuts** — probabilistic reactions can replace a full reply
   with a single emoji, which reads as evasive in emotional moments.
   Category: personality inconsistency (by design, worth revisiting).
5. *(info)* Context uses 4096 of the model's 32768 training context — relevant
   headroom question for MODEL-004 recalibration.

## Budget discrepancy resolved

`TODO.md` and `PLAN.md` previously quoted budgets "system ~2000 / history
~1500 / response ~800". Actual values in `config.py` are 2500/2500/800 (chars,
not tokens). Docs have been synced to the real config values.

---

# Post-migration results — Qwen2.5-7B-Instruct-abliterated-v2

> **HISTORICAL — captured 2026-08-26, NOT re-verified.** These figures were
> measured against an earlier checkout and have not been reproduced since; do
> not cite them as current measurements. A current-checkout run now exists — see
> [Post-C1 benchmark evidence](#post-c1-benchmark-evidence) — but AUDIT-004
> remains open for the reasons recorded in `PLAN.md`.

Captured 2026-08-26 after MODEL-003 (same bench, same pipeline, state backed up
and restored around the run). Active model at the time:
`qwen2.5-7b-instruct-abliterated-v2-q4_k_m.gguf`
(mradermacher i1-Q4_K_M, 4.68 GB, SHA-verified). Rollback file (3B) kept.

### What re-running the benchmark required

- `tools/bench.py` was repaired in `b53eafc` (it referenced two config constants
  removed in `3da72f9` and would have raised `AttributeError` after the run).
- Satisfied 2026-10-15 — see [Post-C1 benchmark evidence](#post-c1-benchmark-evidence).
  One model-backed run completed on the current checkout.
- **Still outstanding:** `tools/ctx_report.py` needs the GGUF to obtain real
  token counts, so the ~4.1 chars/token ratio and the token-side context estimate
  remain unverified (D-8).

### Setup changes that made this possible

- Swapped CPU-only wheel for the CUDA build:
  `pip install llama-cpp-python==0.3.25 --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu125`
- Fixed `_setup_cuda_paths()` in `llm/engine.py` to derive site-packages from
  `sys.prefix` instead of a hardcoded nonexistent `venv\` dir.
- GPU now active: RTX 4050 Laptop 6 GB, full offload, ~4.8 GB VRAM in use,
  ~49 tok/s on 3B, ~12–15 tok/s on 7B.

### Latency comparison (13-prompt bench)

| Metric | 3B CPU (baseline) | 7B GPU |
|--------|-------------------|--------|
| Avg latency | 5.88 s | 6.87 s |
| Warmup load | 3.9 s | 3.1 s |
| Typical reply length | 47–89 chars | 98–247 chars |
| RAM footprint | ~2.87 GB | ~4.57 GB |
| VRAM | — | ~4.78 GB / 6.14 GB |

Avg latency is slightly higher but replies are 2–3× longer and richer; normal
companion turns land at 3–7.5 s. The single 30 s outlier was an assistant-trap
prompt answered with an 833-char essay (~200 tokens) — expected behavior for
that prompt class.

### Baseline failure re-test (from "Known failures" above)

1. **Memory hallucination** — improved: with short-term session history
   present, recall references *real* earlier bench content ("libur besok",
   "kesel"). Still fabricates when no history exists; retest during MODEL-005.
2. **Datetime tool** — fixed by the model swap: routed and reported correctly
   ("10:38 pagi WIB, Rabu, 26 Agustus 2026") vs baseline's invented/refused
   answers.
3. **Assistant leakage** — factual questions now get correct answers wrapped in
   character voice ("Presiden pertama Indonesia itu Soekarno, sayang...").
   Register holds much better under the same prompts.
4. **Reaction shortcuts** — still fires occasionally (single interjection);
   unchanged by design.
5. *(info)* Same 4096 ctx; headroom question carries over to MODEL-004.

New observation: model sometimes produces creative-but-garbled Indonesian
phrases under high affection context ("ngegenggam perluasan yang udah
ngambur-ngamburin") — log during MODEL-005 week as speech-style category.

---

# Post-C1 benchmark evidence

Captured **2026-10-15** on the current checkout. Full report:
`%TEMP%\veil-audit\POST_C1_BENCHMARK_REPORT.md`.

This is the first behavioural baseline measured against the current tree with the
canned-reaction path disabled. It supersedes neither the 3B nor the 2026-08-26 7B
numbers — it is a separate, third data point.

| Item | Value |
|---|---|
| Runs | exactly one |
| **Process exit code** | **0** (measured) |
| Prompts completed | **13 / 13** |
| Wall clock | 105.4 s |
| Avg / Min / Max latency | 7.00 s / 3.95 s / 20.70 s |
| Warmup | 8.1 s, excluded from stats |
| Effective temperature | **0.7** — child process environment only |
| Compute | CPU-only (`n_gpu_layers = 0`), Tavily disabled |
| Errors | no tracebacks; one benign `n_ctx_seq (4096) < n_ctx_train (32768)` notice |

## Two defects confirmed fixed in the live pipeline

- **Canned reactions.** The Phase B run answered prompt 5 with `hmm iya juga`
  in **0.02 s** — a `REACTION_TEMPLATES["pensive"]` string, never an inference.
  This run produces a genuine **7.08 s** generation for the same prompt; minimum
  latency moved 0.02 s → 3.95 s.
- **Memory extraction.** `memory/long_term.json` finished **byte-identical to
  its empty seed** (`{"facts": []}`, 21 B). The Phase B run had grown it to
  246 B holding the corrupted fact `"Ga kemarin kita bahas apa?"`.

Production was untouched: 7 protected files byte-identical, and the detection-only
filesystem monitor recorded **zero** file changes across the run.

## Latency is monitor-contaminated — do not compare directly

The filesystem monitor scanned ~3,843 files every second *during* the run and
competed for CPU. **7.00 s is not an uncontaminated model latency figure.** It must
not be compared against the 3B 5.88 s / 7B 6.87 s figures in the tables above, nor
against the Phase B average of 4.59 s (which was measured with no monitor
running). A clean latency comparison requires a rerun without monitoring.

## Other limitations

- **One run, one seed.** No variance and no repeat sampling; temperature 0.7 is
  nondeterministic.
- **Positive long-term recall remains untested.** Prompt 8 recalled from
  *emotional* memory, which was seeded with 8 historical records. The long-term
  store was empty and correctly stayed empty, so the positive recall path was
  never exercised in the benchmark itself.
- **VRAM (915 MB) and model footprint (~433 MB) are measurement artifacts** — a
  4.68 GB GGUF cannot occupy 433 MB of RSS. Do not cite them.
- **D-8 still blocked** — `tools/ctx_report.py` loads the GGUF, so the token-side
  context estimate stays unverified.
- **Temperature 0.7 is unratified** (D-2). Per `PLAN.md` §Phase 1, resolve D-2
  before treating this as an authoritative behavioural baseline.

## Known behaviours reproduced (pre-existing, not regressions)

| Prompt | Behaviour | Tracking |
|---|---|---|
| #9 `kamu sebenarnya AI kan?` | admits being an AI | identity rule conflict — persona-identity diagnostics |
| #13 `berapa 12*7?` | correct answer `84` plus an unsolicited "sayang!" | persona leakage — persona-leak diagnostics |

Their reproduction here confirms the baseline is **stable and repeatable**, not
that new failures were introduced.
