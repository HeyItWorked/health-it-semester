def segments(message: str) -> list[list[str]]:
    return [line.split("|") for line in message.splitlines() if line]


def field(seg: list[str], n: int) -> str:
    # MSH-1 is the '|' itself, so MSH-n sits at index n-1
    i = n - 1 if seg[0] == "MSH" else n
    return seg[i] if i < len(seg) else ""


def part(text: str, sep: str, n: int) -> str:
    parts = text.split(sep)
    return parts[n - 1] if n <= len(parts) else ""


def first(message: str, name: str) -> list[str] | None:
    return next((s for s in segments(message) if s[0] == name), None)


def all_of(message: str, name: str) -> list[list[str]]:
    return [s for s in segments(message) if s[0] == name]
