from solutions._hl7 import all_of, field, part


def _is_number(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


def validate_results(message: str, known_loinc: set[str]) -> list[str]:
    errors = []
    for obx in all_of(message, "OBX"):
        sid = field(obx, 1)
        code_field = field(obx, 3)
        if part(code_field, "^", 3) != "LN":
            errors.append(f"OBX {sid}: not LOINC")
        elif part(code_field, "^", 1) not in known_loinc:
            errors.append(f"OBX {sid}: unknown LOINC {part(code_field, '^', 1)}")
        if field(obx, 2) == "NM" and not _is_number(field(obx, 5)):
            errors.append(f"OBX {sid}: non-numeric value")
        if not field(obx, 11):
            errors.append(f"OBX {sid}: missing status")
    return errors
