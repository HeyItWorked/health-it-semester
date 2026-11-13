from solutions._hl7 import all_of, field, first, part

GENDER = {"M": "male", "F": "female", "O": "other"}
STATUS = {"F": "final", "P": "preliminary", "C": "corrected", "X": "cancelled"}


def _patient(pid: list[str]) -> dict:
    identifiers = [{"system": part(r, "^", 4), "value": part(r, "^", 1)} for r in field(pid, 3).split("~")]
    name = field(pid, 5)
    given = [g for g in (part(name, "^", 2), part(name, "^", 3)) if g]
    patient = {
        "resourceType": "Patient",
        "identifier": identifiers,
        "name": [{"family": part(part(name, "^", 1), "&", 1), "given": given}],
    }
    dob = field(pid, 7)[:8]
    if dob:
        patient["birthDate"] = "-".join(p for p in (dob[:4], dob[4:6], dob[6:8]) if p)
    patient["gender"] = GENDER.get(field(pid, 8), "unknown")
    return patient


def _observation(obx: list[str], patient_id: str) -> dict:
    code = field(obx, 3)
    system = part(code, "^", 3)
    obs = {
        "resourceType": "Observation",
        "status": STATUS.get(field(obx, 11), "unknown"),
        "subject": {"reference": f"Patient/{patient_id}"},
        "code": {"coding": [{"system": "http://loinc.org" if system == "LN" else system,
                             "code": part(code, "^", 1), "display": part(code, "^", 2)}]},
    }
    if field(obx, 2) == "NM":
        obs["valueQuantity"] = {"value": float(field(obx, 5)), "unit": part(field(obx, 6), "^", 1)}
    else:
        obs["valueString"] = field(obx, 5)
    if field(obx, 8):
        obs["interpretation"] = [{"coding": [{"code": field(obx, 8)}]}]
    return obs


def oru_to_fhir(message: str) -> dict:
    patient = _patient(first(message, "PID"))
    patient_id = patient["identifier"][0]["value"]
    return {"patient": patient, "observations": [_observation(o, patient_id) for o in all_of(message, "OBX")]}
