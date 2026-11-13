def segment_names(message: str) -> list[str]:
    return [line.split("|")[0] for line in message.splitlines() if line]
