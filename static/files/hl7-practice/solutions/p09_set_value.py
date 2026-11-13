def _set_nested(text: str, nums: list[int], seps: str, value: str) -> str:
    if not nums:
        return value
    parts = text.split(seps[0])
    i = nums[0] - 1
    parts += [""] * (i + 1 - len(parts))  # pad missing components/subcomponents
    parts[i] = _set_nested(parts[i], nums[1:], seps[1:], value)
    return seps[0].join(parts)


def set_value(message: str, path: str, value: str) -> str:
    segment, numbers = path.split("-")
    field_num, *sub_nums = [int(n) for n in numbers.split(".")]
    if segment == "MSH" and field_num <= 2:
        raise ValueError("MSH-1 and MSH-2 hold the separators and cannot be set")

    rows = [line.split("|") for line in message.splitlines() if line]
    row = next((r for r in rows if r[0] == segment), None)
    if row is None:
        row = [segment]
        rows.append(row)

    index = field_num - 1 if segment == "MSH" else field_num
    row += [""] * (index + 1 - len(row))  # pad missing fields

    repeats = row[index].split("~")
    repeats[0] = _set_nested(repeats[0], sub_nums, "^&", value)
    row[index] = "~".join(repeats)
    return "\r".join("|".join(r) for r in rows)
