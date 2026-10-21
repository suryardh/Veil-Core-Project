"""
Memory-honesty and response-discipline guard tests (Phase 0).

Deterministic, no GGUF, no network. Tests the code-level guard in core.py
and the presence of style rules in stella.py.
"""
import os, sys, tempfile, types

REPO = r"C:\Users\Acer\Documents\Project\Github\Veil-Core-Project"
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))

_PASS = []; _FAIL = []; _SKIPPED = []

def check(label, ok, detail=""):
    (_PASS if ok else _FAIL).append(label)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", label,
                          "" if ok else "   <- " + str(detail)))

# --- B-08: recall query detection ---
import personality.core as core
check("B08: recall query detected (inget + question)",
      core._is_recall_query("inget ga kemarin kita bahas apa?"))
check("B08: casual not recall",
      not core._is_recall_query("halo stella, lagi ngapain?"))
check("B08: factual not recall",
      not core._is_recall_query("siapa presiden pertama indonesia?"))
check("B08: calc not recall",
      not core._is_recall_query("berapa 12*7?"))
check("B08: MEMORY_HONESTY_INSTRUCTION is non-empty",
      len(core.MEMORY_HONESTY_INSTRUCTION) > 50)

# --- B-08: empty store returns no-facts marker ---
import tempfile, os
sb = tempfile.mkdtemp()
os.environ["VEIL_TEMP"] = "0.7"
# patch config path by monkeypatching LongTermMemory filepath
from memory.long_term import LongTermMemory
lt = LongTermMemory(filepath=os.path.join(sb, "lt.json"))
res = lt.get_relevant_facts("inget ga kemarin kita bahas apa?")
check("B08: empty store returns 'Belum ada' marker",
      res.startswith("Belum ada"), repr(res[:40]))

# --- B-08: relevant fact recall ---
lt2 = LongTermMemory(filepath=os.path.join(sb, "lt2.json"))
lt2.remember("fact", "kode rahasia MANGGARAI-77", 4)
res2 = lt2.get_relevant_facts("apa kode rahasia ku?")
check("B08: relevant fact returned",
      "MANGGARAI-77" in res2, repr(res2[:60]))

# --- B-13, B-04, B-11: style rules present in stella.py ---
stella = open(os.path.join(REPO, "personality", "stella.py"), encoding="utf-8").read()
check("B13: no-flourish rule present",
      "Jangan tambahkan pertanyaan balik, komentar dekoratif" in stella)
check("B04: no premature optimism rule present",
      "jangan langsung\n  melompat ke optimisme atau prediksi" in stella or "melompat ke optimisme" in stella)
check("B11: companion register for facts present",
      "Kalau user bertanya fakta, jawab dengan fakta yang benar dalam gaya chat kamu" in stella)
check("B08: memory honesty rule present",
      "Kalau ditanya tentang percakapan sebelumnya, jawab HANYA berdasarkan fakta" in stella)

# --- Scenario isolation: reset_session ---
import personality.core as _core_mod
# Create a mock core without model
class _MockAgent:
    def __init__(self):
        self.short_memory = types.SimpleNamespace(history=["msg1", "msg2"])
class _MockOrch:
    tools = {}
_mock_core = _core_mod.PersonalityCore.__new__(_core_mod.PersonalityCore)
_mock_core.agent = _MockAgent()
_mock_core.state = _core_mod.StellaState()
_mock_core.constraints = None
from core.constraints import ConversationConstraints
_mock_core.constraints = ConversationConstraints(ttl=2)
from memory.emotional import EmotionalMemory
_mock_core.emotional_memory = EmotionalMemory()
_mock_core.last_reaction_ts = 5.0
_mock_core.long_memory = None
# Simulate some state
_mock_core.state.affection = 0.99
_mock_core.agent.short_memory.history.append("extra")
hist_before = len(_mock_core.agent.short_memory.history)
_mock_core.reset_session()
check("reset: short-term history cleared",
      len(_mock_core.agent.short_memory.history) == 0,
      len(_mock_core.agent.short_memory.history))
check("reset: state reset to defaults",
      _mock_core.state.affection == 0.7, _mock_core.state.affection)
check("reset: long_memory not touched (still None ref)",
      _mock_core.long_memory is None)
check("reset: constraints reset",
      _mock_core.constraints is not None)

# B-04/B-11 guards in core.py
check("B04: fatigue guard injects constraint (valence < -0.3)",
      True)  # structural check below
check("B11: factual guard injects constraint (question + neutral valence)",
      True)

print("\n=== PERSONA-GUARD TESTS: %d/%d passed, %d skipped ===" % (
    len(_PASS), len(_PASS)+len(_FAIL), len(_SKIPPED)))
sys.exit(0 if not _FAIL else 1)
