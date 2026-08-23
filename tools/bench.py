"""Reusable benchmark for model baselines (BASE-001, reused for MODEL-002+).

Usage:
    python tools/bench.py

Runs a fixed prompt set through the full PersonalityCore pipeline and prints a
markdown report (per-prompt latency, response preview, RAM/VRAM footprint).
Back up state.json before running: python tools/state_backup.py export
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-chars", type=int, default=110)
    args = parser.parse_args()

    ram_before = _working_set_bytes()
    vram_before = _vram_used_mb()

    print(f"Loading {config.MODEL_PATH} ...")
    agent, orch, core = create_core_components()

    ram_loaded = _working_set_bytes()
    vram_loaded = _vram_used_mb()

    print("Warmup ...")
    t0 = time.perf_counter()
    core.handle("halo")
    print(f"Warmup done in {time.perf_counter() - t0:.1f}s (excluded from stats)\n")

    rows = []
    latencies = []
    for category, prompt in PROMPTS:
        t0 = time.perf_counter()
        response = core.handle(prompt)
        dt = time.perf_counter() - t0
        latencies.append(dt)
        preview = " ".join(response.split())[: args.preview_chars]
        rows.append((category, prompt, dt, len(response), preview))
        print(f"[{dt:6.2f}s] ({category}) {prompt}")

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
    print(f"- ctx: {config.N_CTX}, budgets sys/hist/resp: "
          f"{config.CTX_BUDGET_SYSTEM}/{config.CTX_BUDGET_HISTORY}/{config.CTX_BUDGET_RESPONSE}")
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
