"""Regression tests: benchmark must never return a canned reaction (Phase C1).

Incident (Phase B, 2026-10-15): benchmark prompt #5 returned "hmm iya juga"
in 0.02s. That string is REACTION_TEMPLATES["pensive"][2] in personality/rhythm.py,
returned by try_reaction() -> PersonalityCore.handle() BEFORE the LLM is ever
called. Latency and response-quality numbers from that run are untrustworthy.

Root cause: tools/bench.py never set core.reactions_enabled = False, although
tools/sim_live.py:40 and tools/daily_eval.py:285 both already did.

SAFETY
  * Runs from a throwaway CWD. config.LOG_DIR ("logs"),
    config.LONG_TERM_MEMORY_PATH ("memory/long_term.json") and
    personality.persistence.DEFAULT_PATH ("data/state.json") are all RELATIVE,
    so chdir() before importing redirects every write away from the repo.
  * llama_cpp is replaced in sys.modules before any import that reaches it,
    so no GGUF is opened and no native library is loaded. A real
    llama_cpp.Llama(...) call raises immediately.
  * Only the LLM boundary is stubbed (the agent). PersonalityCore.handle(),
    try_reaction(), analyze(), build_prompt() are the REAL production code.

PYTEST SAFETY
  Importing this module has NO side effects: no chdir, no sys.path or
  sys.modules mutation, no sandbox directory, no application import. Every
  side effect lives inside main() and is undone in its finally block, so
  pytest collection of this file runs nothing and pollutes nothing.

  This file therefore contains no pytest test_* functions - it is an explicit
  runner, invoked directly:

      python test_bench_reaction_guard.py

  Exit code 0 = all assertions passed, 1 = at least one failed.
"""
import contextlib
import io
import logging
import os
import shutil
import sys
import tempfile
import types

REPO = r"C:\Users\Acer\Documents\Project\Github\Veil-Core-Project"

PENSIVE_PROMPT = "kesel sih habis ketemu mantan"
PENSIVE_TEMPLATE = "hmm iya juga"
LLM_SENTINEL = "__REACHED_THE_LLM__"

# Populated only while main() runs. Importing the module leaves these empty.
_PASS = []
_FAIL = []


def check(label, ok, detail=""):
    (_PASS if ok else _FAIL).append(label)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", label,
                          "" if ok else "   <- " + str(detail)))


class ForcedRNG:
    """Deterministic rng: always take the probability gate, always pick
    "pensive", always pick the "hmm iya juga" template."""

    def random(self):
        return 0.0                       # 0.0 < any prob (prob floor is 0.05)

    def choice(self, seq):
        seq = list(seq)
        if "pensive" in seq:
            return "pensive"
        if PENSIVE_TEMPLATE in seq:
            return PENSIVE_TEMPLATE
        return seq[0]


class StubAgent:
    """Stands in for VeilAgent at the LLM boundary. Records every call."""

    def __init__(self):
        self.calls = []

    def generate(self, system, user_input, observation="", **kw):
        self.calls.append(user_input)
        return LLM_SENTINEL

    def stream(self, *a, **k):
        raise AssertionError("stream() not used by handle()")


class StubOrch:
    tools: dict = {}


class RecordingCore:
    def __init__(self):
        self.reactions_enabled = True     # starts ENABLED, like the real object
        self.handled = []
        self.flags_at_call = []            # flag value seen by each handle()

    def handle(self, prompt):
        self.handled.append(prompt)
        self.flags_at_call.append(self.reactions_enabled)
        return "resp-" + str(len(self.handled))


def _close_app_handlers():
    """Close logging handlers the application opened on files inside the
    sandbox. utils.logger installs a RotatingFileHandler on logs/veil.log and
    keeps it for the process lifetime; on Windows an open file cannot be
    deleted, so shutil.rmtree would silently fail and leak the sandbox. Test
    local only - no production code is modified."""
    for name in ("veil", "veil.personality", "veil.benchmark"):
        for handler in list(logging.getLogger(name).handlers):
            logging.getLogger(name).removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass


def main():
    """Run every assertion inside a throwaway sandbox. All side effects -
    chdir, sys.path, sys.modules, the sandbox directory itself - are created
    here and undone in the finally block."""
    del _PASS[:]
    del _FAIL[:]

    orig_cwd = os.getcwd()
    sandbox = tempfile.mkdtemp(prefix="veil_reactguard_")
    for _sub in ("data", "memory", "logs"):
        os.makedirs(os.path.join(sandbox, _sub), exist_ok=True)

    # Import-time redirection of every relative path. MUST happen before imports.
    os.chdir(sandbox)

    try:
        # Block the real llama_cpp before anything imports it.
        llama_stub = types.ModuleType("llama_cpp")

        class _ForbiddenLlama:
            def __init__(self, *a, **k):
                raise AssertionError(
                    "GGUF load attempted - test must never reach the model")

        llama_stub.Llama = _ForbiddenLlama
        sys.modules["llama_cpp"] = llama_stub
        sys.path.insert(0, REPO)

        import tools.bench as bench                                     # noqa: E402
        from personality.core import PersonalityCore                    # noqa: E402
        from personality.analyzer import analyze                       # noqa: E402
        from personality.rhythm import (                               # noqa: E402
            try_reaction, REACTION_TEMPLATES)
        from personality.state import StellaState                       # noqa: E402
        import personality.core as _pcore                               # noqa: E402

        def build_real_core():
            """A REAL PersonalityCore - only the LLM is stubbed."""
            agent = StubAgent()
            return PersonalityCore(agent, StubOrch(), cognition_tools={}), agent

        print("\n--- fixture validation "
              "-----------------------------------------")

        # If this fails, every guard test below is vacuous. It proves the prompt
        # really does reach the pensive branch of the REAL analyzer and REAL
        # try_reaction.
        _an = analyze(PENSIVE_PROMPT)
        check("fixture: prompt hits pensive branch (v<-0.3, a>0.5)",
              _an.valence < -0.3 and _an.arousal > 0.5,
              "valence=%s arousal=%s" % (_an.valence, _an.arousal))
        check("fixture: canned string is a real pensive template",
              PENSIVE_TEMPLATE in REACTION_TEMPLATES["pensive"],
              REACTION_TEMPLATES.get("pensive"))
        check("fixture: ForcedRNG alone can produce the canned string",
              try_reaction(StellaState(), _an, 0.0, ForcedRNG(),
                           now=10 ** 9).text == PENSIVE_TEMPLATE)

        print("\n--- ordinary interactive path (guard absent) "
              "--------------------")

        _core_i, _agent_i = build_real_core()
        _saved_rng = _pcore._random
        _pcore._random = ForcedRNG()
        try:
            _out_interactive = _core_i.handle(PENSIVE_PROMPT)
        finally:
            _pcore._random = _saved_rng

        check("interactive: canned reaction IS still returned "
              "(behaviour unchanged)",
              _out_interactive == PENSIVE_TEMPLATE, repr(_out_interactive))
        check("interactive: LLM was NOT called (proves the shortcut is real)",
              _agent_i.calls == [], _agent_i.calls)

        print("\n--- evaluation path (guard active) "
              "-----------------------------------")

        _core_e, _agent_e = build_real_core()
        _core_e.reactions_enabled = False          # exactly what bench.py does
        _pcore._random = ForcedRNG()
        try:
            _out_eval = _core_e.handle(PENSIVE_PROMPT)
        finally:
            _pcore._random = _saved_rng

        check("evaluation: canned reaction is NOT returned",
              _out_eval != PENSIVE_TEMPLATE, repr(_out_eval))
        check("evaluation: response comes from the LLM boundary",
              _out_eval == LLM_SENTINEL, repr(_out_eval))
        check("evaluation: agent.generate() was actually invoked",
              _agent_e.calls == [PENSIVE_PROMPT], _agent_e.calls)

        print("\n--- guard is discriminating (would fail if removed) "
              "-------------------")

        _core_t, _agent_t = build_real_core()
        _core_t.reactions_enabled = True           # guard neutralised
        _pcore._random = ForcedRNG()
        try:
            _out_true = _core_t.handle(PENSIVE_PROMPT)
        finally:
            _pcore._random = _saved_rng
        check("regression guard: flag=True restores the shortcut",
              _out_true == PENSIVE_TEMPLATE and _agent_t.calls == [],
              "%r %s" % (_out_true, _agent_t.calls))

        # Same for the default: production reads it via
        # getattr(self, "reactions_enabled", True), so a fresh core must leave
        # the flag unset. The BEHAVIOUR of that default is already proven by the
        # "interactive" block above, which uses a fresh core and gets the canned
        # reaction back with no LLM call - so this only pins the attribute state.
        _core_d, _agent_d = build_real_core()
        check("regression guard: unset attribute defaults to enabled",
              not hasattr(_core_d, "reactions_enabled"))

        print("\n--- bench.main() wiring "
              "----------------------------------------------")

        _rec = RecordingCore()
        _fac = bench.create_core_components
        _bw = bench._working_set_bytes
        _bv = bench._vram_used_mb
        bench.create_core_components = lambda: (object(), object(), _rec)
        bench._working_set_bytes = lambda: 0
        bench._vram_used_mb = lambda: 0
        _saved_argv = sys.argv[:]
        sys.argv = ["bench.py"]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                bench.main()
        finally:
            sys.argv = _saved_argv
            bench.create_core_components = _fac
            bench._working_set_bytes = _bw
            bench._vram_used_mb = _bv

        check("bench.main(): disables reactions",
              _rec.reactions_enabled is False, _rec.reactions_enabled)
        check("bench.main(): reached handle() for warmup + all prompts",
              len(_rec.handled) == len(bench.PROMPTS) + 1,
              "%d calls for %d prompts" % (len(_rec.handled), len(bench.PROMPTS)))
        check("bench.main(): disabled BEFORE the first handle() call",
              bool(_rec.flags_at_call) and _rec.flags_at_call[0] is False,
              _rec.flags_at_call[:3])

        print("\n--- benchmark corpus actually contains the trigger "
              "--------------------")

        check("bench.PROMPTS includes the pensive-trigger prompt",
              any(p == PENSIVE_PROMPT for _, p in bench.PROMPTS),
              [p for _, p in bench.PROMPTS])
        _triggers = [p for _, p in bench.PROMPTS
                     if (a := analyze(p)).valence < -0.3 and a.arousal > 0.5]
        check("every pensive-trigger prompt in the corpus is now covered "
              "by the guard", _triggers == [PENSIVE_PROMPT], _triggers)

        print("\n" + "=" * 62)
        print("REACTION-GUARD TESTS: %d/%d passed"
              % (len(_PASS), len(_PASS) + len(_FAIL)))
        for f in _FAIL:
            print("  FAILED: %s" % f)
        print("=" * 62)
    finally:
        # Always restore the process, even if an assertion raised.
        os.chdir(orig_cwd)
        _close_app_handlers()   # release logs/veil.log before deleting
        shutil.rmtree(sandbox, ignore_errors=True)
        if REPO in sys.path:
            sys.path.remove(REPO)
        sys.modules.pop("llama_cpp", None)

    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())