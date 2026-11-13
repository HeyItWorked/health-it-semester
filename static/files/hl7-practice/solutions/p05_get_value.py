def get_value(message: str, path: str) -> str:
    seg_name, _, rest = path.partition("-")
    field_num, *sub_nums = (int(n) for n in rest.split("."))

    for line in message.splitlines():  # handles \r, \n, \r\n
        fields = line.split("|")
        if fields[0] != seg_name:
            continue

        if seg_name == "MSH":
            if field_num == 1:
                return "|"
            if field_num == 2:
                return fields[1]
            index = field_num - 1  # MSH-1 is the separator itself, so everything shifts by one
        else:
            index = field_num

        if index >= len(fields):
            return ""
        value = fields[index].split("~")[0]

        for sep, n in zip("^&", sub_nums):
            parts = value.split(sep)
            if n > len(parts):
                return ""
            value = parts[n - 1]
        return value

    return ""
