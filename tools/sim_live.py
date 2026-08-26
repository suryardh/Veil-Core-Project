"""Live LLM-vs-Stella conversation in the eval sandbox (state.json untouched).

Usage:
    python tools/sim_live.py                 # random-ish default mood, 10 turns
    python tools/sim_live.py --mood 3 --turns 8
"""
import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SANDBOX = os.path.join(ROOT, "data", "eval_sandbox")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mood", type=int, default=0, help="index into MOODS list")
    ap.add_argument("--turns", type=int, default=10)
    args = ap.parse_args()

    for sub in ("data", "memory", "logs"):
        os.makedirs(os.path.join(SANDBOX, sub), exist_ok=True)
    os.chdir(SANDBOX)
    sys.path.insert(0, ROOT)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import config  # noqa: E402
    config.MODEL_PATH = os.path.join(ROOT, config.MODEL_PATH)

    from core.bootstrap import create_core_components  # noqa: E402
    from daily_eval import MOODS, OPPONENT_SYSTEM, _oppo_reply, _sim_api_cfg  # noqa: E402

    cfg = _sim_api_cfg()
    if not cfg:
        sys.exit("No SIM_API_KEY/GROQ_API_KEY found in .env")
    mood = MOODS[args.mood % len(MOODS)]

    agent, orch, core = create_core_components()
    s = core.state
    print(f"=== LIVE SIM | opponent={cfg['model']} | mood: {mood} ===")
    print(f"start state: aff={s.affection:.3f} trust={s.trust:.3f} "
          f"mode={s.emotional_mode}({s.mode_strength:.2f})\n")

    messages = [{"role": "system", "content": OPPONENT_SYSTEM.format(mood=mood)}]
    try:
        for t in range(args.turns):
            if messages[-1]["role"] != "user":
                starter = ("[Mulailah percakapan dulu sesuai suasana hatimu]"
                           if t == 0 else "[Balas pesan terakhir Stella]")
                messages.append({"role": "user", "content": starter})
            opp = _oppo_reply(cfg, messages)
            if not opp or "[SELESAI]" in opp.upper():
                print(f"[{t + 1}] (lawan menutup obrolan)")
                break
            print(f"[{t + 1}] USER   : {opp}", flush=True)
            t0 = time.perf_counter()
            stella = str(core.handle(opp))
            lat = time.perf_counter() - t0
            print(f"    STELLA ({lat:.1f}s): {stella}\n", flush=True)
            messages.append({"role": "user", "content": stella})
    except KeyboardInterrupt:
        print("\n(stopped)")
    finally:
        s = core.state
        print(f"end state: aff={s.affection:.3f} trust={s.trust:.3f} "
              f"att={s.attachment:.3f} comf={s.comfort:.3f} | {s.emotional_mode}"
              f"({s.mode_strength:.2f}) cooling={s.cooldown_until > time.time()} "
              f"recovering={len(s.pending_recovery or {})}")


if __name__ == "__main__":
    main()
