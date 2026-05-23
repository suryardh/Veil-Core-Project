import re

CALC_PATTERNS = [
    re.compile(r"^[\d\s+\-*/().,%^]+$"),
    re.compile(r"(^|\s)(hitung|calculate|sqrt|persen)(\s|$)", re.IGNORECASE),
    re.compile(r"\d+\s*[+\-*/%]\s*\d+"),
]


def _is_calculator(text: str) -> bool:
    return any(p.search(text) for p in CALC_PATTERNS)


class IntentRouter:
    """
    Rule-based intent detection.
    Decides what kind of action a user input maps to.
    """

    @staticmethod
    def detect(user_input: str) -> str:
        text = user_input.lower()
        text_stripped = text.strip()

        if any(k in text for k in ["search", "cari", "browse", "browsing", "google", "ddg"]):
            return "web_search"
        if any(k in text for k in ["screenshot", "lihat layar", "screen"]):
            return "vision"
        if any(text_stripped.startswith(p) for p in ["ingat ", "ingatkan ", "remember "]):
            return "memory_write"
        if any(
            k in text
            for k in [
                "jam berapa",
                "tanggal berapa",
                "hari ini",
                "sekarang jam",
                "what time",
                "what date",
                "today is",
                "current time",
                "current date",
            ]
        ):
            return "datetime"
        if _is_calculator(text):
            return "calculator"
        return "chat"
