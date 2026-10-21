"""Regression tests: benchmark run-summary record (AUDIT-006 follow-up).

`tools/bench.py --output PATH` writes a header, one record per prompt, and a
final `run` record. The run record is the only in-file signal of whether the
capture completed. It must never claim success for a partial run, and its
latency aggregates must describe exactly the records that exist.

SAFETY
  * No llama_cpp.Llama is constructed; the agent is a stub and PersonalityCore
    is never imported, so no GGUF is opened and no inference runs.
  * `bench._REPO_ROOT` is repointed at a throwaway sandbox carrying its own
    .gitignore, so nothing is written to the real repository's tmp/ or temp/.
  * Importing this module has no side effects; everything happens in main()
    and is undone in finally.

    python test_bench_run_summary_guard.py

Exit code 0 = all assertions passed, 1 = at least one failed.
"""
import builtins
import contextlib
import io
import json
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


class FakeOrch:
    tools = {}


def _sandbox_roots(root):
    with open(os.path.join(root, ".gitignore"), "w", encoding="utf-8") as fh:
        fh.write("tmp/\ntemp/\n")
    os.makedirs(os.path.join(root, "tmp"), exist_ok=True)
    for prot in ("logs", "data", "memory", "models"):
        os.makedirs(os.path.join(root, prot), exist_ok=True)


def _run_bench(bench, core, argv):
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


def _summaries(recs):
    return [r for r in recs if r.get("record") == "run"]


def main():
    del _PASS[:]
    del _FAIL[:]
    del _SKIPPED[:]

    orig_cwd = os.getcwd()
    sandbox = tempfile.mkdtemp(prefix="veil_summaryguard_")
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

        _PROMPTS = bench.PROMPTS
        _sandbox_roots(fake_root)
        bench._REPO_ROOT = fake_root
        responses = ["warmup"] + ["respons %d" % i for i in range(1, len(_PROMPTS) + 1)]

        # ------------------------------------------------ complete run
        print("\n--- complete run "
              "--------------------------------------------------")
        target = os.path.join("tmp", "done.jsonl")
        code, out, err = _run_bench(bench, FakeCore(responses),
                                    ["bench.py", "--output", target])
        path = os.path.join(fake_root, "tmp", "done.jsonl")
        recs = _read_jsonl(path)
        runs = _summaries(recs)
        check("complete: exit code 0", code == 0, code)
        check("complete: exactly one run record", len(runs) == 1, len(runs))
        check("complete: run record is the last line",
              recs[-1].get("record") == "run", recs[-1].get("record"))
        s = runs[0]
        check("complete: status is 'complete'", s.get("status") == "complete", s)
        check("complete: prompts_written == prompt_count == len(PROMPTS)",
              s.get("prompts_written") == s.get("prompt_count") == len(_PROMPTS), s)
        check("complete: error is null", s.get("error") is None, s.get("error"))
        check("complete: samples == 13", s.get("samples") == len(_PROMPTS), s.get("samples"))
        lat = s.get("latency_s", {})
        check("complete: latency values are numbers",
              all(isinstance(lat.get(k), (int, float)) for k in ("avg", "min", "max")), lat)
        check("complete: min <= avg <= max",
              lat.get("min") <= lat.get("avg") <= lat.get("max"), lat)
        check("complete: header still precedes responses",
              recs[0].get("record") == "header"
              and [r.get("i") for r in recs[1:-1]] == list(range(1, len(_PROMPTS) + 1)))
        check("complete: real repo tmp/ holds no guard-created file",
              not os.path.exists(os.path.join(real_repo_tmp, "closefail.jsonl")))

        # ------------------------------------------------ mid-run failure
        print("\n--- mid-run inference failure "
              "------------------------------------")
        partial = os.path.join("tmp", "partial.jsonl")
        code, _, err = _run_bench(bench, FakeCore(responses, fail_at=5),
                                  ["bench.py", "--output", partial])
        prec = _read_jsonl(os.path.join(fake_root, "tmp", "partial.jsonl"))
        ps = _summaries(prec)
        check("mid-run: exit code 5 preserved", code == 5, code)
        check("mid-run: one run record", len(ps) == 1, len(ps))
        check("mid-run: status is 'aborted'", ps[0].get("status") == "aborted", ps[0])
        check("mid-run: prompts_written == 4", ps[0].get("prompts_written") == 4, ps[0])
        check("mid-run: summary samples match written records",
              ps[0].get("samples") == 4, ps[0].get("samples"))
        check("mid-run: error names the cause",
              isinstance(ps[0].get("error"), str)
              and "RuntimeError" in ps[0]["error"]
              and "simulated mid-run failure" in ps[0]["error"], ps[0].get("error"))
        check("mid-run: 4 response records survive", len(prec) == 6, len(prec))

        # ------------------------------------------------ response-write failure
        print("\n--- response-write failure "
              "----------------------------------------")
        wf_name = os.path.join("tmp", "writefail.jsonl")
        wf_path = os.path.join(fake_root, "tmp", "writefail.jsonl")
        orig_emit = bench._emit

        def _boom_on_third_response(fh, record):
            if record.get("record") == "response" and record.get("i") == 3:
                raise OSError("simulated write failure")
            return orig_emit(fh, record)

        bench._emit = _boom_on_third_response
        try:
            code, _, err = _run_bench(bench, FakeCore(responses),
                                      ["bench.py", "--output", wf_name])
        finally:
            bench._emit = orig_emit
        wf = _read_jsonl(wf_path)
        ws = _summaries(wf)
        check("write-failure: exit code 4 preserved", code == 4, code)
        check("write-failure: status is 'aborted'", ws[0].get("status") == "aborted", ws[0])
        check("write-failure: prompts_written == 2", ws[0].get("prompts_written") == 2, ws[0])
        check("write-failure: summary samples == 2", ws[0].get("samples") == 2, ws[0])
        check("write-failure: error describes the write failure",
              "capture write failed" in (ws[0].get("error") or ""), ws[0].get("error"))

        # ------------------------------------------------ header-write failure
        print("\n--- header-write failure "
              "------------------------------------------")
        hf_name = os.path.join("tmp", "headerfail.jsonl")
        hf_path = os.path.join(fake_root, "tmp", "headerfail.jsonl")
        orig_emit2 = bench._emit

        def _header_boom(fh, record):
            if record.get("record") == "header":
                raise OSError("simulated header write failure")
            return orig_emit2(fh, record)

        bench._emit = _header_boom
        try:
            code, hout, herr = _run_bench(bench, FakeCore(responses),
                                          ["bench.py", "--output", hf_name])
        finally:
            bench._emit = orig_emit2
        check("header-failure: exit code 2 preserved", code == 2, code)
        check("header-failure: partial file removed, so no summary can exist",
              not os.path.exists(hf_path), hf_path)
        check("header-failure: success message suppressed",
              "**Capture:**" not in hout, hout[-200:])
        check("header-failure: _emit restored", bench._emit is orig_emit2)

        # ------------------------------------------------ close failure
        print("\n--- close failure must not claim complete "
              "-----------------------------")
        _real_open = builtins.open

        class _CloseFail:
            def __init__(self, fh):
                self._fh = fh

            def write(self, s):
                return self._fh.write(s)

            def flush(self):
                return self._fh.flush()

            def fileno(self):
                return self._fh.fileno()

            def close(self):
                self._fh.close()
                raise OSError("simulated close failure")

        def _wrap_open(suffix, factory):
            def guarded(path, *a, **k):
                fh = _real_open(path, *a, **k)
                if isinstance(path, str) and path.endswith(suffix):
                    return factory(fh)
                return fh
            return guarded

        builtins.open = _wrap_open("closefail.jsonl", _CloseFail)
        try:
            code, cout, cerr = _run_bench(
                bench, FakeCore(responses),
                ["bench.py", "--output", os.path.join("tmp", "closefail.jsonl")])
        finally:
            builtins.open = _real_open
        cf = _read_jsonl(os.path.join(fake_root, "tmp", "closefail.jsonl"))
        check("close-failure: exit code 6", code == 6, code)
        check("close-failure: NO run record in the artifact",
              all(r.get("record") != "run" for r in cf),
              [r.get("record") for r in cf])
        check("close-failure: header + all prompt records survive",
              len(cf) == len(_PROMPTS) + 1, len(cf))
        check("close-failure: finalize error reported",
              "finalize" in cerr and "simulated close failure" in cerr, cerr[-200:])
        check("close-failure: success banner suppressed",
              "**Capture:**" not in cout, cout[-160:])

        # ------------------------------------------------ finalize flush failure
        print("\n--- finalize flush failure must not claim complete "
              "------------------")
        _real_open2 = builtins.open

        class _FlushFailAt:
            def __init__(self, fh, fail_at):
                self._fh = fh
                self._n = 0
                self._fail_at = fail_at

            def write(self, s):
                return self._fh.write(s)

            def flush(self):
                self._n += 1
                if self._n >= self._fail_at:
                    raise OSError("simulated flush failure")
                return self._fh.flush()

            def fileno(self):
                return self._fh.fileno()

            def close(self):
                return self._fh.close()

        # 1 header + 13 response flushes precede the single finalize flush.
        builtins.open = _wrap_open("flushfail.jsonl",
                                   lambda fh: _FlushFailAt(fh, len(_PROMPTS) + 2))
        try:
            code, _, ferr = _run_bench(
                bench, FakeCore(responses),
                ["bench.py", "--output", os.path.join("tmp", "flushfail.jsonl")])
        finally:
            builtins.open = _real_open2
        ff = _read_jsonl(os.path.join(fake_root, "tmp", "flushfail.jsonl"))
        check("flush-failure: exit code 6", code == 6, code)
        check("flush-failure: NO run record in the artifact",
              all(r.get("record") != "run" for r in ff),
              [r.get("record") for r in ff])
        check("flush-failure: flush error reported", "flush" in ferr, ferr[-160:])

        # ------------------------------------------------ summary append failure
        print("\n--- summary append failure must not exit zero "
              "-----------------------")
        orig_append = bench._append_verified

        def _append_boom(path, identity, record):
            raise OSError("simulated summary append failure")

        bench._append_verified = _append_boom
        try:
            code, _, aerr = _run_bench(
                bench, FakeCore(responses),
                ["bench.py", "--output", os.path.join("tmp", "summaryfail.jsonl")])
        finally:
            bench._append_verified = orig_append
        af = _read_jsonl(os.path.join(fake_root, "tmp", "summaryfail.jsonl"))
        check("summary-append failure: exit code 6", code == 6, code)
        check("summary-append failure: NO run record in the artifact",
              all(r.get("record") != "run" for r in af),
              [r.get("record") for r in af])
        check("summary-append failure: error reported",
              "run summary" in aerr and "simulated summary append failure" in aerr,
              aerr[-200:])

        # ------------------------------------------------ verified append
        print("\n--- verified append refuses a changed target "
              "---------------------------")
        vp = os.path.join(fake_root, "tmp", "verify.jsonl")
        fh = open(vp, "x", encoding="utf-8", newline="\n")
        fh.write('{"record":"header"}\n')
        fh.flush()
        ident = bench._capture_identity(fh)
        fh.close()

        bench._append_verified(vp, ident, {"record": "run", "status": "complete"})
        vrecs = _read_jsonl(vp)
        check("append: verified target accepts the summary",
              vrecs[-1].get("record") == "run" and vrecs[-1].get("status") == "complete",
              vrecs[-1])

        fh = open(vp, "a", encoding="utf-8", newline="\n")
        fh.write('{"record":"header"}\n')
        fh.flush()
        ident2 = bench._capture_identity(fh)
        fh.close()
        with open(vp, "r+", encoding="utf-8") as g:
            g.truncate(4)
        refused = False
        try:
            bench._append_verified(vp, ident2, {"record": "run", "status": "complete"})
        except OSError:
            refused = True
        check("append: truncated target refused", refused)
        check("append: truncated target left untouched",
              os.path.getsize(vp) == 4, os.path.getsize(vp))

        rp = os.path.join(fake_root, "tmp", "replaced.jsonl")
        fh = open(rp, "x", encoding="utf-8", newline="\n")
        fh.write('{"record":"header"}\n')
        fh.flush()
        ident3 = bench._capture_identity(fh)
        fh.close()
        os.unlink(rp)
        with open(rp, "w", encoding="utf-8", newline="\n") as g:
            g.write("different\n")
        refused2 = False
        try:
            bench._append_verified(rp, ident3, {"record": "run", "status": "complete"})
        except OSError:
            refused2 = True
        check("append: replaced target refused", refused2)
        check("append: replaced target left untouched",
              open(rp, encoding="utf-8").read() == "different\n")

        # ------------------------------------------------ zero records
        print("\n--- zero successful records "
              "------------------------------------------")
        zero = os.path.join("tmp", "zero.jsonl")
        code, _, _ = _run_bench(bench, FakeCore(responses, fail_at=1),
                                ["bench.py", "--output", zero])
        zrecs = _read_jsonl(os.path.join(fake_root, "tmp", "zero.jsonl"))
        zs = _summaries(zrecs)
        check("zero: exit code 5 preserved", code == 5, code)
        check("zero: status is 'aborted'", zs[0].get("status") == "aborted", zs[0])
        check("zero: prompts_written == 0", zs[0].get("prompts_written") == 0, zs[0])
        check("zero: samples == 0", zs[0].get("samples") == 0, zs[0])
        check("zero: latency aggregates are null, not 0",
              all(zs[0]["latency_s"][k] is None for k in ("avg", "min", "max")),
              zs[0].get("latency_s"))
        check("zero: only header + run record", len(zrecs) == 2, len(zrecs))

        # ------------------------------------------------ default invocation
        print("\n--- default invocation writes no summary "
              "---------------------------")
        before = sorted(os.listdir(os.path.join(fake_root, "tmp")))
        code, out, _ = _run_bench(bench, FakeCore(responses), ["bench.py"])
        after = sorted(os.listdir(os.path.join(fake_root, "tmp")))
        check("default: exit code 0", code == 0, code)
        check("default: no file created", before == after, "%s -> %s" % (before, after))
        check("default: no capture banner", "**Capture:**" not in out, out[-120:])

        print("\n" + "=" * 62)
        print("RUN-SUMMARY-GUARD TESTS: %d/%d passed, %d skipped"
              % (len(_PASS), len(_PASS) + len(_FAIL), len(_SKIPPED)))
        for f in _FAIL:
            print("  FAILED: %s" % f)
        print("=" * 62)
    finally:
        os.chdir(orig_cwd)
        shutil.rmtree(sandbox, ignore_errors=True)
        if REPO in sys.path:
            sys.path.remove(REPO)
        sys.modules.pop("llama_cpp", None)

    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
