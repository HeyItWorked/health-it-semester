from solutions._hl7 import field, part, segments


def validate_header(message: str, expected_version: str = "2.5.1") -> list[str]:
    segs = segments(message)
    if not segs or segs[0][0] != "MSH":
        return ["NOT_MSH"]
    msh = segs[0]
    errors = []
    if field(msh, 2) != "^~\\&":
        errors.append("BAD_ENCODING")
    if not part(field(msh, 9), "^", 1) or not part(field(msh, 9), "^", 2):
        errors.append("NO_MESSAGE_TYPE")
    if not field(msh, 10):
        errors.append("NO_CONTROL_ID")
    if field(msh, 11) not in ("P", "T", "D"):
        errors.append("BAD_PROCESSING_ID")
    if part(field(msh, 12), "^", 1) != expected_version:
        errors.append("VERSION_MISMATCH")
    return errors
