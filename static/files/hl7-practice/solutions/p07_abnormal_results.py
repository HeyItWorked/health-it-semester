def abnormal_results(message: str) -> list[str]:
    results = []
    for line in message.splitlines():
        obx = line.split("|")
        if obx[0] != "OBX":
            continue
        obx += [""] * (9 - len(obx))  # pad so OBX-3..OBX-8 always exist
        flag = obx[8]
        if flag in ("", "N"):
            continue
        name = (obx[3].split("^") + [""])[1]
        results.append(f"{name} {obx[5]} {obx[6]} ({flag})")
    return results
