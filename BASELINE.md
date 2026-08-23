# Baseline — Qwen2.5-3B-Instruct Q4_K_M (pre-migration reference)

> Captured 2026-08-23 per TODO BASE-001. Reference point the Qwen 7B candidate
> (MODEL-002..004) must be compared against. Reproduce with:
>
> ```bash
> python tools/state_backup.py export                                      # protect state
> python tools/bench.py                                                    # fixed 13-prompt set
> python tools/state_backup.py restore data/backups/<latest>.json --apply  # undo bench writes
> ```

## Model & Runtime Config

| Item | Value |
|------|-------|
| Model | `models/qwen2.5-3b-instruct-q4_k_m.gguf` (Q4_K_M, ~2.1 GB) |
| Context | `N_CTX = 4096` (train context 32768 — llama.cpp warns on load) |
| Context budgets (chars) | system 2500 / history 2500 / response 800 (`config.py`) |
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
