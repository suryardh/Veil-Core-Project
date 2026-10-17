"""Regression tests: memory extraction and recall integrity (Phase C2).

Defect 1 - memory/extractor.py matched a bare "inget"/"ingat" prefix, so an
ordinary RECALL question ("inget ga kemarin kita bahas apa?") was classified as
an explicit save command. Its remainder was stripped, capitalized and written
into long-term memory as a "fact about the user".

Defect 2 - personality/core.py persisted the extracted fact BEFORE calling
get_relevant_facts(), so the current message was fed back into its own prompt
as an already-established prior fact.

SAFETY
  * Runs from a throwaway CWD. config.LONG_TERM_MEMORY_PATH
    ("memory/long_term.json") and personality.persistence.DEFAULT_PATH
    ("data/state.json") are RELATIVE, so chdir() before importing redirects
    every write away from the repository.
  * llama_cpp is BLOCKED before anything imports it: the stub module exposes a
    _ForbiddenLlama whose __init__ raises AssertionError, so the suite can never
    reach a real GGUF model load. No model is required at any stage, and this
    file reads or sets no environment variable.

PYTEST SAFETY
  Importing this module has NO side effects: no chdir, no sys.path or
  sys.modules mutation, no sandbox directory, no application import, and no
  reads of production memory files. Every side effect lives inside main() and
  is undone in its finally block, so pytest collection runs nothing and
  pollutes nothing.

  This file therefore contains no pytest test_* functions - it is an explicit
  runner, invoked directly:

      python test_memory_extraction_guard.py

  Exit code 0 = all assertions passed, 1 = at least one failed.
"""
import hashlib
import logging
import os
import shutil
import sys
import tempfile
import types

REPO = r"C:\Users\Acer\Documents\Project\Github\Veil-Core-Project"

REPRO = "inget ga kemarin kita bahas apa?"

# Populated only while main() runs. Importing the module leaves these empty.
_PASS = []
_FAIL = []


def check(label, ok, detail=""):
    (_PASS if ok else _FAIL).append(label)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", label,
                          "" if ok else "   <- " + str(detail)))


def _digest(path):
    """Read-only sha256 of a file. Used to assert production memory is
    untouched; never writes."""
    if not os.path.exists(path):
        return "ABSENT"
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class _StubAgent:
    def __init__(self):
        self.systems = []

    def generate(self, system, user_input, observation="", **kw):
        self.systems.append(system)
        return "__LLM__"

    def stream(self, *a, **k):
        raise AssertionError("unused")


class _StubOrch:
    tools: dict = {}


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
    """Run every assertion inside a throwaway sandbox. All side effects --
    chdir, sys.path, sys.modules, the sandbox directory itself -- are created
    here and undone in the finally block."""
    del _PASS[:]
    del _FAIL[:]

    prod_memory = os.path.join(REPO, "memory", "long_term.json")
    prod_state = os.path.join(REPO, "data", "state.json")
    prod_log = os.path.join(REPO, "logs", "veil.log")
    snapshot = {p: _digest(p) for p in (prod_memory, prod_state, prod_log)}

    orig_cwd = os.getcwd()
    sandbox = tempfile.mkdtemp(prefix="veil_memguard_")
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

        from memory.extractor import extract_fact, strip_framing    # noqa: E402
        from memory.long_term import LongTermMemory                # noqa: E402
        from personality.core import PersonalityCore               # noqa: E402

        def fresh_core(memfile="memory/lt3.json"):
            agent = _StubAgent()
            core = PersonalityCore(agent, _StubOrch(), cognition_tools={})
            core.long_memory = LongTermMemory(memfile)  # isolated fixture store
            return core, agent

        print("\n--- 1. exact reproduction (defect 1) "
              "-------------------------------")
        _r = extract_fact(REPRO)
        check("recall question is NOT seeded", _r["seeded"] is False, _r)
        check("recall question content is not corrupted",
              _r["content"] == REPRO, _r["content"])
        check("recall question is not stored as a fact",
              not LongTermMemory("memory/lt1.json").store.get("facts"),
              "store not empty")

        print("\n--- 2. explicit save instructions still work "
              "------------------------")
        _s = extract_fact("inget ya, aku ulang tahun bulan depan. jangan lupa")
        check("explicit save is seeded", _s["seeded"] is True, _s)
        check("explicit save content stripped correctly",
              _s["content"] == "Aku ulang tahun bulan depan.", _s["content"])
        _s2 = extract_fact("ingat ya, nama saya Rei")
        check("'ingat ya,' save still seeded", _s2["seeded"] is True, _s2)
        check("'ingat ya,' content correct",
              _s2["content"] == "Nama saya Rei", _s2["content"])
        _s3 = extract_fact("remember that my dog is Milo")
        check("english 'remember that' still seeded", _s3["seeded"] is True, _s3)
        check("english 'remember that' content correct",
              _s3["content"] == "My dog is Milo", _s3["content"])

        print("\n--- 3. ordinary sentences containing 'inget' are not saves "
              "----------")
        for txt in ("kamu inget BPD atau nggak?", "halo stella, lagi ngapain?",
                    "eh, kapan ulang tahun aku?", "aku inget banget hari itu"):
            _o = extract_fact(txt)
            check("not seeded: %r" % txt, _o["seeded"] is False, _o)
        check("'remember what we discussed yesterday?' rejected (english question)",
              extract_fact("remember what we discussed yesterday?")["seeded"] is False)
        check("'apakah kamu ingat nama saya?' rejected",
              extract_fact("apakah kamu ingat nama saya?")["seeded"] is False)

        print("\n--- 4. degenerate / invalid extraction rejected "
              "---------------------")
        for txt in ("inget ya,", "ingat ya.", "remember"):
            _d = extract_fact(txt)
            check("degenerate rejected: %r" % txt, _d["seeded"] is False, _d)
        _ltm0 = LongTermMemory("memory/lt2.json")
        for txt in ("inget ya,", "ingat ya."):
            _d = extract_fact(txt)
            if _d["seeded"]:
                _ltm0.remember(_d["type"], _d["content"], _d["importance"])
        check("no garbage fact persisted from degenerate frames",
              not _ltm0.store.get("facts"), _ltm0.store.get("facts"))

        print("\n--- 5. recall cannot retrieve its own current-turn question "
              "---------")

        core_a, agent_a = fresh_core()
        core_a.handle(REPRO)
        core_a.handle("inget ya, favoritku kopi")
        _injected = "\n".join(agent_a.systems)
        check("current-turn question never appears as a user fact",
              REPRO not in _injected and "Ga kemarin" not in _injected)
        check("same-turn save not injected back into its own prompt",
              "Favoritku kopi" not in agent_a.systems[-1],
              agent_a.systems[-1][-200:])
        check("but the save WAS persisted",
              bool(core_a.long_memory.store.get("facts")),
              core_a.long_memory.store.get("facts"))

        print("\n--- 6. recall from an empty store invents nothing "
              "------------------")
        core_e, agent_e = fresh_core("memory/lt4.json")
        core_e.handle("apa favoritku?")
        _empty_facts = agent_e.systems[-1]
        check("empty store: no 'User facts' block",
              "User facts" not in _empty_facts, _empty_facts[-200:])

        print("\n--- 7. positive recall with a deliberately seeded fact "
              "------------")
        core_p, agent_p = fresh_core("memory/lt5.json")
        core_p.long_memory.remember("preference", "Favoritku kopi")
        core_p.handle("apa favoritku?")
        _recalled = agent_p.systems[-1]
        check("positive recall: seeded fact reaches the prompt",
              "Favoritku kopi" in _recalled, _recalled[-200:])
        check("positive recall: appears under the User facts heading",
              "User facts" in _recalled, _recalled[-200:])
        check("positive recall: direct API agrees",
              "Favoritku kopi" in LongTermMemory("memory/lt5.json")
              .get_relevant_facts("apa favoritku"))

        print("\n--- 8. duplicate-save semantics unchanged "
              "---------------------------")
        _dup = LongTermMemory("memory/lt6.json")
        _dup.remember("preference", "Favoritku kopi")
        _dup.remember("preference", "Favoritku kopi")
        check("exact duplicate is not stored twice",
              len(_dup.store.get("facts")) == 1, _dup.store.get("facts"))
        _dup.remember("preference", "favoritku KOPI")
        check("duplicate is case-insensitive (pre-existing semantics)",
              len(_dup.store.get("facts")) == 1, _dup.store.get("facts"))

        print("\n--- 9. strip_framing no longer eats question text "
              "------------------")
        # The defect was strip_framing REMOVING the "inget " prefix. Capitalising
        # the first letter is pre-existing normalisation for stored facts
        # (extractor.py lines 51-52) and is not part of this defect.
        _sf = strip_framing(REPRO)
        check("strip_framing keeps the whole question (frame not stripped)",
              _sf.lower() == REPRO.lower(), _sf)
        check("strip_framing still removed nothing else",
              _sf.lower().endswith("ga kemarin kita bahas apa?"), _sf)

        print("\n--- 10. production memory untouched by this test run "
              "--------------")
        for _p in (prod_memory, prod_state, prod_log):
            check("unchanged: %s" % os.path.relpath(_p, REPO),
                  _digest(_p) == snapshot[_p])

        print("\n" + "=" * 62)
        print("MEMORY-EXTRACTION TESTS: %d/%d passed"
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