"""
llm/prompt.py

Prompt construction utilities for Veil.
Provides helpers for formatting chat history, injecting tool results,
and building the final prompt string sent to the LLM engine.
"""


def sanitize_prompt_text(text: str) -> str:
    """
    Escapes role labels inside external content (e.g. tool results)
    so they don't confuse the prompt structure.
    """
    return (
        text.replace("User:", "[USER]")
            .replace("User :", "[USER]")
            .replace("Stella:", "[STELLA]")
            .replace("Stella :", "[STELLA]")
    )


def format_chat_history(history: list,
                        user_name: str = "User",
                        assistant_name: str = "Stella") -> str:
    """
    Formats a list of {'role': str, 'content': str} messages into
    a plain-text conversation block for use in a prompt context.
    """
    if not history:
        return ""
    lines = []
    for msg in history:
        role = user_name if msg.get("role") == "user" else assistant_name
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def build_final_prompt(system_prompt: str,
                       user_input: str,
                       assistant_name: str = "Stella",
                       user_name: str = "User") -> str:
    """
    Assembles the full prompt string from a system prompt block
    and the latest user turn. This is the format sent directly to the LLM.
    """
    return f"{system_prompt}\n\n{user_name}: {user_input}\n{assistant_name}:".strip()


def truncate_context(text: str, max_chars: int = 1200) -> str:
    """
    Truncates a context string to a maximum character count,
    keeping the most recent (tail) portion to preserve recency.
    """
    if len(text) <= max_chars:
        return text
    return "...\n" + text[-max_chars:]


def inject_tool_result(tool_name: str, result: str) -> str:
    """
    Wraps a tool execution result into a labeled context block
    for clean injection into the prompt.
    """
    return f"""
External tool result:
Tool name: {tool_name}

Result:
{sanitize_prompt_text(result.strip())}
""".strip()
