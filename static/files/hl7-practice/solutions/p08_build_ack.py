from solutions.p03_message_type import message_type


def build_ack(message: str, ack_code: str, now: str) -> str:
    msh = message.splitlines()[0].split("|")
    m = lambda n: msh[n - 1]  # MSH-n sits at index n-1
    _, event = message_type(message)
    ack_type = f"ACK^{event}" if event else "ACK"
    header = ["MSH", m(2), m(5), m(6), m(3), m(4), now, "", ack_type, "ACK" + m(10), m(11), m(12)]
    return "|".join(header) + "\r" + f"MSA|{ack_code}|{m(10)}"
