import random as _random
import time

from core.cognition import Cognition
from core.constraints import ConversationConstraints, render_constraints
from core.orchestrator import is_calculator_query, is_datetime_query, is_tavily_query
from utils.async_utils import with_retry
from utils.logger import log
from personality.analyzer import analyze
from personality.conflict import on_interaction
from personality.state import StellaState, StellaIdentity
from personality.inactivity import InactivityContext, InactivityEffect, compute_inactivity_context, compute_inactivity_effect
from personality.prompting import build_prompt
from personality.rhythm import compute_rhythm, try_reaction, ReactionResult, RhythmConfig
from personality import stella as identity
from personality.persistence import save_state, load_state
from memory.emotional import EmotionalMemory


class PersonalityCore:
    def __init__(self, agent, orchestrator, cognition_tools: dict | None = None):
        self.agent = agent
        self.orch = orchestrator
        self.cognition = Cognition(orchestrator.tools if cognition_tools is None else cognition_tools)
        self.emotional_memory = EmotionalMemory()
        self.constraints = ConversationConstraints(ttl=2)
        self.state = load_state()
        self.identity = StellaIdentity()
        self.last_reaction_ts: float = 0.0
        self._last_initiative_ts: float = 0.0
        self._last_absence_bucket: str = ""

    def _identity_blob(self) -> str:
        return (f"{identity.BASE_IDENTITY}\n\n{identity.LANGUAGE_RULES}\n\n"
                f"{identity.BEHAVIOR_RULES}\n\n{identity.EXAMPLES}")

    def _route_tool(self, text: str) -> str | None:
        _ok = lambda r: r is not None and r.success  # noqa: E731
        if is_calculator_query(text):
            result = with_retry(self.orch.run_tool, "calculator", text,
                                max_retries=1, success_fn=_ok)
            if result and result.success:
                return result.data.get("result", "")
            return None
        if is_datetime_query(text):
            result = with_retry(self.orch.run_tool, "datetime",
                                max_retries=1, success_fn=_ok)
            if result and result.success:
                return str(result.data)
            return None
        if is_tavily_query(text):
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
            pass
        else:
            self.state.emotional_mode = "yearning"
            self.state.mode_strength = 0.3

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

        cycle = on_interaction(self.state, user_input, analysis, now)
        if cycle["event"] is not None:
            ev = cycle["event"]
            log.info("Conflict: %s severity=%.2f cooldown_until=%d",
                     ev.category, ev.severity, self.state.cooldown_until)
        elif cycle["apology"]:
            log.info("Apology received (count=%d, cooldown_left=%ds)",
                     self.state.apology_count,
                     max(0, int(self.state.cooldown_until - now)))
        log.debug("Drift window %s -> %s", self.state.drift_window, cycle["drift"])

        self.state.update_from_interaction(
            analysis.emotion, analysis.arousal, analysis.confidence,
            damping=cycle.get("damping", 1.0))
        self.state.decay()
        if analysis.confidence >= 0.4:
            self.emotional_memory.record("interaction", user_input[:120], analysis.valence, analysis.arousal)
        self._update_baseline_mood()
        self._update_emotional_mode(analysis)

        rhythm = compute_rhythm(self.state, analysis)
        # Probabilistic interjection shortcuts are disabled during evaluation
        # runs (they bypass the LLM entirely -> 1-token replies pollute metrics).
        reaction = None
        if getattr(self, "reactions_enabled", True):
            reaction = try_reaction(self.state, analysis, self.last_reaction_ts, _random, now)
        if reaction is not None:
            self.last_reaction_ts = now
            self.state.last_interaction_ts = now
            save_state(self.state)
            return reaction.text

        cognition_context = ""
        if not (abs(analysis.valence) > 0.4 and analysis.arousal > 0.5):
            if Cognition.can_handle(user_input):
                result = self.cognition.process(user_input)
                if result:
                    cognition_context = result
            if not cognition_context:
                tool_result = self._route_tool(user_input)
                if tool_result:
                    cognition_context = tool_result

        self.state.last_interaction_ts = now
        save_state(self.state)

        emotional_summary = self.emotional_memory.emotional_summary()
        cflags = self.constraints.observe(user_input)
        constraints = render_constraints(cflags)
        system = build_prompt(self._identity_blob(), self.state, emotional_summary,
                              inactivity_ctx, rhythm, user_constraints=constraints)

        reply = self.agent.generate(system, user_input, cognition_context,
                                    closing=cflags.get("conversation_closing", False),
                                    no_questions=cflags.get("avoid_questions", False))
        self.constraints.tick()
        return reply
