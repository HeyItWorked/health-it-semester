START, END = b"\x0b", b"\x1c\x0d"


def wrap(message: str) -> bytes:
    return START + message.encode("ascii") + END


def unwrap(frame: bytes) -> str:
    if not (frame.startswith(START) and frame.endswith(END)):
        raise ValueError("not an MLLP frame")
    return frame[len(START):-len(END)].decode("ascii")
