from solutions._hl7 import field, first, part


def link_patients(messages: list[str]) -> list[list[str]]:
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for m in messages:
        pid = first(m, "PID")
        if pid is None:
            continue
        ids = []
        for rep in field(pid, 3).split("~"):
            id_, auth = part(rep, "^", 1), part(rep, "^", 4)
            if id_ and auth:
                ids.append(f"{auth}:{id_}")
        for i in ids:
            parent.setdefault(i, i)
        for i in ids[1:]:
            parent[find(i)] = find(ids[0])

    groups = {}
    for i in parent:
        groups.setdefault(find(i), []).append(i)
    return sorted(sorted(g) for g in groups.values())
