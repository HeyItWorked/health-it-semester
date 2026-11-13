from solutions._hl7 import field, first, part


def _key_and_code(message: str) -> tuple[str, str]:
    obr = first(message, "OBR")
    return field(obr, 2), part(field(obr, 4), "^", 1)


def match_results(orders: list[str], results: list[str]) -> dict[str, list[str]]:
    ordered = dict(_key_and_code(m) for m in orders)
    out = {"matched": [], "code_mismatch": [], "unknown_order": [], "pending": []}
    resulted = set()
    for m in results:
        placer, code = _key_and_code(m)
        resulted.add(placer)
        if placer not in ordered:
            out["unknown_order"].append(placer)
        elif ordered[placer] == code:
            out["matched"].append(placer)
        else:
            out["code_mismatch"].append(placer)
    out["pending"] = [p for p in ordered if p not in resulted]
    return {k: sorted(v) for k, v in out.items()}
