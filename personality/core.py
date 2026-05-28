import random as _random
import re
import time

from core.cognition import Cognition
from utils.async_utils import with_retry
from personality.analyzer import analyze
from personality.state import StellaState, StellaIdentity
from personality.inactivity import InactivityContext, InactivityEffect, compute_inactivity_context, compute_inactivity_effect
from personality.prompting import build_prompt
from personality.rhythm import compute_rhythm, try_reaction, ReactionResult, RhythmConfig
from personality import stella as identity
from personality.persistence import save_state, load_state
from memory.emotional import EmotionalMemory

CALC_PATTERNS = [
    re.compile(r"^[\d\s+\-*/().,%^]+$"),
    re.compile(r"(^|\s)(hitung|calculate|persen)(\s|$)", re.IGNORECASE),
    re.compile(r"\d+\s*[+\-*/%]\s*\d+"),
    re.compile(r"\b(sqrt|sin|cos|tan|log|abs|round|pow)\s*\(", re.I),
    re.compile(r"\d+\s*%\s*(?:dari)?\s*\d+"),
]

_DATETIME_TRIGGERS = ["jam berapa", "tanggal berapa", "hari ini", "sekarang jam", "what time", "what date", "current time", "current date"]

_TAVILY_TRIGGERS = ["cek usage", "cek tavily", "tavily usage", "sisa usage", "penggunaan api"]


def _is_calculator(text: str) -> bool:
    return any(p.search(text) for p in CALC_PATTERNS)


def _is_datetime(text: str) -> bool:
    lower = text.lower()
    return any(t in lower for t in _DATETIME_TRIGGERS)


def _is_tavily(text: str) -> bool:
    lower = text.lower()
    return any(t in lower for t in _TAVILY_TRIGGERS)


class PersonalityCore:
    def __init__(self, agent, orchestrator, cognition_tools: dict | None = None):
        self.agent = agent
        self.orch = orchestrator
        self.cognition = Cognition(orchestrator.tools if cognition_tools is None else cognition_tools)
        self.emotional_memory = EmotionalMemory()
        self.state = load_state()
        self.identity = StellaIdentity()
        self.last_reaction_ts: float = 0.0
        self._last_initiative_ts: float = 0.0
        self._last_absence_bucket: str = ""

    def _identity_blob(self) -> str:
        return f"{identity.BASE_IDENTITY}\n\n{identity.LANGUAGE_RULES}\n\n{identity.BEHAVIOR_RULES}"

    def _route_tool(self, text: str) -> str | None:
        _ok = lambda r: r is not None and r.success  # noqa: E731
        if _is_calculator(text):
            result = with_retry(self.orch.run_tool, "calculator", text,
                                max_retries=1, success_fn=_ok)
            if result and result.success:
                return result.data.get("result", "")
            return None
        if _is_datetime(text):
            result = with_retry(self.orch.run_tool, "datetime",
                                max_retries=1, success_fn=_ok)
            if result and result.success:
                return str(result.data)
            return None
        if _is_tavily(text):
            result = with_retry(self.orch.run_tool, "tavily_usage",
                                max_retries=1, success_fn=_ok)
            if result and result.success:
                return str(result.data.get("raw", ""))
            return None
        return None

    def _update_baseline_mood(self):
        recent = self.emotional_memory.recall_recent(5)
        if len(recent) < 2:
            return
        avg_val = sum(r["valence"] for r in recent) / len(recent)
        if avg_val > 0.15:
            self.state.baseline_mood = "warm"
        elif avg_val < -0.15:
            self.state.baseline_mood = "subdued"
        else:
            self.state.baseline_mood = "neutral"

    def _apply_inactivity_effect(self, effect: InactivityEffect):
        if effect.severity in ("recent", "short"):
            self._last_absence_bucket = ""
            return
        if effect.severity == self._last_absence_bucket:
            return
        self._last_absence_bucket = effect.severity
        self.state.trust = max(0.0, min(1.0, self.state.trust + effect.trust_delta))
        self.state.attachment = max(0.0, min(1.0, self.state.attachment + effect.attachment_delta))
        if effect.mood_shift and self.state.mode_strength < 0.4:
            self.state.emotional_mode = effect.mood_shift
            self.state.mode_strength = 0.45

    def _update_emotional_mode(self, analysis):
        new_mode = None
        self.state.mode_strength *= 0.85

        if analysis.valence < -0.3 and analysis.arousal > 0.3 and self.state.trust > 0.25:
            new_mode = "comforting"
        elif analysis.emotion == "intimate" and analysis.valence > 0.5:
            new_mode = "yearning"
        elif analysis.arousal > 0.6 and analysis.valence > 0.3:
            new_mode = "excited"
        elif analysis.valence > 0.4 and analysis.arousal < 0.4:
            new_mode = "soft"
        elif analysis.valence < -0.5:
            new_mode = "withdrawn"

        if new_mode is not None:
            if new_mode != self.state.emotional_mode and self.state.mode_strength > 0.5:
                pass  # Guard: mode kuat → tolak overwrite dari mode berbeda, biarkan decay dulu
            else:
                self.state.emotional_mode = new_mode
                self.state.mode_strength = min(1.0, self.state.mode_strength + 0.4)
        elif self.state.mode_strength > 0.15:
            pass  # Mode masih aktif (strength > 0.15) → biarkan decay alami tanpa reset ke neutral
        else:
            self.state.emotional_mode = "neutral"
            self.state.mode_strength = 0.0

    def initiative_cue(self, inactivity_ctx: InactivityContext | None = None) -> str | None:
        now = time.time()
        if now - self._last_initiative_ts < 300:
            return None
        from personality.initiative import try_initiate
        if inactivity_ctx is None:
            inactivity_ctx = compute_inactivity_context(self.state, now)
        event = try_initiate(self.state, inactivity_ctx, _random)
        if event is None:
            return None
        self._last_initiative_ts = now
        return event.opener

    def handle(self, user_input: str) -> str:
        now = time.time()
        effect = compute_inactivity_effect(self.state, now)
        self._apply_inactivity_effect(effect)
        inactivity_ctx = compute_inactivity_context(self.state, now)
        analysis = analyze(user_input) 

        self.state.update_from_interaction(analysis.emotion, analysis.arousal, analysis.confidence)
        self.state.decay()
        if analysis.confidence >= 0.4:
            self.emotional_memory.record("interaction", user_input[:120], analysis.valence, analysis.arousal)
        self._update_baseline_mood()
        self._update_emotional_mode(analysis)

        rhythm = compute_rhythm(self.state, analysis)
        reaction = try_reaction(self.state, analysis, self.last_reaction_ts, _random, now)
        if reaction is not None:
            self.last_reaction_ts = now
            self.state.last_interaction_ts = now
            save_state(self.state)
            return reaction.text

        cognition_context = ""
        is_emotional = abs(analysis.valence) > 0.4 and analysis.arousal > 0.5
        if is_emotional:
            pass
        else:
            tool_result = self._route_tool(user_input)
            if tool_result:
                cognition_context = tool_result
            elif Cognition.can_handle(user_input):
                result = self.cognition.process(user_input)
                if result:
                    cognition_context = result

        self.state.last_interaction_ts = now
        save_state(self.state)

        emotional_summary = self.emotional_memory.emotional_summary()
        system = build_prompt(self._identity_blob(), self.state, emotional_summary, inactivity_ctx, rhythm)

        return self.agent.generate(system, user_input, cognition_context)
