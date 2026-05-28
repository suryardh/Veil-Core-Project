import sys
import time
import config
from core.agent import VeilAgent
from core.orchestrator import Orchestrator
from personality.core import PersonalityCore
from personality.analyzer import analyze
from personality.state import StellaState
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
ltm = LongTermMemory(filepath="logs/test_long_term.json")
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

import os
os.remove("logs/test_long_term.json")

# ── 3. SHORT-TERM MEMORY OVERFLOW TESTS ──────────────────────

print("\n--- Short-Term Memory Overflow ---")
stm = ShortTermMemory(limit=8)
for i in range(20):
    stm.add_message("user", f"pesan ke-{i}")
    stm.add_message("assistant", f"respon ke-{i}")
ctx = stm.get_context()
test("context not empty", len(ctx) > 0)
test("context respects budget", len(ctx) <= 4000, f"got {len(ctx)} chars")

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

print("\n--- State Management ---")
s = StellaState()
test("default stage kenalan", s.stage_label() == "kenalan")
test("default mood neutral", s.dominant_mood() == "neutral")

s.update_from_interaction("positive", 0.8, 0.9)
test("affection increased", s.affection > 0)

s.update_from_interaction("negative", 0.9, 0.9)
test("trust decreased", s.trust < 0.33)

s.decay()
test("decay reduces affection", s.affection <= 0.04)

s2 = StellaState()
s2.update_from_interaction("intimate", 1.0, 0.95)
test("intimate boosts stage", s2.stage_label() != "kenalan")

print("\n--- Emotional Memory ---")
em = EmotionalMemory(filepath="logs/test_emotional.json")
em.record("interaction", "halo", 0.1, 0.1)
test("salience filter", len(em.records) == 0)

em.record("interaction", "aku sayang kamu", 0.8, 0.8)
test("record stored", len(em.records) == 1)

em.record("interaction", "aku sayang kamu", 0.8, 0.8)
test("recurrence merged", len(em.records) == 1 and em.records[0]["recurrence"] == 2)

summary = em.emotional_summary()
test("summary is string", isinstance(summary, str))
em.clear()
os.remove("logs/test_emotional.json")

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

    r = core.handle("12 * 12")
    test("calculator via orch", "144" in r, f"got: {r}")

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
