"""Regression tests: benchmark full-response capture (AUDIT-006, --output).

The runner used to keep only a character count and a 110-character preview
(tools/bench.py:105-106), so the complete response text was unrecoverable after
a run and no B-01..B-13 criterion could be scored. `--output PATH` writes one
UTF-8 JSONL record per prompt, holding the untruncated response.

SAFETY
  * These tests never construct a llama_cpp.Llama, so no GGUF is opened and no
    inference runs. The agent is a stub; PersonalityCore is never imported.
  * `bench._REPO_ROOT` is repointed at a throwaway sandbox that carries its own
    .gitignore listing tmp/ and temp/, so the destination validator runs against
    a fake tree. The real repository's tmp/ and temp/ are never created, and no
    file outside the sandbox is read or written.
  * Only the sandbox created here is removed. No user data is touched.

PYTEST SAFETY
  Importing this module has NO side effects: no chdir, no sys.path or
  sys.modules mutation, no sandbox directory, no application import. Every side
  effect lives inside main() and is undone in its finally block.

  This file contains no pytest test_* functions - it is an explicit runner:

      python test_bench_output_guard.py

  Exit code 0 = all assertions passed, 1 = at least one failed.
"""
import builtins
import contextlib
import io
import json
import logging
import os
import shutil
import sys
import tempfile
import types

REPO = r"C:\Users\Acer\Documents\Project\Github\Veil-Core-Project"

_PASS = []
_FAIL = []
_SKIPPED = []


def check(label, ok, detail=""):
    (_PASS if ok else _FAIL).append(label)
    print("  %s  %s%s" % ("PASS" if ok else "FAIL", label,
                          "" if ok else "   <- " + str(detail)))


def skip(label, why):
    _SKIPPED.append(label)
    print("  SKIP  %s   <- %s" % (label, why))


def _close_app_handlers():
    """Release files held by the app's RotatingFileHandler; on Windows an open
    file cannot be deleted, which would silently leak the sandbox."""
    for name in ("veil", "veil.personality", "veil.benchmark"):
        for handler in list(logging.getLogger(name).handlers):
            logging.getLogger(name).removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass


class FakeCore:
    """Stands in for PersonalityCore. Never touches the model."""

    def __init__(self, responses, fail_at=None):
        self.reactions_enabled = True
        self._responses = responses
        self._fail_at = fail_at
        self.calls = []

    def handle(self, prompt):
        if self._fail_at is not None and len(self.calls) >= self._fail_at:
            raise RuntimeError("simulated mid-run failure")
        self.calls.append(prompt)
        i = len(self.calls) - 1
        if i < len(self._responses):
            return self._responses[i]
        return "overflow-%d" % i


class FakeAgent:
    def generate(self, *a, **k):
        return "__LLM__"

    def stream(self, *a, **k):
        raise AssertionError("stream() not used")


class FakeOrch:
    tools = {}


def _payload(n):
    """One warmup response plus n prompt responses covering the edge cases:
    empty, very long, non-ASCII, emoji, control characters and quotes."""
    out = ["warmup response"]
    out.append("Halo! Aku di sini, apa kabar?")            # 1 plain
    out.append("")                                          # 2 EMPTY
    out.append("Panjang. " * 900)                           # 3 ~6.3k chars
    out.append("Halo éèü 你好 \U0001f680 — ❤️")              # 4 unicode + emoji
    out.append("kutip \" dan backslash \\ dan newline\n")     # 5 escaping
    out.append("   \t whitespace di luar   ")                 # 6 whitespace only
    for i in range(7, n + 1):
        out.append("respons nomor %d" % i)
    return out


def _sandbox_roots(root):
    """Give the fake tree its own .gitignore and the protected dirs the
    validator must refuse."""
    with open(os.path.join(root, ".gitignore"), "w", encoding="utf-8") as fh:
        fh.write("tmp/\ntemp/\n")
    os.makedirs(os.path.join(root, "tmp"), exist_ok=True)
    for prot in ("logs", "data", "memory", "models"):
        os.makedirs(os.path.join(root, prot), exist_ok=True)


def _run_bench(bench, core, argv):
    """Invoke bench.main() with a stubbed core.

    Returns (exit_code, stdout, stderr). Every module attribute the helper
    patches is saved first and restored in finally, so a failing run cannot leak
    stubs into later tests or into the real module."""
    saved = {
        "create_core_components": bench.create_core_components,
        "_working_set_bytes": bench._working_set_bytes,
        "_vram_used_mb": bench._vram_used_mb,
        "_REPO_ROOT": bench._REPO_ROOT,
        "argv": sys.argv[:],
    }
    bench.create_core_components = lambda: (FakeAgent(), FakeOrch(), core)
    bench._working_set_bytes = lambda: 0
    bench._vram_used_mb = lambda: 0
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    sys.argv = argv
    try:
        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
            try:
                bench.main()
                code = 0
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv = saved["argv"]
        bench._REPO_ROOT = saved["_REPO_ROOT"]
        bench.create_core_components = saved["create_core_components"]
        bench._working_set_bytes = saved["_working_set_bytes"]
        bench._vram_used_mb = saved["_vram_used_mb"]
    return code, out_buf.getvalue(), err_buf.getvalue()


def _read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main():
    del _PASS[:]
    del _FAIL[:]
    del _SKIPPED[:]

    orig_cwd = os.getcwd()
    sandbox = tempfile.mkdtemp(prefix="veil_outguard_")
    fake_root = os.path.join(sandbox, "repo")
    os.makedirs(fake_root, exist_ok=True)
    os.makedirs(os.path.join(sandbox, "data"), exist_ok=True)
    os.makedirs(os.path.join(sandbox, "memory"), exist_ok=True)
    os.makedirs(os.path.join(sandbox, "logs"), exist_ok=True)
    os.chdir(sandbox)

    real_repo_tmp = os.path.join(REPO, "tmp")

    try:
        llama_stub = types.ModuleType("llama_cpp")

        class _ForbiddenLlama:
            def __init__(self, *a, **k):
                raise AssertionError("GGUF load attempted")

        llama_stub.Llama = _ForbiddenLlama
        sys.modules["llama_cpp"] = llama_stub
        sys.path.insert(0, REPO)

        import tools.bench as bench                               # noqa: E402

        _REAL_CCC = bench.create_core_components
        _REAL_WSB = bench._working_set_bytes
        _REAL_VRAM = bench._vram_used_mb
        _PROMPTS = bench.PROMPTS
        _sandbox_roots(fake_root)
        bench._REPO_ROOT = fake_root
        check("fixture: sandbox .gitignore covers tmp/ and temp/",
              bench._gitignore_covers_dirname(os.path.join(fake_root, "tmp")))
        check("fixture: real repository tmp/ was not created",
              not os.path.exists(real_repo_tmp))

        responses = _payload(len(_PROMPTS))

        # ------------------------------------------------ default invocation
        print("\n--- default invocation writes nothing "
              "------------------------------")
        before = sorted(os.listdir(os.path.join(fake_root, "tmp")))
        code, out, _ = _run_bench(bench, FakeCore(responses), ["bench.py"])
        after = sorted(os.listdir(os.path.join(fake_root, "tmp")))
        check("default: exit code 0", code == 0, code)
        check("default: no file created in tmp/", before == after,
              "%s -> %s" % (before, after))
        check("default: stdout still reports all prompts",
              out.count("(casual)") + out.count("(") >= len(_PROMPTS), out[-200:])

        # ------------------------------------------------ happy path
        print("\n--- capture to tmp/ "
              "-----------------------------------------------")
        target = os.path.join("tmp", "capture.jsonl")
        code, out, _ = _run_bench(bench, FakeCore(responses),
                                  ["bench.py", "--output", target])
        path = os.path.join(fake_root, "tmp", "capture.jsonl")
        check("capture: exit code 0", code == 0, code)
        check("capture: file created", os.path.isfile(path), path)
        recs = _read_jsonl(path)
        check("capture: record count == len(PROMPTS) + 1",
              len(recs) == len(_PROMPTS) + 1, len(recs))

        header, bodies = recs[0], recs[1:]
        for field in ("record", "version", "format", "generated_at",
                      "model_file", "n_ctx", "sampling", "max_tokens",
                      "prompt_char_limit", "preview_chars", "prompt_count"):
            check("header: has %s" % field, field in header, sorted(header))
        check("header: prompt_count matches PROMPTS",
              header.get("prompt_count") == len(_PROMPTS))
        check("header: model_file is a bare filename (no user path)",
              header.get("model_file") == os.path.basename(header.get("model_file", "")))
        blob = json.dumps(header)
        # Narrow, literal-token check only: it proves these exact strings are
        # absent, NOT that the header is free of every secret. It deliberately
        # does not read or print .env. The header intentionally keeps non-secret
        # sampling metadata (including the effective temperature) because it is
        # needed to interpret the run and the unresolved D-2 decision.
        check("header: omits literal '.env'/'VEIL_TEMP'/'long_term'/'state.json' tokens",
              ".env" not in blob and "VEIL_TEMP" not in blob
              and "long_term" not in blob and "state.json" not in blob, blob[:160])
        check("header: sampling keeps the effective temperature for provenance",
              header.get("sampling", {}).get("temperature") is not None,
              header.get("sampling"))

        check("bodies: prompt/category/order match PROMPTS exactly",
              [(b["category"], b["prompt"]) for b in bodies] == list(_PROMPTS),
              [(b["category"], b["prompt"]) for b in bodies[:3]])
        check("bodies: index i runs 1..N",
              [b["i"] for b in bodies] == list(range(1, len(_PROMPTS) + 1)))

        check("bodies: every chars == len(response)",
              all(len(b["response"]) == b["chars"] for b in bodies))
        check("bodies: every response round-trips exactly against the stub",
              [b["response"] for b in bodies] == responses[1:],
              "first mismatch at %s" % next(
                  (i for i, (x, y) in enumerate(
                      zip([b["response"] for b in bodies], responses[1:])
                  ) if x != y), None))
        check("bodies: empty response recorded with chars 0",
              bodies[1]["chars"] == 0 and bodies[1]["response"] == "",
              bodies[1]["chars"])
        check("bodies: long response preserved in full",
              len(bodies[2]["response"]) > 5000, len(bodies[2]["response"]))
        check("bodies: unicode and control chars survive round-trip",
              bodies[3]["response"] == responses[4]
              and bodies[5]["response"] == responses[6],
              repr(bodies[3]["response"][:20]))
        check("stdout: full response text is NOT echoed",
              all(r not in out for r in responses if len(r) > 40 and r.strip()),
              "a long response appeared on stdout")

        # ------------------------------------------------ overwrite refusal
        print("\n--- existing destination "
              "--------------------------------------")
        with open(path, "rb") as fh:
            original = fh.read()
        code, _, _ = _run_bench(bench, FakeCore(responses),
                                ["bench.py", "--output", target])
        with open(path, "rb") as fh:
            after_bytes = fh.read()
        check("overwrite: exit code non-zero", code != 0, code)
        check("overwrite: existing contents untouched", original == after_bytes)

        # ------------------------------------------------ rejected paths
        print("\n--- rejected destinations "
              "-------------------------------------")
        rejected = [
            ("logs/", "logs/evil.jsonl"),
            ("data/", "data/evil.jsonl"),
            ("memory/", "memory/evil.jsonl"),
            ("models/", "models/evil.jsonl"),
            ("repo root", "evil.jsonl"),
            ("traversal into logs", "tmp/../logs/evil.jsonl"),
            ("absolute outside repo", os.path.join(sandbox, "evil.jsonl")),
            ("temp/ is approved", "temp/ok.jsonl"),
            ("nested subdir refused", "tmp/sub/deep.jsonl"),
            ("empty string", ""),
        ]
        for label, arg in rejected:
            code, _, _ = _run_bench(bench, FakeCore(responses),
                                    ["bench.py", "--output", arg])
            expect_ok = label == "temp/ is approved"
            if expect_ok:
                check("reject(%s): accepted" % label, code == 0, code)
            else:
                check("reject(%s): exit non-zero" % label, code != 0, code)
        for prot in ("logs", "data", "memory"):
            check("reject: nothing written into %s/" % prot,
                  os.listdir(os.path.join(fake_root, prot)) == [],
                  os.listdir(os.path.join(fake_root, prot)))
        check("reject: nested subdir destination left no directory behind",
              not os.path.exists(os.path.join(fake_root, "tmp", "sub")),
              os.path.join(fake_root, "tmp", "sub"))

        # ------------------------------------------------ symlink escape
        print("\n--- symlink escape "
              "--------------------------------------------")
        link = os.path.join(fake_root, "tmp", "link-out")
        try:
            os.symlink(os.path.join(fake_root, "logs"), link, target_is_directory=True)
        except (OSError, NotImplementedError, AttributeError) as exc:
            skip("symlink: destination symlink refused",
                 "symlink creation not permitted here (%s)" % type(exc).__name__)
        else:
            code, _, _ = _run_bench(bench, FakeCore(responses),
                                    ["bench.py", "--output", "tmp/link-out/evil.jsonl"])
            check("symlink: escape via directory symlink refused", code != 0, code)
            check("symlink: nothing reached logs/", os.listdir(
                os.path.join(fake_root, "logs")) == [])
            file_link = os.path.join(fake_root, "tmp", "evil-link.jsonl")
            try:
                os.symlink(os.path.join(fake_root, "logs", "x.jsonl"), file_link)
            except (OSError, NotImplementedError) as exc:
                skip("symlink: file symlink refused",
                     "file symlink not permitted (%s)" % type(exc).__name__)
            else:
                code, _, _ = _run_bench(bench, FakeCore(responses),
                                        ["bench.py", "--output", "tmp/evil-link.jsonl"])
                check("symlink: destination symlink refused", code != 0, code)
            os.unlink(link)

        # The OS-level symlink cases above are skipped when the platform forbids
        # creating symlinks. These two exercise the same rejection branches by
        # faking os.path.islink, so the defence is still covered deterministically.
        real_islink = os.path.islink
        try:
            def fake_islink(path, _roots=(os.path.join(fake_root, "tmp"),
                                          os.path.join(fake_root, "tmp", "evil-link.jsonl"))):
                target = os.path.normcase(os.path.normpath(str(path)))
                return any(target == os.path.normcase(os.path.normpath(r))
                           for r in _roots)

            os.path.islink = fake_islink
            code, _, _ = _run_bench(bench, FakeCore(responses),
                                    ["bench.py", "--output", "tmp/evil-link.jsonl"])
            check("symlink(faked): destination symlink refused", code != 0, code)
            check("symlink(faked): symlinked tmp/ root is disqualified from the approved list",
                  "tmp" not in [n for n, _ in bench._approved_output_roots()],
                  bench._approved_output_roots())
            code, _, _ = _run_bench(bench, FakeCore(responses),
                                    ["bench.py", "--output", "tmp/anything.jsonl"])
            check("symlink(faked): no approved root means refusal, not a write",
                  code != 0, code)
            check("symlink(faked): nothing leaked into logs/", os.listdir(
                os.path.join(fake_root, "logs")) == [])
        finally:
            os.path.islink = real_islink
        check("symlink: os.path.islink restored", os.path.islink is real_islink)

        # ------------------------------------------------ mid-run failure
        print("\n--- mid-run failure "
              "-------------------------------------------")
        partial = os.path.join("tmp", "partial.jsonl")
        code, _, _ = _run_bench(bench, FakeCore(responses, fail_at=5),
                                ["bench.py", "--output", partial])
        ppath = os.path.join(fake_root, "tmp", "partial.jsonl")
        check("mid-run: exit code non-zero", code != 0, code)
        check("mid-run: partial file exists", os.path.isfile(ppath))
        prec = _read_jsonl(ppath)
        check("mid-run: header plus 4 complete records (failed on the 5th)",
              len(prec) == 5, len(prec))
        check("mid-run: every surviving line is valid JSON with full response",
              all("response" in r or r.get("record") == "header" for r in prec)
              and all(len(r["response"]) == r["chars"] for r in prec[1:]))
        check("mid-run: real repo tmp/ still absent",
              not os.path.exists(real_repo_tmp))

        # ------------------------------------------------ header write failure
        print("\n--- header write failure (L-2) "
              "----------------------------------")
        hf_name = os.path.join("tmp", "headerfail.jsonl")
        hf_path = os.path.join(fake_root, "tmp", "headerfail.jsonl")
        orig_emit = bench._emit

        def _header_boom(fh, record):
            if record.get("record") == "header":
                raise OSError("simulated header write failure")
            return orig_emit(fh, record)

        bench._emit = _header_boom
        try:
            code, hout, herr = _run_bench(
                bench, FakeCore(responses), ["bench.py", "--output", hf_name])
        finally:
            bench._emit = orig_emit
        check("header-failure: exit code non-zero", code != 0, code)
        check("header-failure: newly created partial file removed",
              not os.path.exists(hf_path), hf_path)
        check("header-failure: original error reported on stderr",
              "header" in herr, herr[:200])
        check("header-failure: success message suppressed",
              "**Capture:**" not in hout, hout[-200:])
        check("header-failure: _emit restored", bench._emit is orig_emit)

        # ------------------------------------------------ close failure (H-1)
        print("\n--- close failure must not report success (H-1) "
              "--------------")
        _real_open = builtins.open

        class _CloseFail:
            """Delegates write/flush to the real file but fails on close."""

            def __init__(self, fh):
                self._fh = fh

            def write(self, s):
                return self._fh.write(s)

            def flush(self):
                return self._fh.flush()

            def close(self):
                self._fh.close()
                raise OSError("simulated close failure")

        def _run_with_close_failure(core, argv, suffix):
            def guarded(path, *a, **k):
                fh = _real_open(path, *a, **k)
                if isinstance(path, str) and path.endswith(suffix):
                    return _CloseFail(fh)
                return fh

            builtins.open = guarded
            try:
                return _run_bench(bench, core, argv)
            finally:
                builtins.open = _real_open

        cf_name = os.path.join("tmp", "closefail.jsonl")
        cf_path = os.path.join(fake_root, "tmp", "closefail.jsonl")
        code, cout, cerr = _run_with_close_failure(
            FakeCore(responses), ["bench.py", "--output", cf_name], "closefail.jsonl")
        check("close-failure: exit code non-zero", code != 0, code)
        check("close-failure: dedicated finalize exit code (6)", code == 6, code)
        check("close-failure: file exists with the written data",
              os.path.isfile(cf_path))
        check("close-failure: records fully written before close",
              len(_read_jsonl(cf_path)) == len(_PROMPTS) + 1)
        check("close-failure: close error reported on stderr",
              "finalize" in cerr and "simulated close failure" in cerr, cerr[-200:])
        check("close-failure: success message suppressed",
              "**Capture:**" not in cout, cout[-200:])

        cf2_name = os.path.join("tmp", "closefail2.jsonl")
        code, cout2, cerr2 = _run_with_close_failure(
            FakeCore(responses, fail_at=5),
            ["bench.py", "--output", cf2_name], "closefail2.jsonl")
        check("close-failure-after-error: primary exit code preserved (5)",
              code == 5, code)
        check("close-failure-after-error: primary error still reported",
              "run aborted" in cerr2, cerr2[-200:])
        check("close-failure-after-error: cleanup failure also reported",
              "finalize" in cerr2, cerr2[-200:])
        check("close-failure-after-error: success message suppressed",
              "**Capture:**" not in cout2, cout2[-200:])

        # ------------------------------------------------ default exception (M-1)
        print("\n--- default path: core exception stays uncaught (M-1) "
              "---------")
        raised = None
        try:
            _run_bench(bench, FakeCore(responses, fail_at=5), ["bench.py"])
        except BaseException as exc:            # noqa: BLE001 - assert type
            raised = exc
        check("default exception: original RuntimeError propagates (not exit 5)",
              isinstance(raised, RuntimeError),
              type(raised).__name__ if raised is not None else "no exception")
        check("default exception: not converted into SystemExit",
              not isinstance(raised, SystemExit),
              type(raised).__name__ if raised is not None else "no exception")
        check("default exception: stubs restored after the failure",
              bench.create_core_components is _REAL_CCC
              and bench._working_set_bytes is _REAL_WSB
              and bench._vram_used_mb is _REAL_VRAM)

        # ------------------------------------------------ restoration (L-5)
        print("\n--- monkeypatch restoration (L-5) "
              "------------------------------------")
        check("restore: create_core_components is the real function",
              bench.create_core_components is _REAL_CCC)
        check("restore: _working_set_bytes is the real function",
              bench._working_set_bytes is _REAL_WSB)
        check("restore: _vram_used_mb is the real function",
              bench._vram_used_mb is _REAL_VRAM)
        check("restore: _REPO_ROOT back to the sandbox root",
              bench._REPO_ROOT == fake_root, bench._REPO_ROOT)
        check("restore: builtins.open is the real open",
              builtins.open is _real_open)

        # ------------------------------------------------ pre-open re-check (M-2)
        print("\n--- pre-open containment re-check (M-2) "
              "----------------------------")
        good = os.path.join(fake_root, "tmp", "recheck.jsonl")
        good_root = os.path.join(fake_root, "tmp")
        passed = True
        try:
            bench._recheck_output_target(good, good_root)
        except bench.OutputPathError:
            passed = False
        check("recheck: unchanged target passes", passed)
        refused = False
        try:
            bench._recheck_output_target(good, os.path.join(fake_root, "elsewhere"))
        except bench.OutputPathError:
            refused = True
        check("recheck: root that changed since validation is refused", refused)
        real_islink3 = os.path.islink
        try:
            os.path.islink = lambda p: str(p) == good
            refused_link = False
            try:
                bench._recheck_output_target(good, good_root)
            except bench.OutputPathError:
                refused_link = True
            check("recheck: symlinked target is refused", refused_link)
        finally:
            os.path.islink = real_islink3
        check("recheck: os.path.islink restored after M-2 probes",
              os.path.islink is real_islink3)

        print("\n" + "=" * 62)
        print("OUTPUT-GUARD TESTS: %d/%d passed, %d skipped"
              % (len(_PASS), len(_PASS) + len(_FAIL), len(_SKIPPED)))
        for f in _FAIL:
            print("  FAILED: %s" % f)
        for s in _SKIPPED:
            print("  SKIPPED: %s" % s)
        print("=" * 62)
    finally:
        os.chdir(orig_cwd)
        _close_app_handlers()
        shutil.rmtree(sandbox, ignore_errors=True)
        if REPO in sys.path:
            sys.path.remove(REPO)
        sys.modules.pop("llama_cpp", None)

    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())