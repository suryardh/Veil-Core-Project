from datetime import datetime, timezone, timedelta
from tools.base import BaseTool, ToolResult

WIB = timezone(timedelta(hours=7))

DAYS = {
    "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
    "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu",
    "Sunday": "Minggu",
}

MONTHS = {
    "January": "Januari", "February": "Februari", "March": "Maret",
    "April": "April", "May": "Mei", "June": "Juni",
    "July": "Juli", "August": "Agustus", "September": "September",
    "October": "Oktober", "November": "November", "December": "Desember",
}


class DateTimeTool(BaseTool):
    """
    Veil Tool: returns current Jakarta (WIB) date and time.
    """

    @property
    def name(self) -> str:
        return "datetime"

    @property
    def description(self) -> str:
        return "Returns the current date and time in Indonesian timezone (WIB)."

    @property
    def category(self) -> str:
        return "system"

    def execute(self, *args, **kwargs) -> ToolResult:
        now = datetime.now(WIB)
        day = DAYS.get(now.strftime("%A"), now.strftime("%A"))
        month = MONTHS.get(now.strftime("%B"), now.strftime("%B"))
        return ToolResult(
            success=True,
            data=(
                f"Tanggal: {day}, {now.day} {month} {now.year}\n"
                f"Waktu: {now.strftime('%H:%M:%S WIB')}"
            ),
            source="datetime",
        )
