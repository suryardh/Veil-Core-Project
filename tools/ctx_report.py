"""MODEL-004: measure real token counts of every prompt component.

Loads the configured model (tokenizer only matters) and reports chars/tokens
per component under three scenario tiers: light / typical / worst case.
Run: python tools/ctx_report.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from llm.engine import LLMEngine  # runs _setup_cuda_paths() first — required for CUDA wheel
from personality import stella as identity
from personality.prompting import build_prompt
from personality.state import StellaState
from personality.rhythm import compute_rhythm
from personality.inactivity import compute_inactivity_context
from personality.analyzer import analyze

SAMPLE_USER = "aku kemarin ngga bisa tidur, pikiran berat banget soal kerjaan"
SAMPLE_OBSERVATION = ("Fotosintesis adalah proses tumbuhan mengubah cahaya matahari "
                      "menjadi energi kimia glukosa dengan bantuan klorofil dan air. ") * 5


def history_blocks(msgs):
    return "\n".join(f"<|im_start|>{r}\n{c}<|im_end|>" for r, c in msgs)


def main():
    engine = LLMEngine(config.MODEL_PATH)
    model = engine.model
    tok = lambda s: len(model.tokenize(s.encode("utf-8"), add_bos=False, special=True))

    identity_blob = f"{identity.BASE_IDENTITY}\n\n{identity.LANGUAGE_RULES}\n\n{identity.BEHAVIOR_RULES}"
    analysis = analyze(SAMPLE_USER)
    state = StellaState()  # defaults = warm/yearning mid-relationship
    state.emotional_summary_sample = None
    rhythm = compute_rhythm(state, analysis)
    inactivity = compute_inactivity_context(state, time.time())

    emotional_light = ""
    emotional_typical = "\n".join(
        f"- {'x' * 40} [positif]" for _ in range(5))
    system_light = build_prompt(identity_blob, state, emotional_light, inactivity, rhythm)
    system_typical = build_prompt(identity_blob, state, emotional_typical, inactivity, rhythm)

    hist_light = []
    hist_worst = [(("user" if i % 2 == 0 else "assistant"),
                   ("kalimat contoh percakapan bahasa indonesia sehari-hari " * 7)[:config.SHORT_TERM_MEMORY_LIMIT * 0 + 500])
                  for i in range(16)]
    history_light_s = history_blocks(hist_light[:4])
    history_worst_s = history_blocks(hist_worst)

    rows = [
        ("identity blob", identity_blob),
        ("system prompt (no emotion)", system_light),
        ("system prompt (5 emotion recs)", system_typical),
        ("history 4 msgs", history_light_s),
        ("history 16 msgs x~500c (worst)", history_worst_s),
        ("observation (max 500c)", SAMPLE_OBSERVATION[:500]),
        ("user input (sample)", SAMPLE_USER),
        ("chat template overhead", "<|im_start|>user\n<|im_end|>\n<|im_start|>assistant\n"),
    ]

    print(f"| Component | Chars | Tokens | Chars/Token |")
    print(f"|-----------|-------|--------|-------------|")
    ratios = []
    for name, s in rows:
        t = tok(s)
        r = len(s) / t if t else 0
        if len(s) > 200:
            ratios.append(r)
        print(f"| {name} | {len(s)} | {t} | {r:.2f} |")

    avg_ratio = sum(ratios) / len(ratios)
    worst_total_chars = len(system_typical) + len(history_worst_s) + 500 + len(SAMPLE_USER) + 60
    worst_total_tokens = tok(system_typical + history_worst_s + SAMPLE_OBSERVATION[:500] +
                             "\n<|im_start|>user\n" + SAMPLE_USER + "<|im_end|>\n<|im_start|>assistant\n")
    prompt_room = config.N_CTX - config.MAX_TOKENS
    print(f"\nWorst-case assembled prompt: {worst_total_chars} chars = {worst_total_tokens} tokens")
    print(f"Avg chars/token (Indonesian, long text): {avg_ratio:.2f}")
    print(f"N_CTX={config.N_CTX}, MAX_TOKENS={config.MAX_TOKENS} -> prompt room = {prompt_room} tokens")
    print(f"Worst case fits: {'YES' if worst_total_tokens <= prompt_room else 'NO — OVERFLOW RISK'}"
          f" ({prompt_room - worst_total_tokens} tokens spare)")


if __name__ == "__main__":
    main()
