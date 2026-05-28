import re

import time

from core.cognition import Cognition
from personality.analyzer import analyze
from personality.state import StellaState, StellaIdentity
from personality.inactivity import compute_inactivity_context
from personality.prompting import build_prompt
from personality import stella as identity
from personality.persistence import save_state, load_state
from memory.emotional import EmotionalMemory

CALC_PATTERNS = [
    re.compile(r"^[\d\s+\-*/().,%^]+$"),
    re.compile(r"(^|\s)(hitung|calculate|sqrt|persen)(\s|$)", re.IGNORECASE),
    re.compile(r"\d+\s*[+\-*/%]\s*\d+"),
]

_DATETIME_TRIGGERS = ["jam berapa", "tanggal berapa", "hari ini", "sekarang jam", "what time", "what date", "current time", "current date"]


def _is_calculator(text: str) -> bool:
    return any(p.search(text) for p in CALC_PATTERNS)


def _is_datetime(text: str) -> bool:
    lower = text.lower()
    return any(t in lower for t in _DATETIME_TRIGGERS)


class PersonalityCore:
    def __init__(self, agent, orchestrator, cognition_tools: dict | None = None):
        self.agent = agent
        self.orch = orchestrator
        self.cognition = Cognition(orchestrator.tools if cognition_tools is None else cognition_tools)
        self.emotional_memory = EmotionalMemory()
        self.state = load_state()
        self.identity = StellaIdentity()

    def _identity_blob(self) -> str:
        return f"{identity.BASE_IDENTITY}\n\n{identity.LANGUAGE_RULES}\n\n{identity.BEHAVIOR_RULES}"

    def _route_tool(self, text: str) -> str | None:
        if _is_calculator(text):
            result = self.orch.run_tool("calculator", text)
            if result.success:
                return result.data.get("result", "")
            return None
        if _is_datetime(text):
            result = self.orch.run_tool("datetime")
            if result.success:
                return str(result.data)
            return None
        return None

    def handle(self, user_input: str) -> str:
        inactivity_ctx = compute_inactivity_context(self.state, time.time())
        analysis = analyze(user_input) 

        self.state.update_from_interaction(analysis.emotion, analysis.arousal, analysis.confidence)
        self.state.decay()
        if analysis.confidence >= 0.4:
            self.emotional_memory.record("interaction", user_input[:120], analysis.valence, analysis.arousal)

        cognition_context = ""
        if Cognition.can_handle(user_input):
            result = self.cognition.process(user_input)
            if result:
                cognition_context = result
        else:
            tool_result = self._route_tool(user_input)
            if tool_result:
                cognition_context = tool_result

        self.state.last_interaction_ts = time.time()
        save_state(self.state)

        emotional_summary = self.emotional_memory.emotional_summary()
        system = build_prompt(self._identity_blob(), self.state, emotional_summary, user_input, cognition_context, inactivity_ctx)

        return self.agent.generate(system, user_input)
