START, END = b"\x0b", b"\x1c\x0d"


class MllpReader:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, chunk: bytes) -> list[str]:
        self.buffer += chunk
        messages = []
        while True:
            start = self.buffer.find(START)
            if start == -1:
                self.buffer.clear()  # no frame started: everything is noise
                break
            del self.buffer[:start]
            end = self.buffer.find(END)
            if end == -1:
                break  # incomplete frame, wait for more bytes
            messages.append(self.buffer[1:end].decode("ascii"))
            del self.buffer[:end + len(END)]
        return messages
