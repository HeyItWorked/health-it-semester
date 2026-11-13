from solutions._hl7 import field, first, part

ACTIONS = {
    "A01": "OPEN_ENCOUNTER", "A02": "MOVE_PATIENT", "A03": "CLOSE_ENCOUNTER", "A04": "OPEN_OUTPATIENT",
    "A08": "UPDATE_PATIENT", "A11": "CANCEL_ADMIT", "A31": "UPDATE_PERSON",
}


def adt_action(message: str) -> str:
    msh_9 = field(first(message, "MSH"), 9)
    if part(msh_9, "^", 1) != "ADT":
        return "NOT_ADT"
    return ACTIONS.get(part(msh_9, "^", 2), "IGNORE")
