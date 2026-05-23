import sys
import time
import config
from core.agent import VeilAgent
from core.orchestrator import Orchestrator
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

ltm.remember("pribadi", "nama panggilan saya Rei")
data3 = ltm.store.get("facts", [])
test("new fact stored", any("Rei" in f["content"] for f in data3))
for f in data3:
    if "Rei" in f["content"]:
        test("importance 3 for personal facts", f.get("importance") == 3, f"got {f.get('importance')}")

# Cleanup test file
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

# ── 4. ORCHESTRATOR INTENT TESTS ─────────────────────────────

print("\n--- Intent Detection ---")
orch_no_model = Orchestrator(agent=None)
test("detects calculator",  orch_no_model.detect_intent("hitung 2+2") == "calculator")
test("detects datetime",    orch_no_model.detect_intent("jam berapa") == "datetime")
test("detects web search",  orch_no_model.detect_intent("cari berita") == "web_search")
test("detects memory write",orch_no_model.detect_intent("ingat kalau aku suka kopi") == "memory_write")
test("chat fallback",       orch_no_model.detect_intent("apa kabar") == "chat")
test("no false positive: berapa kabar", orch_no_model.detect_intent("berapa kabar") == "chat")
test("no false positive: berapa lama",  orch_no_model.detect_intent("berapa lama") != "calculator")

# ── 5. (OPTIONAL) LLM-DEPENDENT TESTS ─────────────────────────

print("\n--- LLM-dependent tests (model required) ---")
try:
    agent = VeilAgent(config.MODEL_PATH)
    orch = Orchestrator(agent)
    orch.register_tool("web_search", WebSearchTool())
    orch.register_tool("calculator", CalculatorTool())
    orch.register_tool("datetime", DateTimeTool())

    t0 = time.time()
    r = orch.handle("Halo")
    lat = time.time() - t0
    test("chat responds", len(r) > 0, f"response len: {len(r)}")
    print(f"  Latency: {lat:.2f}s  Preview: {r[:60]}...")

    r = orch.handle("calculate 12 * 12")
    test("calculator via orch", "144" in r, f"got: {r}")

    # Streaming structural check
    gen = agent.chat_stream("Halo")
    first = next(gen, None)
    test("stream yields tokens", first is not None)
    for _ in gen:
        pass

except Exception as e:
    test("LLM-dependent tests", False, f"Model error: {e}")

# ── SUMMARY ──────────────────────────────────────────────────

print(f"\n{'='*40}")
print(f"  PASSED: {passed}  FAILED: {failed}  TOTAL: {passed + failed}")
print(f"{'='*40}")
sys.exit(1 if failed else 0)
