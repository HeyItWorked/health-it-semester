from collections import Counter

from solutions.p01_segment_names import segment_names


def count_segments(message: str) -> dict[str, int]:
    return dict(Counter(segment_names(message)))
