from solutions.p04_format_date import format_hl7_date


def _part(text: str, sep: str, n: int) -> str:
    parts = text.split(sep)
    return parts[n - 1] if n <= len(parts) else ""


def patient_summary(message: str) -> dict | None:
    pid = next((line.split("|") for line in message.splitlines() if line.startswith("PID|")), None)
    if pid is None:
        return None
    field = lambda n: pid[n] if n < len(pid) else ""
    return {
        "mrn": _part(field(3), "^", 1),
        "family": _part(_part(field(5), "^", 1), "&", 1),
        "given": _part(field(5), "^", 2),
        "dob": format_hl7_date(field(7)),
        "sex": field(8),
        "phones": [p for p in field(13).split("~") if p],
    }
