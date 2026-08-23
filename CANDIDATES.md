# MODEL-002 — Candidate Evaluation: Uncensored Qwen 7B-class GGUF

> Evaluated 2026-08-23. Requirement added by user: candidate must be uncensored
> (refusal-free), because "unnecessary disclaimer/refusal" and "assistant-style
> leakage" are documented baseline failures (see `BASELINE.md`). Reference
> numbers come from `BASELINE.md` (Qwen2.5-3B Q4_K_M, CPU-only, avg 5.88s).

## Hardware/runtime constraints

- Inference: llama.cpp via `llama-cpp-python==0.3.25` (Jun 2026 build — supports
  the Qwen3 architecture, which landed in llama.cpp mid-2025).
- Currently **CPU-only**; 7–8B Q4_K_M ≈ 4.4–5.0 GB file → expect ~5–6 GB process
  RAM (extrapolated from 3B's measured 2.87 GB footprint).
- Runtime builds raw ChatML prompts (`<|im_start|>/<|im_end|>`) without chat
  templates — this matters for Qwen3 (see thinking-mode caveat below).

## Candidates

### 1. huihui-ai/Qwen2.5-7B-Instruct-abliterated-v2 — SELECTED (primary)

| Item | Value |
|------|-------|
| Exact base | Qwen/Qwen2.5-7B-Instruct (7.6B params) |
| Method | Abliteration v2 (author states improvement over v1) |
| Quantization target | Q4_K_M ≈ 4.7 GB (community quants, 14 listed on HF model tree) |
| Context length | 32K native |
| License | Apache-2.0 |
| Source | huggingface.co/huihui-ai/Qwen2.5-7B-Instruct-abliterated-v2 |
| RAM (est.) | ~5–5.5 GB process, CPU |
| Expected speed | ~2–2.5× current 3B latency → avg ~12–15 s/response CPU |
| Roleplay/Indonesian | Qwen2.5 officially covers 29+ languages incl. Indonesian; same model family as the working 3B |

**Why selected:** zero-integration-risk drop-in — identical architecture,
tokenizer, and ChatML format to the currently running model. Removes refusals
while keeping instruct behavior. Rollback is trivial (keep 3B config).

### 2. DavidAU/Qwen3-8B-Hivemind-Instruct-Heretic-Abliterated-Uncensored-NEO-Imatrix-GGUF

| Item | Value |
|------|-------|
| Exact base | Qwen3-8B finetune ("Hivemind" instruct merge) |
| Method | Heretic refusal-removal (card: refusals 99/100 → 8/100, KL divergence 0.02 = low behavioral damage) |
| Quantization target | Q4_K_M-imat ≈ 5 GB (imatrix quants published in repo) |
| Context length | Native 32K (card markets "256k" — unverified) |
| License | Apache-2.0 |
| Source | huggingface.co/DavidAU/Qwen3-8B-Hivemind-Instruct-Heretic-Abliterated-Uncensored-NEO-Imatrix-GGUF |
| RAM (est.) | ~5.5–6 GB process, CPU |
| Roleplay/Indonesian | Card is roleplay-oriented ("vivid prose", NSFW-capable); Qwen3 officially supports more languages than 2.5 |

**Caveats:** Qwen3 emits `<think>...</think>` blocks unless disabled — this
runtime's raw-prompt builder has no template support yet, so either add a
`/no_think` soft switch to the system prompt or strip `<think>` in
`utils/text.py`. Heretic method preserves quality better than classic
abliteration, but repo provenance is single-maintainer and marketing-heavy;
verify the Q4_K_M-imat file loads before committing.

### 3. huihui-ai/Huihui-Qwen3-8B-abliterated-v2

Same profile as #2 minus the RP finetune: cleaner provenance (well-known
abliteration maintainer), newer/faster ablation method, but no roleplay-tuned
flavor and the same Qwen3 thinking-mode integration cost.

## Rejected / noted

- **Goekdeniz-Guelmez/Josiefied-Qwen3-8B-abliterated-v1** — trained-in rude/sassy
  persona would contaminate Stella's warm identity. Skip.
- **Qwen3.8-27B-Uncensored-GGUF** (Aug 2026) — far beyond this machine's budget.
  Skip.
- Note for MODEL-003: the README's CUDA wheel instructions point to the old
  release index. Current prebuilt CUDA wheels live at
  `pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124`
  (cu118…cu132). Latest binding version is 0.3.35 (Aug 2026).

## Decision

Run candidate 1 first: bench it against `BASELINE.md` with the existing
13-prompt set, then start the MODEL-005 week of normal use. If refusals still
leak or roleplay depth disappoints, candidate 2 becomes experiment two (requires
the `<think>`-handling change first). The 3B setup stays intact as rollback.
