import re
import math
from tools.base import BaseTool, ToolResult

MAX_EXPR_LENGTH = 100
BLOCKED_PATTERNS = re.compile(r"__|\[|\]|\{|\}|lambda|import|exec|compile|eval|open|getattr|setattr")

PCT_PATTERNS = [
    re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:dari|of)?\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|persen)\s*(?:dari|of)\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
]


def _parse_percentage(expr: str):
    for pat in PCT_PATTERNS:
        m = pat.match(expr)
        if m:
            pct = float(m.group(1))
            total = float(m.group(2))
            return pct, total
    return None


class CalculatorTool(BaseTool):
    """
    Veil Tool: safe math expression evaluator.
    """

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluates safe math expressions (e.g., '2 + 2', 'sqrt(16)', '15% of 200')."

    @property
    def category(self) -> str:
        return "system"

    def execute(self, expression: str) -> ToolResult:
        expr = expression.strip()

        if not expr:
            return ToolResult.fail("Tidak ada ekspresi untuk dihitung.", "calculator")

        if len(expr) > MAX_EXPR_LENGTH:
            return ToolResult.fail(f"Ekspresi terlalu panjang (maks {MAX_EXPR_LENGTH} karakter).", "calculator")

        if BLOCKED_PATTERNS.search(expr):
            return ToolResult.fail("Ekspresi mengandung karakter yang tidak diizinkan.", "calculator")

        pct = _parse_percentage(expr)
        if pct:
            result = pct[0] / 100 * pct[1]
            a = int(pct[0]) if pct[0].is_integer() else pct[0]
            b = int(pct[1]) if pct[1].is_integer() else pct[1]
            return ToolResult.ok({"expression": expr, "result": f"{a}% dari {b} = {result:g}"}, "calculator")

        safe_globals = {
            "__builtins__": {},
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "log10": math.log10,
            "pi": math.pi,
            "e": math.e,
            "abs": abs,
            "round": round,
            "pow": pow,
        }

        try:
            result = eval(expr, safe_globals, {})  # noqa: S307
            if not isinstance(result, (int, float)):
                return ToolResult.fail("Hasil tidak valid.", "calculator")
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            return ToolResult.ok({"expression": expr, "result": f"{expr} = {result}"}, "calculator")
        except ZeroDivisionError:
            return ToolResult.fail("Error: Pembagian dengan nol tidak diperbolehkan.", "calculator")
        except Exception as e:
            return ToolResult.fail(f"Tidak bisa menghitung '{expr}': {str(e)}", "calculator")
