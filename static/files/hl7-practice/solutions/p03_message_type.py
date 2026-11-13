def message_type(message: str) -> tuple[str, str]:
    msh = message.splitlines()[0].split("|")
    msh_9 = msh[8]  # MSH-1 is the '|' itself, so MSH-n sits at index n-1
    code, event = (msh_9.split("^") + [""])[:2]
    return code, event
