from collections import Counter

from solutions._hl7 import field, first


def reconcile_acks(sent: list[str], acks: list[str]) -> dict[str, str]:
    sent_ids = [field(first(m, "MSH"), 10) for m in sent]
    counts = Counter(sent_ids)
    latest = {}
    for a in acks:
        msa = first(a, "MSA")
        latest[field(msa, 2)] = field(msa, 1)  # later ACK overwrites earlier one

    result = {}
    for cid in sent_ids:
        result[cid] = "DUPLICATE_ID" if counts[cid] > 1 else latest.get(cid, "MISSING")
    for cid, code in latest.items():
        if cid not in counts:
            result[f"ORPHAN:{cid}"] = code
    return result
