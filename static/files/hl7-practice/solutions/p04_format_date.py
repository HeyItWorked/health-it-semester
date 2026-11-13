def format_hl7_date(ts: str) -> str:
    # (start, end, separator placed before this piece)
    pieces = [(0, 4, ""), (4, 6, "-"), (6, 8, "-"), (8, 10, " "), (10, 12, ":"), (12, 14, ":")]
    return "".join(sep + ts[start:end] for start, end, sep in pieces if len(ts) >= end)
