import os
import re
import sys
import time
import json
import config
from core.agent import VeilAgent
from core.orchestrator import Orchestrator
from personality.core import PersonalityCore
from personality.analyzer import analyze
from personality.state import StellaState
from personality.persistence import save_state, load_state, SCHEMA_VERSION
from personality.conflict import detect_conflict, on_interaction, compute_drift, is_apology
from utils.text import _EMOJI_RE
from tools.state_backup import export_backup, restore_backup, checksum_payload
from memory.emotional import EmotionalMemory
from memory.extractor import extract_fact
from memory.long_term import LongTermMemory
from memory.short_term import ShortTermMemory
from tools.web.search import WebSearchTool
from tools.system.calculator import CalculatorTool
from tools.system.datetime import DateTimeTool

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS  {name}")
        passed += 1
    else:
        print(f"  FAIL  {name}  {detail}")
        failed += 1


# ── 1. TOOL TESTS (deterministic, no LLM needed) ──────────────

print("\n--- Tool: Calculator ---")
r = CalculatorTool().execute("2 + 3")
test("basic addition", r.success and "= 5" in r.data.get("result", ""), f"got: {r}")

r = CalculatorTool().execute("15% of 200")
test("percentage of", r.success and "15% dari 200 = 30" in r.data.get("result", ""), f"got: {r}")

r = CalculatorTool().execute("sqrt(25)")
test("sqrt function", r.success and "= 5" in r.data.get("result", ""), f"got: {r}")

r = CalculatorTool().execute("")
test("empty input", not r.success and "Tidak ada ekspresi" in (r.error or ""), f"got: {r}")

r = CalculatorTool().execute("__import__('os')")
test("injection blocked", not r.success and "tidak diizinkan" in (r.error or ""), f"got: {r}")

r = CalculatorTool().execute("1/0")
test("division by zero", not r.success and "Pembagian dengan nol" in (r.error or ""), f"got: {r}")

print("\n--- Tool: Datetime ---")
r = DateTimeTool().execute()
data = r.data or ""
test("returns date and time", r.success and "Tanggal:" in data and "Waktu:" in data)
test("uses Indonesian day",
     any(d in data for d in ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]),
     f"got: {data[:50]}")
test("uses Indonesian month",
     any(m in data for m in ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
                           "Juli", "Agustus", "September", "Oktober", "November", "Desember"]),
     f"got: {data[:50]}")
test("timezone is WIB", "WIB" in data, f"got: {data}")

# ── 2. LONG-TERM MEMORY TESTS ─────────────────────────────────

print("\n--- Long-Term Memory ---")
TEST_LTM_PATH = "logs/test_long_term.json"
try:
    ltm = LongTermMemory(filepath=TEST_LTM_PATH)
    ltm.remember("hobi", "saya suka coding")
    data = ltm.store.get("facts", [])
    test("fact was stored", any("coding" in f["content"] for f in data))
    test("fact has timestamp", all("timestamp" in f for f in data))
    test("fact has importance", any(f.get("importance", 0) >= 1 for f in data))

    ltm.remember("hobi", "saya suka coding")
    data2 = ltm.store.get("facts", [])
    test("no duplicate stored", len(data2) == len(data))

    fact = extract_fact("nama panggilan saya Rei")
    ltm.remember(fact["type"], fact["content"], importance=fact["importance"])
    data3 = ltm.store.get("facts", [])
    test("new fact stored", any("Rei" in f["content"] for f in data3))
    for f in data3:
        if "Rei" in f["content"]:
            test("importance 4 for personal facts", f.get("importance") == 4, f"got {f.get('importance')}")
finally:
    if os.path.exists(TEST_LTM_PATH):
        os.remove(TEST_LTM_PATH)

# ── 3. SHORT-TERM MEMORY OVERFLOW TESTS ──────────────────────

print("\n--- Short-Term Memory Overflow ---")
stm = ShortTermMemory(limit=8)
for i in range(20):
    stm.add_message("user", f"pesan ke-{i}")
    stm.add_message("assistant", f"respon ke-{i}")
test("context not empty", len(stm.history) > 0)
test("history respects limit", len(stm.history) <= 16, f"got {len(stm.history)} messages")

stm.add_message("user", "wkwk")
test("ignore useless messages", not any("wkwk" in m["content"] for m in stm.history))

stm.add_message("user", "a" * 1000)
test("truncate long messages", all(len(m["content"]) <= 503 for m in stm.history))

# ── 4. EMOTIONAL + PERSONALITY TESTS (deterministic) ─────────

print("\n--- Emotional Analysis ---")
r = analyze("aku sayang kamu")
test("intimate emotion", r.emotion == "intimate" and r.valence > 0)

r = analyze("kesel ah")
test("negative emotion", r.emotion == "negative" and r.valence < 0)

r = analyze("makasih")
test("positive emotion", r.emotion == "positive" and r.valence > 0)

r = analyze("")
test("empty returns neutral", r.emotion == "neutral")

r = analyze("aku semangat banget hari ini")
test("positive semangat", "positive" in r.emotion and r.valence > 0)

r = analyze("aku takut kamu pergi")
test("takut + pergi negative", r.valence < 0, f"val={r.valence}")

r = analyze("kamu keren banget")
test("positive keren", r.valence > 0, f"val={r.valence}")

r = analyze("aku ga peduli")
test("ga peduli negative", r.valence < 0, f"val={r.valence}")

r = analyze("tidak bahagia")
test("tidak bahagia is negative", r.emotion == "negative" and r.valence < 0, f"emo={r.emotion} val={r.valence}")

r = analyze("aku ga sayang kamu")
test("ga sayang is negative", r.emotion == "negative" and r.valence < -0.3, f"emo={r.emotion} val={r.valence}")

r = analyze("lagi bete nih")
test("negative bete", r.valence < 0, f"val={r.valence}")

print("\n--- State Management ---")
s = StellaState()
test("default stage sayang", s.stage_label() == "sayang")
test("default mood yearning", s.dominant_mood() == "yearning")

s.update_from_interaction("positive", 0.8, 0.9)
test("affection increased", s.affection > 0)

s.update_from_interaction("negative", 0.9, 0.9)
test("trust decreased after negative", s.trust < 0.8)

s3 = StellaState()
s3.affection = 0.5
s3.decay()
test("decay reduces affection", 0 < s3.affection < 0.5)

s2 = StellaState()
s2.update_from_interaction("intimate", 1.0, 0.95)
test("intimate boosts stage", s2.stage_label() != "kenalan")

print("\n--- Emotional Memory ---")
TEST_EM_PATH = "logs/test_emotional.json"
try:
    em = EmotionalMemory(filepath=TEST_EM_PATH)
    em.record("interaction", "halo", 0.1, 0.1)
    test("salience filter", len(em.records) == 0)

    em.record("interaction", "aku sayang kamu", 0.8, 0.8)
    test("record stored", len(em.records) == 1)

    em.record("interaction", "aku sayang kamu", 0.8, 0.8)
    test("recurrence merged", len(em.records) == 1 and em.records[0]["recurrence"] == 2)

    summary = em.emotional_summary()
    test("summary is string", isinstance(summary, str))
    em.clear()
finally:
    if os.path.exists(TEST_EM_PATH):
        os.remove(TEST_EM_PATH)

# ── 4b. STATE BACKUP / RESTORE (deterministic) ────────────────

print("\n--- State Backup / Restore ---")
TEST_STATE = "logs/test_state.json"
TEST_BDIR = "logs/test_backups"
tampered = newer = ""
try:
    save_state(StellaState(affection=0.42, trust=0.33), TEST_STATE)
    bpath = export_backup(TEST_STATE, TEST_BDIR)
    test("backup file created", os.path.exists(bpath), f"missing: {bpath}")

    with open(bpath, encoding="utf-8") as f:
        env = json.load(f)
    test("backup metadata present",
         all(k in env for k in ("backup_version", "created_at", "schema_version", "checksum", "payload")))
    test("schema version recorded", env["schema_version"] == SCHEMA_VERSION, f"got {env['schema_version']}")
    test("checksum matches payload", env["checksum"] == checksum_payload(env["payload"]))
    test("payload round-trips", abs(env["payload"]["state"]["affection"] - 0.42) < 1e-9)

    save_state(StellaState(affection=0.9), TEST_STATE)  # corrupt live state
    ok = restore_backup(bpath, TEST_STATE, apply=True)
    test("apply restores state", ok)
    live = load_state(TEST_STATE)
    test("restored values match backup", abs(live.affection - 0.42) < 1e-9 and abs(live.trust - 0.33) < 1e-9,
         f"got affection={live.affection} trust={live.trust}")

    save_state(StellaState(affection=0.7), TEST_STATE)
    ok = restore_backup(bpath, TEST_STATE, apply=False)
    live = load_state(TEST_STATE)
    test("verify-only leaves original untouched", ok and abs(live.affection - 0.7) < 1e-9)

    tampered = bpath + ".tampered"
    with open(tampered, "w", encoding="utf-8") as f:
        json.dump({**env, "checksum": "deadbeef"}, f)
    try:
        restore_backup(tampered, TEST_STATE, apply=False)
        rejected = False
    except ValueError:
        rejected = True
    test("tampered backup rejected", rejected)

    newer = bpath + ".newer"
    with open(newer, "w", encoding="utf-8") as f:
        json.dump({**env, "schema_version": 99}, f)
    # checksum no longer covers the edited schema_version field... recompute so only schema check fires
    with open(newer, encoding="utf-8") as f:
        bad_env = json.load(f)
    bad_env["payload"] = dict(env["payload"], version=99)
    bad_env["checksum"] = checksum_payload(bad_env["payload"])
    with open(newer, "w", encoding="utf-8") as f:
        json.dump(bad_env, f)
    try:
        restore_backup(newer, TEST_STATE, apply=False)
        future_rejected = False
    except ValueError:
        future_rejected = True
    test("newer-schema backup rejected", future_rejected)
finally:
    for p in (TEST_STATE, tampered, newer):
        if p and os.path.exists(p):
            os.remove(p)
    if os.path.exists(TEST_BDIR):
        import shutil
        shutil.rmtree(TEST_BDIR)

# ── 4c. CONTEXT BUDGET GUARD (deterministic) ──────────────────

print("\n--- Context Budget Guard ---")
try:
    agent = object.__new__(VeilAgent)
    agent.short_memory = ShortTermMemory(limit=8)
    SYSTEM = "IDENTITY-MARKER " + ("x" * 200)
    BIG = ("kalimat panjang bahasa indonesia untuk mengisi riwayat obrolan " * 8)[:400]

    for i in range(16):
        agent.short_memory.add_message("user" if i % 2 == 0 else "assistant", BIG + f" [{i}]")

    p = agent._assemble_prompt(SYSTEM, "halo")
    test("guard: prompt within hard limit", len(p) <= config.CTX_PROMPT_CHAR_LIMIT,
         f"got {len(p)} > {config.CTX_PROMPT_CHAR_LIMIT}")
    test("guard: system block intact under full history", p.startswith(f"<|im_start|>system\n{SYSTEM}<|im_end|>\n"))
    test("guard: ends with assistant suffix", p.endswith("<|im_start|>assistant\n"))
    test("guard: oldest dropped, newest kept",
         "[0]" not in p.split("<|im_start|>user")[1] and "[14]" in p)

    p2 = agent._assemble_prompt(SYSTEM, "A" * 30000)
    test("guard: giant input capped", len(p2) <= config.CTX_PROMPT_CHAR_LIMIT,
         f"got {len(p2)}")
    test("guard: system survives giant input", p2.startswith(f"<|im_start|>system\n{SYSTEM}<|im_end|>\n"))

    agent.small = ShortTermMemory(limit=8)
    agent.short_memory.clear()
    agent.short_memory.add_message("user", "pesan-pertama-yang-harus-hilang")
    agent.short_memory.add_message("assistant", "ok")
    p3 = agent._assemble_prompt(SYSTEM, "halo lagi")
    test("guard: normal path keeps short history", "pesan-pertama-yang-harus-hilang" in p3)
finally:
    pass

# ── 4d. CONFLICT / COOLDOWN / RECOVERY (deterministic) ────────

print("\n--- Conflict Dynamics ---")
NOW = 1_000_000.0
try:
    ev = detect_conflict("kamu bego banget sih!!")
    test("conflict: directed insult detected", ev is not None and ev.severity >= 0.55,
         f"got {ev}")
    test("conflict: third-party venting ignored", detect_conflict("bos gw bego banget") is None)
    test("conflict: self-directed ignored", detect_conflict("aku bego banget ya") is None)
    test("conflict: abandonment detected", detect_conflict("pergi sana aja deh kamu") is not None)
    test("conflict: neutral chat ignored", detect_conflict("lagi ngapain sayang?") is None)
    test("apology: 'ya ampun' exclamation excluded", not is_apology("ya ampun, seru banget!"))
    test("apology: genuine ampun accepted", is_apology("ampun, aku salah banget"))

    s = StellaState(trust=0.8, affection=0.6, comfort=0.7, attachment=0.5)
    a_neg = analyze("kamu bego banget!!")
    info = on_interaction(s, "kamu bego banget!!", a_neg, NOW)
    test("cycle: conflict event returned", info["event"] is not None)
    test("cycle: trust dropped", s.trust < 0.8 - 0.05, f"got {s.trust}")
    test("cycle: cooldown entered", s.cooldown_until > NOW)
    test("cycle: withdrawn mode set", s.emotional_mode == "withdrawn")
    test("cycle: recovery gap recorded", sum((s.pending_recovery or {}).values()) > 0.02,
         f"got {s.pending_recovery}")

    # damping while cooling down
    hot = StellaState(affection=0.5, trust=0.5, comfort=0.5, attachment=0.5)
    cold = StellaState(affection=0.5, trust=0.5, comfort=0.5, attachment=0.5)
    cold.cooldown_until = NOW + 600
    a_pos = analyze("makasih ya sayang")
    hot.update_from_interaction(a_pos.emotion, a_pos.arousal, a_pos.confidence)
    cold.update_from_interaction(a_pos.emotion, a_pos.arousal, a_pos.confidence, damping=0.35)
    test("cooldown: positive gains damped", cold.affection < hot.affection,
         f"hot={hot.affection} cold={cold.affection}")

    # recovery after cooldown expiry — gradual, never instant
    r = StellaState(trust=0.8, affection=0.6, comfort=0.7, attachment=0.5)
    on_interaction(r, "kamu bego banget!!", a_neg, NOW, cooldown_base_s=100)
    gaps0 = sum(r.pending_recovery.values())
    on_interaction(r, "makasih ya sayang", a_pos, NOW + 50)   # still cooling → no heal yet
    test("recovery: none during cooldown", abs(sum(r.pending_recovery.values()) - gaps0) < 1e-9)
    on_interaction(r, "maaf ya aku kejam", a_pos, NOW + 200)  # apology + expired
    gaps1 = sum(r.pending_recovery.values())
    test("recovery: gradual, no instant reset", 0 < gaps1 < gaps0 * 0.75,
         f"gaps0={gaps0:.3f} gaps1={gaps1:.3f}")
    for i in range(30):
        on_interaction(r, "makasih ya", a_pos, NOW + 300 + i * 60)
    test("recovery: fully healed eventually", len(r.pending_recovery) == 0 and r.conflict_severity == 0.0,
         f"left={r.pending_recovery}")
    test("recovery: never overshoots baseline", r.trust <= 0.8 + 1e-9 and r.comfort <= 0.7 + 1e-9)

    # reconciliation halves active cooldown; diminishing repeats
    q = StellaState()
    on_interaction(q, "pergi saja kamu", analyze("pergi saja kamu"), NOW, cooldown_base_s=1000)
    cd0 = q.cooldown_until - NOW
    on_interaction(q, "maaf ya", analyze("maaf ya"), NOW + 10)
    # halving is relative to the moment of apology: (NOW+10) + (cd0-10)/2
    expected_until = (NOW + 10) + (cd0 - 10) * 0.5
    test("reconcile: cooldown halved", abs(q.cooldown_until - expected_until) < 0.01,
         f"cd0={cd0:.0f} until={q.cooldown_until:.1f} expected={expected_until:.1f}")
    for _ in range(3):
        on_interaction(q, "maaf maaf maaf", analyze("maaf ya"), NOW + 20)
    # second apology still counts (count<=2), third+ stop helping
    expected_final = (NOW + 20) + (expected_until - (NOW + 20)) * 0.5
    test("reconcile: repeat apologies stop helping",
         q.apology_count == 4 and abs(q.cooldown_until - expected_final) < 0.01,
         f"count={q.apology_count} until={q.cooldown_until:.1f} expected={expected_final:.1f}")

    # EMO-001 drift classification
    test("drift: insufficient samples", compute_drift([0.5, 0.4]) == "insufficient")
    test("drift: stable under noise", compute_drift([0.3, -0.2, 0.1, -0.1, 0.05]) == "stable")
    test("drift: positive pattern", compute_drift([0.5] * 5) == "positive")
    test("drift: negative pattern", compute_drift([-0.6] * 6) == "negative")

    # persistence: v3 roundtrip + legacy v2 migration
    p = StellaState(pending_recovery={"trust": 0.05}, drift_window=[0.3, -0.1], cooldown_until=123.45)
    save_state(p, TEST_STATE)
    lp = load_state(TEST_STATE)
    test("persist: v3 fields round-trip",
         abs(lp.pending_recovery["trust"] - 0.05) < 1e-9 and lp.drift_window == [0.3, -0.1]
         and abs(lp.cooldown_until - 123.45) < 1e-9)
    import json as _json
    legacy = {"version": 2, "state": {"affection": 0.5, "trust": 0.6}}
    with open(TEST_STATE, "w", encoding="utf-8") as f:
        _json.dump(legacy, f)
    lv = load_state(TEST_STATE)
    test("persist: legacy v2 migrates to v3",
         lv.conflict_severity == 0.0 and lv.pending_recovery == {} and lv.drift_window == []
         and abs(lv.affection - 0.5) < 1e-9)
finally:
    if os.path.exists(TEST_STATE):
        os.remove(TEST_STATE)

print("\n--- Output Sanitizer ---")
from utils.text import sanitize_llm_output as _san
test("sanitizer: leading tic chain stripped",
     _san("Gas, wkwk, halo sayang") == "Halo sayang", f"got {_san('Gas, wkwk, halo sayang')!r}")
test("sanitizer: sentence-initial Gas removed",
     _san("Mantap. Gas, lanjut!") == "Mantap. lanjut!", f"got {_san('Mantap. Gas, lanjut!')!r}")
test("sanitizer: pure reaction preserved", _san("wkwk") == "wkwk")
test("sanitizer: normal text untouched", _san("aku kangen kamu") == "Aku kangen kamu")
test("sanitizer: jakartan pronouns normalized",
     _san("nanti gw bales sama lo") == "Nanti aku bales sama kamu",
     f"got {_san('nanti gw bales sama lo')!r}")
q_wrapped = '"film itu keren banget"'
test("sanitizer: wrapping quotes unwrapped",
     _san(q_wrapped) == "Film itu keren banget",
     f"got {_san(q_wrapped)!r}")
multi_emoji = "seru banget! \U0001F60F\U0001F680\U0001F4A5\U0001F95C"
test("sanitizer: emoji capped at two", len(_EMOJI_RE.findall(_san(multi_emoji))) <= 2,
     f"got {_san(multi_emoji)!r}")
test("sanitizer: hiks removed", _san("ya udahlah hiks. aku baik") == "Ya udahlah aku baik",
     f"got {_san('ya udahlah hiks. aku baik')!r}")
gas_spam = "Gas buka linknya ya? Gas kita bahas. Gas jangan drama!"
g = _san(gas_spam)
test("sanitizer: gas spam reduced to at most one",
     len(re.findall(r"\bgas\b", g, re.I)) <= 1 and "  " not in g, f"got {g!r}")
test("sanitizer: saya normalized", _san("saya tungguin kamu") == "Aku tungguin kamu")
from utils.text import collapse_sayang, strip_emojis_from_source
sayang_spam = "kamu sayang aku sayang kamu sayang"
test("glue: sayang capped per message",
     collapse_sayang(sayang_spam) == "kamu sayang aku kamu",
     f"got {collapse_sayang(sayang_spam)!r}")
cat_chat = "wkwk \U0001F431\U0001F4AC"
cat_reply = "seru! \U0001F431\U0001F4AC"
echoed = strip_emojis_from_source(cat_reply, cat_chat)
test("glue: user emoji echo stripped", echoed == "seru!", f"got {echoed!r}")
own = strip_emojis_from_source("mantap \U0001F680", "halo \U0001F431")
test("glue: own emoji kept", own == "mantap \U0001F680", f"got {own!r}")
from utils.text import fix_orphan_punct, remove_pet_names
test("sanitizer: orphan comma before question mark fixed",
     fix_orphan_punct("mau aku bantu apa, ?") == "mau aku bantu apa?")
petted = "Sayang, kamu udah makan? Jangan lupa sayang!"
stripped = remove_pet_names(petted)
test("glue: pet names stripped for cross-turn damper",
     "sayang" not in stripped.lower() and "kamu udah makan? jangan lupa!" == stripped.lower(),
     f"got {stripped!r}")
mixed_en = "Belum nih sayang. I've heard it's really good! Have you seen it yet?"
test("sanitizer: english sentences dropped",
     _san(mixed_en) == "Belum nih sayang.", f"got {_san(mixed_en)!r}")
test("sanitizer: indonesian with loanword kept",
     _san("kamu nonton The Batman belum?") == "Kamu nonton The Batman belum?",
     f"got {_san('kamu nonton The Batman belum?')!r}")
night_glued = "\U0001F60Anight \U0001F303"
test("sanitizer: glued emoji separated",
     _san(night_glued) == "\U0001F60A night \U0001F303",
     f"got {_san(night_glued)!r}")

print("\n--- Orchestrator ---")
orch = Orchestrator()
orch.register_tool("calculator", CalculatorTool())
orch.register_tool("datetime", DateTimeTool())

r = orch.run_tool("calculator", "2 + 2")
test("calculator via orch", r.success and "4" in r.data.get("result", ""))

# ── 5. (OPTIONAL) LLM-DEPENDENT TESTS ─────────────────────────

print("\n--- LLM-dependent tests (model required) ---")
try:
    agent = VeilAgent(config.MODEL_PATH)
    orch = Orchestrator()
    orch.register_tool("web_search", WebSearchTool())
    orch.register_tool("calculator", CalculatorTool())
    orch.register_tool("datetime", DateTimeTool())
    core = PersonalityCore(agent, orch)

    t0 = time.time()
    r = core.handle("Halo")
    lat = time.time() - t0
    test("chat responds", len(r) > 0, f"response len: {len(r)}")
    print(f"  Latency: {lat:.2f}s  Preview: {r[:60]}...")

    r = ""
    for _ in range(3):  # tool path is deterministic; 7B sometimes ignores the
        r = core.handle("12 * 12")  # injected observation — allow e2e retries
        if "144" in r:
            break
    test("calculator via orch", "144" in r, f"got: {r[:80]}")

    gen = agent.chat_stream("Halo")
    first = next(gen, None)
    test("stream yields tokens", first is not None)
    for _ in gen:
        pass

except Exception as e:
    import traceback
    traceback.print_exc()
    test("LLM-dependent tests", False, f"Model error: {e}")

# ── SUMMARY ──────────────────────────────────────────────────

print(f"\n{'='*40}")
print(f"  PASSED: {passed}  FAILED: {failed}  TOTAL: {passed + failed}")
print(f"{'='*40}")
sys.exit(1 if failed else 0)
