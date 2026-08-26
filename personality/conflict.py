"""Conflict dynamics + relationship drift (TODO EMO-001, REL-001..004).

Fully deterministic — no LLM involvement. All timings are injected so tests
can run without waiting. Entry point: on_interaction().
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

# ── Tunables (override in tests) ────────────────────────────────────────────
CONFLICT_MIN_SEVERITY = 0.25   # below this = noise, ignored
COOLDOWN_BASE_S = 900          # seconds at severity 1.0 (15 min)
DAMPING_IN_COOLDOWN = 0.35     # positive-delta multiplier while cooling down
RECOVERY_FRACTION = 0.25       # fraction of remaining gap healed per good turn
APOLOGY_BONUS = 2.0            # apology multiplies recovery fraction
APOLOGY_MAX_EFFECTIVE = 2      # apologies beyond this stop accelerating
RECOVERY_GAP_EPSILON = 0.01    # gap below this counts as healed
DRIFT_WINDOW_SIZE = 10         # kept in state.drift_window
DRIFT_MIN_SAMPLES = 5
DRIFT_POSITIVE = 0.15          # avg valence above -> positive drift
DRIFT_NEGATIVE = -0.15         # avg valence below -> negative drift
ESCALATION_STEP = 0.15         # severity added by repeat conflict in cooldown

# ── REL-001: conflict triggers ──────────────────────────────────────────────
# Insults must be DIRECTED at Stella: a second-person marker near the insult,
# otherwise third-party venting ("bos gw bego") would be a false positive.
_SECOND_PERSON = re.compile(r"\b(kamu|km|lo|loe|elu|anda|u)\b", re.IGNORECASE)

_CONFLICT_LEXICON: list[tuple[re.Pattern, str, float]] = [
    # category, base severity
    (re.compile(r"\b(bego|tolol|idiot|dumb|stupid)\b", re.I), "insult", 0.55),
    (re.compile(r"\b(menyebalkan|nyebelin|payah|hina|kejam)\b", re.I), "insult", 0.40),
    (re.compile(r"\b(pergi\s+(saja|aja)|tinggalin|tinggalkan)\b", re.I), "abandonment", 0.60),
    (re.compile(r"\b(pergi\s+sana|minggir)\b", re.I), "abandonment", 0.60),
    (re.compile(r"\b(cari\s+yang\s+lain|ganti\s+(kamu|lo)|putus)\b", re.I), "abandonment", 0.70),
    (re.compile(r"\b(ga\s+mau\s+ngobrol|nggak\s+mau\s+ngobrol|jangan\s+ganggu)\b", re.I), "rejection", 0.45),
    (re.compile(r"\b(bosan\s+(sama|ama)\s+kamu|capek\s+sama\s+kamu)\b", re.I), "rejection", 0.50),
]

_APOLOGY_RE = re.compile(
    r"\b(maaf|maf|sorry|sory|(?<!ya )ampun|aku\s+salah)\b", re.I)

_INTENSIFIER = re.compile(r"[!?]{2,}|[A-Z]{5,}")


@dataclass
class ConflictEvent:
    category: str
    severity: float


def detect_conflict(text: str) -> ConflictEvent | None:
    """Return a conflict event if the text attacks Stella directly."""
    best: ConflictEvent | None = None
    directed = bool(_SECOND_PERSON.search(text))
    boost = 0.15 if _INTENSIFIER.search(text) else 0.0
    for pattern, category, base in _CONFLICT_LEXICON:
        m = pattern.search(text)
        if not m:
            continue
        # abandonment/rejection phrases are inherently directed ("pergi saja",
        # "capek sama kamu"); plain insults need a second-person marker.
        needs_marker = category == "insult"
        if needs_marker and not directed:
            continue
        severity = min(1.0, base + boost)
        if best is None or severity > best.severity:
            best = ConflictEvent(category=category, severity=severity)
    if best is None or best.severity < CONFLICT_MIN_SEVERITY:
        return None
    return best


def is_apology(text: str) -> bool:
    return bool(_APOLOGY_RE.search(text))


def compute_drift(window: list[float]) -> str:
    """EMO-001: classify recent-valence window. Hysteresis lives in the caller."""
    if len(window) < DRIFT_MIN_SAMPLES:
        return "insufficient"
    avg = sum(window) / len(window)
    if avg > DRIFT_POSITIVE:
        return "positive"
    if avg < DRIFT_NEGATIVE:
        return "negative"
    return "stable"


# ── Cycle orchestration ─────────────────────────────────────────────────────
def on_interaction(state, text: str, analysis, now: float,
                   cooldown_base_s: float = COOLDOWN_BASE_S) -> dict:
    """Apply the full conflict/cooldown/recovery/reconciliation cycle.

    Mutates `state`; returns an info dict for logging and tests.
    """
    info: dict = {"event": None, "apology": False, "drift": None, "damping": 1.0}

    # EMO-001: record significant valence into the drift window.
    if analysis.confidence >= 0.4:
        window = list(getattr(state, "drift_window", []) or [])
        window.append(analysis.valence)
        state.drift_window = window[-DRIFT_WINDOW_SIZE:]
    drift = compute_drift(list(state.drift_window or []))
    info["drift"] = drift

    # REL-004: reconciliation attempt.
    if is_apology(text):
        info["apology"] = True
        state.apology_count = getattr(state, "apology_count", 0) + 1
        if state.cooldown_until > now and state.apology_count <= APOLOGY_MAX_EFFECTIVE:
            remaining = state.cooldown_until - now
            state.cooldown_until = now + remaining * 0.5
            info["cooldown_halved"] = True

    in_cooldown = state.cooldown_until > now
    if in_cooldown:
        info["damping"] = DAMPING_IN_COOLDOWN
    else:
        # Cooldown expired: reset the apology budget for the next cycle.
        state.apology_count = 0

    # REL-001: new conflict?
    event = detect_conflict(text)
    if event is not None:
        if in_cooldown:
            event.severity = min(1.0, event.severity + ESCALATION_STEP)
        info["event"] = event
        info["damping"] = 1.0  # fresh conflict is not damped
        _apply_conflict(state, event, now, cooldown_base_s)
        return info

    # REL-003: gradual recovery once out of cooldown.
    if not in_cooldown and state.pending_recovery:
        _apply_recovery(state, analysis, info)
    return info


def _apply_conflict(state, event: ConflictEvent, now: float, cooldown_base_s: float):
    sev = event.severity
    gaps = {}
    for dim in ("affection", "trust", "attachment", "comfort"):
        before = getattr(state, dim)
        delta = -sev * {"trust": 0.10, "affection": 0.06, "comfort": 0.05, "attachment": 0.04}[dim]
        after = max(0.0, before + delta)
        setattr(state, dim, after)
        gaps[dim] = round(before - after, 4)
    merged = dict(state.pending_recovery or {})
    for dim, g in gaps.items():
        merged[dim] = round(merged.get(dim, 0.0) + g, 4)
    state.pending_recovery = merged
    state.conflict_severity = sev
    state.conflict_ts = now
    state.cooldown_until = now + cooldown_base_s * sev
    # Cold exterior during cooldown, via the existing mode system.
    state.emotional_mode = "withdrawn"
    state.mode_strength = max(state.mode_strength, 0.4)


def _apply_recovery(state, analysis, info: dict):
    """Heal toward the pre-conflict level. One turn never fully heals."""
    frac = RECOVERY_FRACTION
    if info.get("apology") and state.apology_count <= APOLOGY_MAX_EFFECTIVE:
        frac *= APOLOGY_BONUS
    if analysis.valence >= 0.2:
        frac *= min(1.5, 1.0 + analysis.valence)
    remaining = {}
    for dim, gap in (state.pending_recovery or {}).items():
        if gap <= RECOVERY_GAP_EPSILON:
            continue
        step = min(gap, gap * frac + 0.002)
        cur = getattr(state, dim)
        ceiling = cur + gap  # never overshoot past pre-conflict value
        setattr(state, dim, min(ceiling, cur + step))
        left = max(0.0, ceiling - getattr(state, dim))
        if left > RECOVERY_GAP_EPSILON:
            remaining[dim] = round(left, 4)
    state.pending_recovery = remaining
    if not remaining:
        state.conflict_severity = 0.0
