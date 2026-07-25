"""
utils/text.py

Shared text utility functions.
"""
import re

CLEANUP_PATTERNS = [
    (re.compile(r"<\|im_start\|>\s*(?:assistant|user|system)?", re.I), ""),
    (re.compile(r"<\|im_end\|>"), ""),
    (re.compile(r"^\s*(?:assistant|user|system)\s*", re.I), ""),
]


def sanitize_llm_output(text: str) -> str:
    """Clean and sanitize the output from an LLM response."""
    text = text.strip()
    if "<|im_end|>" in text:
        text = text.split("<|im_end|>")[0]
    for pattern, replacement in CLEANUP_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()
