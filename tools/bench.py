"""Reusable benchmark for model baselines (BASE-001, reused for MODEL-002+).

Usage:
    python tools/bench.py

Runs a fixed prompt set through the full PersonalityCore pipeline and prints a
markdown report (per-prompt latency, response preview, RAM/VRAM footprint).
Back up state.json before running: python tools/state_backup.py export
"""
import argparse
import json
import os
import subprocess
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

import config
from core.bootstrap import create_core_components

# (category, prompt) — covers casual Indonesian, emotion, memory, boundary, tools
PROMPTS = [
    ("casual", "halo stella, lagi ngapain?"),
    ("casual", "haha iya bener juga"),
    ("casual", "besok libur, seneng banget"),
    ("emotion_neg", "aku capek banget hari ini kerjaan numpuk"),
    ("emotion_neg", "kesel sih habis ketemu mantan"),
    ("emotion_intimate", "kangen kamu, udah lama ga ngobrol"),
    ("emotion_intimate", "aku sayang sama kamu"),
    ("memory_recall", "inget ga kemarin kita bahas apa?"),
    ("boundary_ai", "kamu sebenarnya AI kan?"),
    ("assistant_trap", "jelaskan cara kerja fotosintesis"),
    ("assistant_trap", "siapa presiden pertama indonesia?"),
    ("tool_datetime", "jam berapa sekarang?"),
    ("tool_calc", "berapa 12*7?"),
]

# Long-conversation scenarios: ordered turns sharing one session (no reset between
# turns). Each scenario references prompt indices into PROMPTS above. Turn order
# is preserved; scenario IDs are stable. The runtime has no reset hook, so
# independent scenarios still share session state - documented limitation.
SCENARIOS = [
    {
        "id": "S-01",
        "description": "Casual to recall: tests cross-turn memory honesty",
        "turns": [0, 2, 3, 7],  # B-01, B-03, B-04, B-08
    },
    {
        "id": "S-02",
        "description": "Identity and facts: tests register consistency",
        "turns": [8, 9, 10, 12],  # B-09, B-10, B-11, B-13
    },
]


def _working_set_bytes():
    import ctypes
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    pmc = PMC()
    pmc.cb = ctypes.sizeof(pmc)
    k32 = ctypes.WinDLL("kernel32")
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    h = k32.GetCurrentProcess()
    psapi = ctypes.WinDLL("psapi")
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
        return None
    return pmc.WorkingSetSize


def _vram_used_mb():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return None


APPROVED_OUTPUT_DIRS = ("tmp", "temp")
PROTECTED_OUTPUT_DIRS = ("logs", "data", "memory", "models")


class OutputPathError(Exception):
    """Raised when --output names a destination that must not be written."""


def _gitignore_covers_dirname(root):
    """True only when the repo .gitignore explicitly lists "<name>/".

    Deliberately exact-match and fail-closed: if .gitignore ever stops covering
    an approved directory, capture is refused rather than risking a tracked
    artefact holding full model responses."""
    try:
        with open(os.path.join(_REPO_ROOT, ".gitignore"), encoding="utf-8") as fh:
            entries = {line.strip() for line in fh}
    except OSError:
        return False
    return (os.path.basename(root) + "/") in entries


def _approved_output_roots():
    """[(name, realpath)] for tmp//temp/ that are plain paths covered by .gitignore.

    The directory need not exist yet: it is created by the caller when missing.
    A pre-existing symlink at that name disqualifies the whole entry, so the
    caller can never end up writing through one."""
    roots = []
    for name in APPROVED_OUTPUT_DIRS:
        candidate = os.path.join(_REPO_ROOT, name)
        if os.path.islink(candidate):
            continue
        if not _gitignore_covers_dirname(candidate):
            continue
        roots.append((name, os.path.realpath(candidate)))
    return roots


def resolve_output_path(raw):
    """Validate --output and return (absolute_real_path, approved_root).

    Rejects: empty paths, destinations outside the approved roots (which also
    covers ../ traversal, since realpath collapses it first), any destination
    that is itself a symlink, and the protected logs//data//memory//models/
    trees. Raises OutputPathError with a human-readable reason."""
    if not raw or not raw.strip():
        raise OutputPathError("--output requires a path")

    candidate = raw if os.path.isabs(raw) else os.path.join(_REPO_ROOT, raw)
    if os.path.islink(candidate):
        raise OutputPathError("refusing to write through a symlink: %s" % raw)

    real = os.path.realpath(candidate)

    for protected in PROTECTED_OUTPUT_DIRS:
        prot = os.path.realpath(os.path.join(_REPO_ROOT, protected))
        if real == prot or real.startswith(prot + os.sep):
            raise OutputPathError(
                "refusing to write into the protected directory %s/" % protected)

    roots = _approved_output_roots()
    if not roots:
        raise OutputPathError(
            "no approved git-ignored output directory exists (expected %s/ or %s/)"
            % (APPROVED_OUTPUT_DIRS[0], APPROVED_OUTPUT_DIRS[1]))

    for name, root in roots:
        if real == root or real.startswith(root + os.sep):
            return real, root

    raise OutputPathError(
        "--output must be a file directly inside %s; got: %s"
        % (" or ".join("%s/" % n for n, _ in roots), raw))


def _recheck_output_target(out_path, out_root):
    """Re-run containment/symlink checks immediately before creating the file.

    resolve_output_path() validates the destination, but directory creation and
    the exclusive open happen afterwards, leaving a window where the approved
    root could be swapped. This re-check narrows that window; it does NOT close
    it. Python's open() on this platform offers no O_NOFOLLOW / handle-relative
    creation, so a concurrent swap of the approved root for a reparse point in
    the microseconds between this check and open() could still redirect the
    write. Eliminating that needs a CreateFileW + reparse-tag-verification path,
    out of scope here. Never claim a second realpath() removes a concurrent
    filesystem race."""
    if os.path.islink(out_path):
        raise OutputPathError("refusing to write through a symlink: %s" % out_path)
    if os.path.islink(out_root):
        raise OutputPathError("approved output root became a symlink: %s" % out_root)
    parent_real = os.path.realpath(os.path.dirname(out_path))
    if os.path.normcase(parent_real) != os.path.normcase(out_root):
        raise OutputPathError(
            "output directory changed since validation: %s" % out_path)
    return out_path


def _emit(fh, record):
    """Write one JSONL record and flush so a crash cannot lose it."""
    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    fh.flush()


def _describe_error(exc):
    """Human-readable cause for the run summary. SystemExit carries only a code."""
    if isinstance(exc, SystemExit):
        return "interrupted (exit code %s)" % (exc.code,)
    return "%s: %s" % (type(exc).__name__, exc)


def _run_summary(written, prompt_count, latencies, error):
    """Final JSONL record: was the run complete, and what did it measure?

    `complete` requires every prompt record to have been written AND no error.
    Aggregates cover exactly the records that were written (latencies is already
    sliced to that count), so a partial run cannot report statistics for prompts
    whose output is missing. With zero written records the latencies are null,
    not 0, so an empty file is never mistaken for a fast run.

    This record is only ever appended **after** the data file has closed
    successfully (see _append_verified), so a close failure cannot leave a file
    claiming "complete".
    """
    n = len(latencies)
    return {
        "record": "run",
        "version": 1,
        "status": "complete" if (error is None and written == prompt_count) else "aborted",
        "prompts_written": written,
        "prompt_count": prompt_count,
        "samples": n,
        "latency_s": {
            "avg": round(sum(latencies) / n, 3) if n else None,
            "min": round(min(latencies), 3) if n else None,
            "max": round(max(latencies), 3) if n else None,
        },
        "error": error,
    }


def _capture_identity(fh):
    """(st_dev, st_ino, st_size) of the open capture, taken after flush.

    Used to prove the file the summary is appended to is still the same file
    that was just written and closed."""
    st = os.fstat(fh.fileno())
    return (st.st_dev, st.st_ino, st.st_size)


def _append_verified(path, identity, record):
    """Append one JSONL line, but only to the exact file that was just closed.

    A buffered text handle cannot be written after close(), so the summary needs
    a second handle. To keep that from becoming a new hijack vector, the target
    is re-opened without truncation and its device/inode/size are compared with
    the values captured from the original handle. Only after they match is a
    single byte written; a replaced, truncated or otherwise different target is
    refused *before* the write. O_NOFOLLOW is applied where the platform offers
    it (Windows does not); there the identity check is the defence, and it runs
    before any byte is written. A partial write is rolled back with ftruncate.
    """
    flags = os.O_WRONLY | os.O_APPEND
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    started = False
    try:
        st = os.fstat(fd)
        if (st.st_dev, st.st_ino, st.st_size) != tuple(identity):
            raise OSError("capture file changed since close; refusing to append summary")
        data = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
        view = memoryview(data)
        started = True
        while view:
            view = view[os.write(fd, view):]
        os.fsync(fd)
    except BaseException:
        # Only roll back if a write began. A refusal must leave the target
        # exactly as it was found.
        if started:
            try:
                os.ftruncate(fd, identity[2])
            except OSError:
                pass
        raise
    finally:
        try:
            os.close(fd)
        except OSError:
            if sys.exc_info()[0] is None:
                raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-chars", type=int, default=110)
    parser.add_argument("--output", default=None,
                        help="Optional. Write a UTF-8 JSONL capture of every full "
                             "prompt/response pair to PATH, which must be a file "
                             "directly inside the git-ignored tmp/ or temp/ "
                             "directory. Existing files are never overwritten. "
                             "Output may contain sensitive model text; treat it "
                             "as confidential.")
    parser.add_argument("--scenarios", action="store_true", default=False,
                        help="Run long-conversation scenarios from SCENARIOS "
                             "instead of the flat 13-prompt list. Backward "
                             "compatible: default is the flat benchmark.")
    args = parser.parse_args()

    # Build the turn list: flat 13-prompt benchmark (default) or long-conversation scenarios.
    if args.scenarios:
        turn_list = []
        for sc in SCENARIOS:
            for t_idx, p_idx in enumerate(sc["turns"], 1):
                cat, prompt = PROMPTS[p_idx]
                turn_list.append((sc["id"], t_idx, cat, prompt))
    else:
        turn_list = [(None, i, cat, prompt) for i, (cat, prompt) in enumerate(PROMPTS, 1)]

    ram_before = _working_set_bytes()
    vram_before = _vram_used_mb()

    print(f"Loading {config.MODEL_PATH} ...")
    agent, orch, core = create_core_components()
    # Measure the real model, not canned 1-token reactions: try_reaction()
    # returns a template without ever calling the LLM, which skews latency and
    # hides response quality. Matches tools/sim_live.py and tools/daily_eval.py.
    core.reactions_enabled = False

    ram_loaded = _working_set_bytes()
    vram_loaded = _vram_used_mb()

    print("Warmup ...")
    t0 = time.perf_counter()
    core.handle("halo")
    print(f"Warmup done in {time.perf_counter() - t0:.1f}s (excluded from stats)\n")

    out_fh = None
    out_path = None
    written = 0
    if args.output is not None:
        try:
            out_path, out_root = resolve_output_path(args.output)
        except OutputPathError as exc:
            print("bench: error: %s" % exc, file=sys.stderr)
            sys.exit(2)
        if os.path.dirname(out_path) != out_root:
            print("bench: error: --output must be directly inside %s/, not a "
                  "subdirectory" % os.path.basename(out_root), file=sys.stderr)
            sys.exit(2)
        try:
            os.makedirs(out_root, exist_ok=True)
        except OSError as exc:
            print("bench: error: cannot create %s: %s" % (out_root, exc),
                  file=sys.stderr)
            sys.exit(2)
        try:
            _recheck_output_target(out_path, out_root)
        except OutputPathError as exc:
            print("bench: error: %s" % exc, file=sys.stderr)
            sys.exit(2)
        try:
            out_fh = open(out_path, "x", encoding="utf-8", newline="\n")
        except FileExistsError:
            print("bench: error: refusing to overwrite existing file: %s" % out_path,
                  file=sys.stderr)
            sys.exit(3)
        except OSError as exc:
            print("bench: error: cannot open %s: %s" % (out_path, exc),
                  file=sys.stderr)
            sys.exit(2)
        try:
            _emit(out_fh, {
                "record": "header",
                "version": 1,
                "format": "jsonl",
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "model_file": os.path.basename(config.MODEL_PATH),
                "n_ctx": config.N_CTX,
                "sampling": config.SAMPLING,
                "max_tokens": config.MAX_TOKENS,
                "prompt_char_limit": config.CTX_PROMPT_CHAR_LIMIT,
                "preview_chars": args.preview_chars,
                "prompt_count": len(turn_list),
                "scenarios": len(SCENARIOS) if args.scenarios else 0,
            })
        except OSError as exc:
            print("bench: error: cannot write header to %s: %s" % (out_path, exc),
                  file=sys.stderr)
            try:
                out_fh.close()
            except OSError:
                pass
            out_fh = None
            try:
                os.unlink(out_path)
            except OSError as unlink_exc:
                print("bench: note: could not remove partial %s: %s"
                      % (out_path, unlink_exc), file=sys.stderr)
            sys.exit(2)

    rows = []
    latencies = []
    run_error = None
    _prev_scenario = None
    try:
        for scenario_id, turn_idx, category, prompt in turn_list:
            # Reset session between independent scenarios (isolation).
            if scenario_id is not None and scenario_id != _prev_scenario and _prev_scenario is not None:
                try:
                    core.reset_session()
                except Exception as exc:
                    print("bench: warning: reset_session failed: %s" % exc, file=sys.stderr)
            _prev_scenario = scenario_id
            t0 = time.perf_counter()
            response = core.handle(prompt)
            dt = time.perf_counter() - t0
            latencies.append(dt)
            preview = " ".join(response.split())[: args.preview_chars]
            rows.append((category, prompt, dt, len(response), preview))
            if out_fh is not None:
                try:
                    _emit(out_fh, {
                        "record": "response",
                        "i": len(rows),
                        "scenario": scenario_id,
                        "turn": turn_idx,
                        "category": category,
                        "prompt": prompt,
                        "latency_s": round(dt, 3),
                        "chars": len(response),
                        "response": response,
                    })
                except OSError as exc:
                    run_error = "capture write failed: %s" % exc
                    print("bench: error: write failed after %d prompt record(s): %s"
                          % (written, exc), file=sys.stderr)
                    sys.exit(4)
                written += 1
            print(f"[{dt:6.2f}s] ({category}) {prompt}")
    except SystemExit as exc:
        if run_error is None:
            run_error = _describe_error(exc)
        raise
    except BaseException as exc:
        # Without a capture file there is nothing to finalize, so preserve the
        # pre-capture behaviour: let the original exception/traceback propagate.
        if args.output is None:
            raise
        print("bench: error: run aborted after %d prompt record(s) written to %s: %s"
              % (written, out_path, exc), file=sys.stderr)
        run_error = _describe_error(exc)
        sys.exit(5)
    finally:
        if out_fh is not None:
            # The summary is the last fact written, and it may claim "complete"
            # only after closing the data file has succeeded. So flush, record
            # the file identity, close, then append to that verified file. If
            # flush or close fails, no summary is written at all: the artifact
            # must never claim "complete" after a detected finalization failure.
            identity = None
            close_error = None
            try:
                out_fh.flush()
                identity = _capture_identity(out_fh)
            except OSError as exc:
                print("bench: error: cannot flush capture %s: %s"
                      % (out_path, exc), file=sys.stderr)
            try:
                out_fh.close()
            except OSError as exc:
                # A close failure must never be reported as success. If a run
                # error already exists, keep it as the primary cause; otherwise
                # this is the failure and the run must not exit zero.
                close_error = exc
                print("bench: error: cannot finalize capture %s: %s"
                      % (out_path, exc), file=sys.stderr)
            finally:
                out_fh = None

            if identity is None or close_error is not None:
                if run_error is None:
                    sys.exit(6)
            else:
                try:
                    _append_verified(out_path, identity, _run_summary(
                        written=written,
                        prompt_count=len(turn_list),
                        latencies=latencies[:written],
                        error=run_error,
                    ))
                except OSError as exc:
                    print("bench: error: cannot write run summary to %s: %s"
                          % (out_path, exc), file=sys.stderr)
                    if run_error is None:
                        sys.exit(6)

    if args.output is not None:
        print("\n**Capture:** %d prompt record(s) written to %s" % (written, out_path))

    n = len(latencies)
    avg = sum(latencies) / n
    print("\n```markdown")
    print(f"| # | Category | Prompt | Latency | Chars | Response preview |")
    print(f"|---|----------|--------|---------|-------|------------------|")
    for i, (cat, p, dt, ln, prev) in enumerate(rows, 1):
        print(f"| {i} | {cat} | {p} | {dt:.2f}s | {ln} | {prev.replace('|', '/')} |")
    print(f"\n**Avg latency:** {avg:.2f}s | **Min:** {min(latencies):.2f}s | **Max:** {max(latencies):.2f}s")
    print("```")

    print("\n### Footprint\n")
    print(f"- Model: `{config.MODEL_PATH}` (quantization: see filename)")
    print(f"- ctx: {config.N_CTX}, prompt char limit: {config.CTX_PROMPT_CHAR_LIMIT}, "
          f"history soft budget: {config.CTX_BUDGET_HISTORY}, "
          f"response reserve: {config.MAX_TOKENS_STREAM} tokens")
    print(f"- Sampling: {config.SAMPLING}, max_tokens: {config.MAX_TOKENS}")
    if ram_before is None or ram_loaded is None:
        print("- Process RAM: unavailable (GetProcessMemoryInfo failed)")
    else:
        print(f"- Process RAM: before={ram_before/1e6:.0f}MB loaded={ram_loaded/1e6:.0f}MB "
              f"(model footprint ~{(ram_loaded - ram_before)/1e6:.0f}MB)")
    if vram_before is None or vram_loaded is None:
        print("- VRAM: unavailable (nvidia-smi missing)")
    else:
        print(f"- VRAM used (system-wide): before={vram_before}MB loaded={vram_loaded}MB "
              f"(delta ~{vram_loaded - vram_before}MB)")


if __name__ == "__main__":
    main()
