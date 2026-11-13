class MllpReader:
    """INT-301. See README.md."""

    def feed(self, chunk: bytes) -> list[str]:
        raise NotImplementedError
