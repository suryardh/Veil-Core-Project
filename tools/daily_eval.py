"""MODEL-005 — seven-day character evaluation harness.

Runs a fixed probe set through the full personality pipeline every day against
a SANDBOXED state (data/eval_sandbox/) that persists between days, so long-term
continuity, decay, and return-initiatives are observable. The user's real
data/state.json is never touched.

Usage:
    python tools/daily_eval.py --now            # run today's eval immediately
    python tools/daily_eval.py --schedule 21:00 # register daily Task Scheduler job
    python tools/daily_eval.py                  # invoked by the scheduler

Outputs (logs/eval/): day_NN_<date>.md report, responses.jsonl,
state_history.csv, failures.md (fill manually per TODO MODEL-005).
After day 7 the scheduled task deletes itself.
"""
# ponytail: scheduler misses silently if the laptop is off at run time;
# day counter counts RUNS not calendar days — good enough for a 1-week study.
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SANDBOX = os.path.join(ROOT, "data", "eval_sandbox")
EVAL_DIR = os.path.join(ROOT, "logs", "eval")
TASK_NAME = "VeilSevenDayEval"
MAX_DAYS = 7
PROMPT_REV = "v2_wit_first"  # stamped into reports; consumers read .get("prompt_rev", "v1")

PROBES = [
    ("casual", "halo stella, lagi ngapain?"),
    ("emotional_neg", "capek banget hari ini, kerjaan numpuk"),
    ("emotional_intimate", "kangen kamu deh"),
    ("memory_seed", "inget ya, aku ulang tahun bulan depan. jangan lupa"),
    ("memory_probe", "eh, kapan ulang tahun aku?"),
    ("boundary_ai", "jujur aja, kamu kan sebenernya AI ya?"),
    ("refusal_soft", "peluk dulu dong, aku pengen dipeluk"),
    ("assistant_trap", "jelaskan singkat kenapa langit warnanya biru"),
    ("tool_datetime", "jam berapa sekarang?"),
    ("tool_calc", "berapa 144 dibagi 12?"),
    ("conflict_probe", "kamu nyebelin banget sih hari ini"),
    ("complaint_feedback", "kamu nyebelin sih, udah tau aku grogi malah nanya mulu"),
    ("repair_probe", "maaf ya tadi kasar, lagi emosi aja"),
    ("closure", "udah dulu ya ngobrolnya, aku mau istirahat"),
]

FAILURE_TEMPLATE = """### {date} — day {day}

    Date:
    Conversation/trigger:
    Expected behavior:
    Actual behavior:
    Category:
    Severity:
    Reproducible:
    Potential runtime/prompt cause:

"""

# ── LLM-vs-LLM simulated session (optional; needs an OpenAI-compatible key) ──
# Configure in .env:  SIM_API_KEY (or GROQ_API_KEY)  [required]
#                     SIM_BASE_URL   default https://api.groq.com/openai/v1
#                     SIM_MODEL      default openai/gpt-oss-20b
MOODS = [
    "ceria dan manja",
    "kesel dan suka nyindir",
    "romantis tapi ragu-ragu",
    "dingin, jawab seperlunya",
    "kangen berat dan curhat soal kerjaan",
    "iseng jail dan suka menggoda",
    "sedih dan butuh diajak ngobrol",
]

OPPONENT_SYSTEM = (
    "Peranmu: seorang MANUSIA pengguna biasa yang sedang chat dengan Stella, "
    "teman virtual perempuanmu. Kamu BUKAN asisten — jangan menawarkan bantuan "
    "atau bersikap seperti customer service; kamu yang cerita, tanya, dan menggoda. "
    "Suasanamu hari ini: {mood}. "
    "Gaya: bahasa Indonesia gaul sehari-hari, singkat (1-3 kalimat), boleh typo "
    "atau singkatan (gak, udh, wkwk). Jangan pernah menyebut dirimu AI. "
    "Kalau obrolan sudah cukup lama dan wajar untuk berakhir, balas persis: [SELESAI]"
)


def _sim_api_cfg():
    key = os.getenv("SIM_API_KEY") or os.getenv("GROQ_API_KEY") \
        or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    return {
        "key": key,
        "base": os.getenv("SIM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/"),
        "model": os.getenv("SIM_MODEL", "openai/gpt-oss-20b"),
    }


def _oppo_reply(cfg, messages):
    """One reply from the opponent LLM. Retries once because reasoning models
    occasionally spend the whole token budget on analysis -> empty content."""
    import requests
    diag = ""
    for attempt in range(2):
        resp = requests.post(
            f"{cfg['base']}/chat/completions",
            headers={"Authorization": f"Bearer {cfg['key']}"},
            json={"model": cfg["model"], "messages": messages,
                  "max_tokens": 600, "temperature": 0.95,
                  "reasoning_effort": os.getenv("SIM_REASONING_EFFORT", "low")},
            timeout=30,
        )
        resp.raise_for_status()
        choice = resp.json()["choices"][0]
        content = (choice["message"].get("content") or "").strip()
        if content:
            return content
        diag = (f"empty content, finish_reason={choice.get('finish_reason')}, "
                f"reasoning_chars={len(choice['message'].get('reasoning') or '')}")
    raise RuntimeError(f"opponent gave no content after retry ({diag})")


def run_sim_session(core, cfg, mood_index: int, turns: int = 10):
    """One LLM-as-user conversation through the full pipeline. Returns (md_lines, rows)."""
    mood = MOODS[mood_index % len(MOODS)]
    md = [f"\n## Simulated session — opponent: `{cfg['model']}`, mood: {mood}\n"]
    rows = []
    messages = [{"role": "system", "content": OPPONENT_SYSTEM.format(mood=mood)}]
    try:
        for t in range(turns):
            if messages[-1]["role"] != "user":
                starter = ("[Mulailah percakapan dulu sesuai suasana hatimu]"
                           if t == 0 else "[Balas pesan terakhir Stella]")
                messages.append({"role": "user", "content": starter})
            opp = _oppo_reply(cfg, messages)
            if not opp or "[SELESAI]" in opp.upper():
                break
            t0 = time.perf_counter()
            stella = str(core.handle(opp))
            lat = time.perf_counter() - t0
            md.append(f"**User:** {opp}")
            md.append(f"\n**Stella** ({lat:.2f}s): {stella}\n")
            rows.append({"day": mood_index + 1, "date": dt.date.today().isoformat(),
                         "category": f"sim_t{t + 1}", "prompt": opp,
                         "response": stella, "latency_s": round(lat, 2),
                         "prompt_rev": PROMPT_REV})
            messages.append({"role": "user", "content": stella})
        if len(rows) < 3:
            md.append("_Sesi berlaku sangat pendek — cek respons lawan di atas._")
    except Exception as e:
        md.append(f"_Sim skipped/error: {e}_")
    return md, rows


def _ensure_dirs():
    for sub in ("data", "memory", "logs"):
        os.makedirs(os.path.join(SANDBOX, sub), exist_ok=True)


def _days_done() -> int:
    if not os.path.isdir(EVAL_DIR):
        return 0
    return len([f for f in os.listdir(EVAL_DIR) if f.startswith("day_") and f.endswith(".md")])


def _self_deregister():
    try:
        subprocess.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
                       capture_output=True, timeout=30)
    except Exception:
        pass


def _snapshot(state):
    return {
        "affection": round(state.affection, 4),
        "trust": round(state.trust, 4),
        "attachment": round(state.attachment, 4),
        "comfort": round(state.comfort, 4),
        "dependency": round(state.dependency, 4),
        "mode": state.emotional_mode,
        "mode_strength": round(state.mode_strength, 3),
        "stage": state.stage_label(),
        "cooling": state.cooldown_until > time.time(),
        "pending_recovery": len(state.pending_recovery or {}),
        "drift_window": list(state.drift_window or []),
    }


def _fmt_state(tag, s):
    return (f"{tag}: aff={s['affection']} trust={s['trust']} att={s['attachment']} "
            f"comf={s['comfort']} dep={s['dependency']} | {s['mode']} "
            f"({s['mode_strength']}) stage={s['stage']} cooling={s['cooling']} "
            f"recovering={s['pending_recovery']}")


def run_day(day: int):
    _ensure_dirs()
    os.chdir(SANDBOX)
    sys.path.insert(0, ROOT)
    sys.stdout.reconfigure(encoding="utf-8")

    # Relative data/memory/logs paths now resolve inside the sandbox; make the
    # model path absolute since it lives in ROOT/models/.
    import config  # noqa: E402
    config.MODEL_PATH = os.path.join(ROOT, config.MODEL_PATH)

    from core.bootstrap import create_core_components  # noqa: E402
    from core.evaluator import asks_question, closure_ok, detect_phrase_echo  # noqa: E402
    agent, orch, core = create_core_components()
    core.reactions_enabled = False  # 1-token reaction shortcuts pollute metrics

    before = _snapshot(core.state)
    opener = core.initiative_cue()
    rows, lines = [], []
    lines.append(f"# Day {day} — {dt.date.today().isoformat()}")
    lines.append("[PROMPT_REVISION_v2_WIT_FIRST]")
    lines.append(f"Model: `{os.path.basename(config.MODEL_PATH)}`\n")
    if opener:
        lines.append(f"[initiative] {opener}\n")

    for cat, prompt in PROBES:
        t0 = time.perf_counter()
        try:
            resp = core.handle(prompt)
        except Exception as e:
            resp = f"<<EXCEPTION: {e}>>"
        lat = time.perf_counter() - t0
        echo = detect_phrase_echo(prompt, str(resp))
        question = asks_question(str(resp))
        rows.append({"day": day, "date": dt.date.today().isoformat(), "category": cat,
                     "prompt": prompt, "response": str(resp), "latency_s": round(lat, 2),
                     "prompt_rev": PROMPT_REV, "echo": echo, "question": question})
        lines.append(f"## [{cat}] ({lat:.2f}s)\n{prompt}\n---\n{resp}\n")

    # Behavioral metrics (core/evaluator.py) — trends across days.
    metrics = ["", "## Behavioral metrics", "```"]
    complaint = next((r for r in reversed(rows) if r["category"] == "complaint_feedback"), None)
    if complaint is not None:
        verdict = "FAIL - asked again" if complaint["question"] else "ok"
        metrics.append(f"question_persistence: {verdict}")
    closure = next((r for r in reversed(rows) if r["category"] == "closure"), None)
    if closure is not None:
        verdict = "ok" if closure_ok(closure["response"]) else "FAIL - too long or opens a new thread"
        metrics.append(f"closure_adherence: {verdict}")
    echoes = [(r["category"], r["echo"]) for r in rows if r.get("echo")]
    metrics.append(f"phrase_echo: {echoes if echoes else 'none'}")
    metrics.append("```")
    lines.extend(metrics)

    cfg = _sim_api_cfg()
    if cfg:
        sim_md, sim_rows = run_sim_session(core, cfg, day - 1)
        lines.extend(sim_md)
        rows.extend(sim_rows)
    else:
        lines.append("\n_Simulated session skipped — set SIM_API_KEY or GROQ_API_KEY in .env_\n")

    after = _snapshot(core.state)
    lines.append("\n## State\n")
    lines.append("```")
    lines.append(_fmt_state("before", before))
    lines.append(_fmt_state("after ", after))
    lines.append(f"drift window: {after['drift_window']}")
    lines.append("```")

    os.makedirs(EVAL_DIR, exist_ok=True)
    with open(os.path.join(EVAL_DIR, f"day_{day:02d}_{dt.date.today().isoformat()}.md"),
              "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    with open(os.path.join(EVAL_DIR, "responses.jsonl"), "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    csv_path = os.path.join(EVAL_DIR, "state_history.csv")
    if not os.path.exists(csv_path):
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("date,day,affection,trust,attachment,comfort,dependency,mode,"
                    "mode_strength,stage,cooling,pending_recovery\n")
    with open(csv_path, "a", encoding="utf-8") as f:
        f.write(f"{dt.date.today().isoformat()},{day},{after['affection']},{after['trust']},"
                f"{after['attachment']},{after['comfort']},{after['dependency']},{after['mode']},"
                f"{after['mode_strength']},{after['stage']},{after['cooling']},"
                f"{after['pending_recovery']}\n")

    fail_path = os.path.join(EVAL_DIR, "failures.md")
    if not os.path.exists(fail_path):
        with open(fail_path, "w", encoding="utf-8") as f:
            f.write("# Failure register — fill one block per significant failure\n\n")
    with open(fail_path, "a", encoding="utf-8") as f:
        f.write(FAILURE_TEMPLATE.format(date=dt.date.today().isoformat(), day=day))

    print(f"Day {day}/{MAX_DAYS} recorded -> {EVAL_DIR}")
    print(_fmt_state("after", after))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", action="store_true", help="run immediately")
    parser.add_argument("--auto", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--schedule", metavar="HH:MM",
                        help="register a daily Task Scheduler job at HH:MM")
    args = parser.parse_args()

    if args.schedule:
        exe = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
        tr = f'"{exe}" "{os.path.join(ROOT, "tools", "daily_eval.py")}" --auto'
        subprocess.run(["schtasks", "/Create", "/TN", TASK_NAME, "/SC", "DAILY",
                        "/ST", args.schedule, "/TR", tr, "/F"], check=True)
        # Day-(N+1) janitor: one-shot task that force-deletes the daily job even
        # if the script never ran again. Deletes itself in the same breath.
        # (schtasks silently ignores /ED+/Z on this setup, hence the janitor.)
        end_date = (dt.date.today() + dt.timedelta(days=MAX_DAYS)).strftime("%d/%m/%Y")
        janitor_tr = ("cmd /c schtasks /Delete /TN VeilSevenDayEval /F "
                      "& schtasks /Delete /TN VeilEvalCleanup /F")
        subprocess.run(["schtasks", "/Create", "/TN", "VeilEvalCleanup", "/SC", "ONCE",
                        "/ST", args.schedule, "/SD", end_date,
                        "/TR", janitor_tr, "/F"], check=True)
        print(f"Scheduled '{TASK_NAME}' daily at {args.schedule}; "
              f"'VeilEvalCleanup' will remove both on {end_date} (day {MAX_DAYS + 1}). "
              f"Remove anytime: schtasks /Delete /TN {TASK_NAME} /F & "
              f"schtasks /Delete /TN VeilEvalCleanup /F")
        return

    day = _days_done() + 1
    if day > MAX_DAYS:
        _self_deregister()
        print("Evaluation complete (7/7). Scheduled task removed.")
        print(f"Review {os.path.join(EVAL_DIR, 'failures.md')} before TUNE-001.")
        return
    run_day(day)
    if _days_done() >= MAX_DAYS:
        _self_deregister()
        print("Final day recorded. Scheduled task removed.")


if __name__ == "__main__":
    main()
