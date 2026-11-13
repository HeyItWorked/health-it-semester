import importlib
import sys

# ---------------------------------------------------------------- sample messages

ADT = "\r".join([
    "MSH|^~\\&|REG|HOSP|EMR|HOSP|202611110930||ADT^A04^ADT_A01|MSG100|P|2.5.1",
    "EVN|A04|202611110930",
    "PID|1||12345^^^HOSP^MR||NGUYEN&VAN^AN^B||19900515|F|||12 LE LOI^^HUE^^530000^VN||(234)555-0101~(234)555-0202",
    "NK1|1|TRAN^BINH|SPO||(234)555-0303",
    "NK1|2|NGUYEN^CUONG|FTH",
    "PV1|1|O|CLINIC1||||277^ALLEN^KATRINA",
])

ORU_CBC = "\r".join([
    "MSH|^~\\&|LAB|HOSP|EMR|HOSP|202611111015||ORU^R01|MSG42|P|2.5.1",
    "PID|1||67890^^^HOSP^MR||BROWN^SAM||19780203|M",
    "OBR|1||ORD1|CBC^Complete Blood Count",
    "OBX|1|NM|GLU^Glucose||5.4|mmol/L|3.9-5.5|N",
    "OBX|2|NM|HGB^Hemoglobin||11.2|g/dL|13.5-17.5|L",
    "OBX|3|NM|WBC^White Cells||12.8|10*9/L|4.0-11.0|H",
    "NTE|1||Repeat test advised",
])

ACK_ONLY = "MSH|^~\\&|EMR|HOSP|LAB|HOSP|202611111016||ACK|ACKMSG42|P|2.5.1\rMSA|AA|MSG42"

GET_MSG = "\r".join([
    "MSH|^~\\&|LAB|HOSP|EMR|HOSP|202611110930||ORU^R01|MSG42|P|2.5.1",
    "PID|1||12345^^^HOSP^MR||NGUYEN&VAN^AN^B||19900515|F|||12 LE LOI^^HUE^^530000^VN||(234)555-0101~(234)555-0202",
    "OBX|1|NM|GLU^Glucose||5.4|mmol/L",
    "OBX|2|NM|HGB^Hemoglobin||13.9|g/dL",
])


def msh(msg_type, control_id="MSG1", processing="P", version="2.5.1", sender="LAB", receiver="EMR"):
    return f"MSH|^~\\&|{sender}|HOSP|{receiver}|HOSP|202611111015||{msg_type}|{control_id}|{processing}|{version}"


ORU = "\r".join([
    msh("ORU^R01", "MSG42"),
    "PID|1||12345^^^HOSP^MR~98765^^^CLINIC_B^MR||NGUYEN^AN^THI||19900515|F",
    "OBR|1|ORD1||2160-0^Creatinine^LN|||202611110800",
    "OBX|1|NM|2160-0^Creatinine^LN||1.8|mg/dL|0.6-1.2|H|||F",
    "OBX|2|NM|14749-6^Glucose^LN||5.4|mmol/L^mmol/L^UCUM|3.9-5.5|N|||F",
    "OBX|3|ST|8251-1^Service comment^LN||Hemolyzed sample||||||P",
])

ORU_BAD = "\r".join([
    msh("ORU^R01", "MSG43"),
    "PID|1||12345^^^HOSP^MR||NGUYEN^AN||19900515|F",
    "OBR|1|ORD5||2160-0^Creatinine^LN",
    "OBX|1|NM|GLU^Glucose^L||90|mg/dL||||",
    "OBX|2|NM|99999-9^Mystery^LN||<5|mg/dL|||||F",
    "OBX|3|NM|2160-0^Creatinine^LN||1.1|mg/dL|||||F",
])

ORU_SIMPLE = "\r".join([
    msh("ORU^R01", "MSG44"),
    "PID|1||67890^^^HOSP^MR||BROWN^SAM||197802|U",
    "OBX|1|NM|GLU^Glucose^L||90|mg/dL",
])

VT, FS_CR = b"\x0b", b"\x1c\x0d"
M_A = "MSH|^~\\&|A|B\rPID|1"
M_B = "MSH|^~\\&|C|D\rOBX|1"


def adt_with(old, new):
    assert ADT.count(old) == 1, old
    return ADT.replace(old, new)


def ack(code, ref, control_id="ACK1"):
    return msh("ACK^R01", control_id, sender="EMR", receiver="LAB") + f"\rMSA|{code}|{ref}"


def order_msg(placer, test, kind="ORM^O01"):
    return msh(kind, "M-" + placer) + f"\rPID|1||12345^^^HOSP^MR\rOBR|1|{placer}||{test}"


def pid_msg(pid3):
    return msh("ADT^A08") + f"\rPID|1||{pid3}||X^Y"


def run_reader(module, chunks):
    reader = module.MllpReader()
    return [reader.feed(c) for c in chunks]


def short(args):
    text = ", ".join(repr(a) for a in args)
    return text if len(text) <= 70 else text[:67] + "..."


def calls(func, cases):
    """(args, expected) pairs for a plain function -> (label, call(module), expected)."""
    return [(f"{func}({short(args)})", lambda m, a=args: getattr(m, func)(*a), expected) for args, expected in cases]


GET_CASES = [
    # basic fields
    ("PID-3", "12345^^^HOSP^MR"),
    ("PID-7", "19900515"),
    ("PID-8", "F"),
    # components / subcomponents
    ("PID-5.2", "AN"),
    ("PID-5.3", "B"),
    ("PID-5.1", "NGUYEN&VAN"),
    ("PID-5.1.1", "NGUYEN"),
    ("PID-5.1.2", "VAN"),
    ("PID-3.4", "HOSP"),
    ("PID-11.3", "HUE"),
    # repeats: first one only
    ("PID-13", "(234)555-0101"),
    # MSH off-by-one
    ("MSH-1", "|"),
    ("MSH-2", "^~\\&"),
    ("MSH-3", "LAB"),
    ("MSH-9", "ORU^R01"),
    ("MSH-9.2", "R01"),
    ("MSH-10", "MSG42"),
    # first of repeated segments
    ("OBX-5", "5.4"),
    ("OBX-3.2", "Glucose"),
    # not found / empty
    ("PID-4", ""),
    ("PID-3.2", ""),
    ("PID-30", ""),
    ("PID-5.9", ""),
    ("PID-7.1.5", ""),
    ("PV1-2", ""),
]

# ---------------------------------------------------------------- problems

# module -> [(label, call(module), expected)]; expected may be an exception class
PROBLEMS = {
    # 1. Reading messages
    "p01_segment_names": calls("segment_names", [
        ((ADT,), ["MSH", "EVN", "PID", "NK1", "NK1", "PV1"]),
        ((ORU_CBC.replace("\r", "\n") + "\n",), ["MSH", "PID", "OBR", "OBX", "OBX", "OBX", "NTE"]),
        ((ADT.replace("\r", "\r\n"),), ["MSH", "EVN", "PID", "NK1", "NK1", "PV1"]),
        (("",), []),
    ]),
    "p02_count_segments": calls("count_segments", [
        ((ORU_CBC,), {"MSH": 1, "PID": 1, "OBR": 1, "OBX": 3, "NTE": 1}),
        ((ADT.replace("\r", "\n"),), {"MSH": 1, "EVN": 1, "PID": 1, "NK1": 2, "PV1": 1}),
        (("",), {}),
    ]),
    "p03_message_type": calls("message_type", [
        ((ADT,), ("ADT", "A04")),
        ((ORU_CBC,), ("ORU", "R01")),
        ((ACK_ONLY,), ("ACK", "")),
        ((ORU_CBC.replace("\r", "\n"),), ("ORU", "R01")),
    ]),
    "p04_format_date": calls("format_hl7_date", [
        (("1990",), "1990"),
        (("199005",), "1990-05"),
        (("19900515",), "1990-05-15"),
        (("2026111109",), "2026-11-11 09"),
        (("202611110930",), "2026-11-11 09:30"),
        (("20261111093045",), "2026-11-11 09:30:45"),
        (("",), ""),
    ]),
    "p05_get_value": calls("get_value", [
        ((GET_MSG.replace("\r", eol), path), expected)
        for eol in ("\r", "\n", "\r\n")
        for path, expected in GET_CASES
    ]),
    "p06_patient_summary": calls("patient_summary", [
        ((ADT,), {"mrn": "12345", "family": "NGUYEN", "given": "AN", "dob": "1990-05-15",
                  "sex": "F", "phones": ["(234)555-0101", "(234)555-0202"]}),
        ((ORU_CBC,), {"mrn": "67890", "family": "BROWN", "given": "SAM", "dob": "1978-02-03",
                      "sex": "M", "phones": []}),
        ((ACK_ONLY,), None),
    ]),
    "p07_abnormal_results": calls("abnormal_results", [
        ((ORU_CBC,), ["Hemoglobin 11.2 g/dL (L)", "White Cells 12.8 10*9/L (H)"]),
        ((ORU_CBC.replace("|H\r", "|\r"),), ["Hemoglobin 11.2 g/dL (L)"]),
        ((ADT,), []),
    ]),
    # 2. Writing messages
    "p08_build_ack": calls("build_ack", [
        ((ORU_CBC, "AA", "202611111016"),
         "MSH|^~\\&|EMR|HOSP|LAB|HOSP|202611111016||ACK^R01|ACKMSG42|P|2.5.1\rMSA|AA|MSG42"),
        ((ADT.replace("\r", "\n"), "AE", "20261111"),
         "MSH|^~\\&|EMR|HOSP|REG|HOSP|20261111||ACK^A04|ACKMSG100|P|2.5.1\rMSA|AE|MSG100"),
    ]),
    "p09_set_value": calls("set_value", [
        ((ADT, "PID-8", "M"), adt_with("|19900515|F|", "|19900515|M|")),
        ((ADT, "PID-5.2", "ANH"), adt_with("NGUYEN&VAN^AN^B", "NGUYEN&VAN^ANH^B")),
        ((ADT, "PID-5.5", "DR"), adt_with("NGUYEN&VAN^AN^B", "NGUYEN&VAN^AN^B^^DR")),
        ((ADT, "PID-5.1.2", "VO"), adt_with("NGUYEN&VAN^AN^B", "NGUYEN&VO^AN^B")),
        ((ADT, "PID-3.1.2", "X"), adt_with("12345^^^HOSP^MR", "12345&X^^^HOSP^MR")),
        ((ADT, "PID-4.3", "Z"), adt_with("MR||NGUYEN", "MR|^^Z|NGUYEN")),
        ((ADT, "PID-13", "(234)555-9999"), adt_with("(234)555-0101~", "(234)555-9999~")),
        ((ADT, "PID-15", "vi"), adt_with("(234)555-0202", "(234)555-0202||vi")),
        ((ADT, "NK1-2.2", "AN"), adt_with("TRAN^BINH", "TRAN^AN")),
        ((ADT, "PV1-3.2", "ROOM5"), adt_with("|CLINIC1|", "|CLINIC1^ROOM5|")),
        ((ADT, "MSH-9.2", "A08"), adt_with("ADT^A04^ADT_A01", "ADT^A08^ADT_A01")),
        ((ADT, "MSH-10", "MSG101"), adt_with("|MSG100|", "|MSG101|")),
        ((ADT, "ZPI-3", "VIP"), ADT + "\rZPI|||VIP"),
        ((ADT.replace("\r", "\n"), "PV1-2", "I"), adt_with("PV1|1|O|", "PV1|1|I|")),
        ((ADT, "MSH-1", "x"), ValueError),
        ((ADT, "MSH-2", "x"), ValueError),
    ]),
    # 3. Transport (MLLP)
    "p10_mllp": [
        ("wrap", lambda m: m.wrap(M_A), VT + M_A.encode() + FS_CR),
        ("unwrap", lambda m: m.unwrap(VT + M_A.encode() + FS_CR), M_A),
        ("roundtrip", lambda m: m.unwrap(m.wrap(ORU)), ORU),
        ("no start byte", lambda m: m.unwrap(M_A.encode() + FS_CR), ValueError),
        ("no end bytes", lambda m: m.unwrap(VT + M_A.encode()), ValueError),
        ("only CR at end", lambda m: m.unwrap(VT + M_A.encode() + b"\r"), ValueError),
    ],
    "p11_mllp_reader": [
        ("one frame", lambda m: run_reader(m, [VT + M_A.encode() + FS_CR]), [[M_A]]),
        ("two frames one chunk", lambda m: run_reader(m, [VT + M_A.encode() + FS_CR + VT + M_B.encode() + FS_CR]),
         [[M_A, M_B]]),
        ("split in 3", lambda m: run_reader(m, [VT + b"MSH|^~", b"\\&|A|B\rPI", b"D|1" + FS_CR]), [[], [], [M_A]]),
        ("split between 1C and 0D", lambda m: run_reader(m, [VT + M_A.encode() + b"\x1c", b"\x0d"]), [[], [M_A]]),
        ("garbage before start", lambda m: run_reader(m, [b"noise" + VT + M_A.encode() + FS_CR]), [[M_A]]),
        ("frame + partial next", lambda m: run_reader(m, [VT + M_A.encode() + FS_CR + VT + b"MSH|^~\\&|C",
                                                          b"|D\rOBX|1" + FS_CR]), [[M_A], [M_B]]),
        ("byte by byte", lambda m: [x for x in run_reader(m, [bytes([b]) for b in VT + M_A.encode() + FS_CR]) if x],
         [[M_A]]),
    ],
    # 4. Engine front door: validate + route
    "p12_validate_header": [
        ("valid", lambda m: m.validate_header(ORU), []),
        ("not MSH", lambda m: m.validate_header("PID|1||123\rOBX|1"), ["NOT_MSH"]),
        ("bad encoding", lambda m: m.validate_header(ORU.replace("^~\\&", "^~&", 1)), ["BAD_ENCODING"]),
        ("no event", lambda m: m.validate_header(msh("ADT")), ["NO_MESSAGE_TYPE"]),
        ("no control id", lambda m: m.validate_header(msh("ORU^R01", "")), ["NO_CONTROL_ID"]),
        ("bad processing", lambda m: m.validate_header(msh("ORU^R01", processing="X")), ["BAD_PROCESSING_ID"]),
        ("version", lambda m: m.validate_header(msh("ORU^R01", version="2.3")), ["VERSION_MISMATCH"]),
        ("AU version w/ components", lambda m: m.validate_header(msh("ORU^R01", version="2.4^AUS&&ISO3166_1"), "2.4"), []),
        ("truncated MSH", lambda m: m.validate_header("MSH|^~\\&|A|B"),
         ["NO_MESSAGE_TYPE", "NO_CONTROL_ID", "BAD_PROCESSING_ID", "VERSION_MISMATCH"]),
    ],
    "p13_adt_router": [
        ("A01", lambda m: m.adt_action(msh("ADT^A01")), "OPEN_ENCOUNTER"),
        ("A02", lambda m: m.adt_action(msh("ADT^A02")), "MOVE_PATIENT"),
        ("A03", lambda m: m.adt_action(msh("ADT^A03")), "CLOSE_ENCOUNTER"),
        ("A04 with structure", lambda m: m.adt_action(msh("ADT^A04^ADT_A01")), "OPEN_OUTPATIENT"),
        ("A08 \\n endings", lambda m: m.adt_action(msh("ADT^A08") + "\nPID|1"), "UPDATE_PATIENT"),
        ("A11", lambda m: m.adt_action(msh("ADT^A11")), "CANCEL_ADMIT"),
        ("A31", lambda m: m.adt_action(msh("ADT^A31")), "UPDATE_PERSON"),
        ("unhandled ADT", lambda m: m.adt_action(msh("ADT^A28")), "IGNORE"),
        ("ORU", lambda m: m.adt_action(ORU), "NOT_ADT"),
    ],
    "p14_validate_results": [
        ("all good", lambda m: m.validate_results(ORU, {"2160-0", "14749-6", "8251-1"}), []),
        ("unknown code in good msg", lambda m: m.validate_results(ORU, {"2160-0", "14749-6"}),
         ["OBX 3: unknown LOINC 8251-1"]),
        ("bad msg", lambda m: m.validate_results(ORU_BAD, {"2160-0"}), [
            "OBX 1: not LOINC", "OBX 1: missing status",
            "OBX 2: unknown LOINC 99999-9", "OBX 2: non-numeric value",
        ]),
        ("no OBX", lambda m: m.validate_results(msh("ADT^A01"), {"2160-0"}), []),
    ],
    # 5. Reconciliation
    "p15_reconcile_acks": [
        ("mixed", lambda m: m.reconcile_acks(
            [msh("ORU^R01", c) for c in ["MSG1", "MSG2", "MSG3", "MSG4", "MSG4", "MSG5"]],
            [ack("AA", "MSG1"), ack("AE", "MSG2"), ack("AR", "MSG3"), ack("AA", "MSG3"), ack("AA", "MSG4"), ack("AA", "MSG9")]),
         {"MSG1": "AA", "MSG2": "AE", "MSG3": "AA", "MSG4": "DUPLICATE_ID", "MSG5": "MISSING", "ORPHAN:MSG9": "AA"}),
        ("nothing acked", lambda m: m.reconcile_acks([msh("ORU^R01", "X1")], []), {"X1": "MISSING"}),
        ("empty", lambda m: m.reconcile_acks([], []), {}),
    ],
    "p16_match_results": [
        ("mixed", lambda m: m.match_results(
            [order_msg("ORD1", "2160-0^Creatinine^LN"), order_msg("ORD2", "14749-6^Glucose^LN"),
             order_msg("ORD3", "718-7^Hemoglobin^LN")],
            [order_msg("ORD1", "2160-0^Creatinine^LN", "ORU^R01"), order_msg("ORD2", "2345-7^Glucose^LN", "ORU^R01"),
             order_msg("ORD9", "2160-0^Creatinine^LN", "ORU^R01")]),
         {"matched": ["ORD1"], "code_mismatch": ["ORD2"], "unknown_order": ["ORD9"], "pending": ["ORD3"]}),
        ("sorted output", lambda m: m.match_results(
            [order_msg("B", "1^x^LN"), order_msg("A", "1^x^LN")], []),
         {"matched": [], "code_mismatch": [], "unknown_order": [], "pending": ["A", "B"]}),
    ],
    "p17_link_patients": [
        ("chain + traps", lambda m: m.link_patients([
            pid_msg("12345^^^HOSP^MR~98765^^^CLINIC_B^MR"),
            pid_msg("98765^^^CLINIC_B^MR~555^^^LAB^MR"),
            pid_msg("777^^^HOSP^MR"),
            pid_msg("555^^^LAB^MR~888^^^PHARM^MR"),
            pid_msg("777^^^CLINIC_B^MR"),
            ack("AA", "MSG1"),
            pid_msg("12345"),
        ]), [["CLINIC_B:777"], ["CLINIC_B:98765", "HOSP:12345", "LAB:555", "PHARM:888"], ["HOSP:777"]]),
        ("link appears late", lambda m: m.link_patients([
            pid_msg("1^^^A"), pid_msg("2^^^B"), pid_msg("3^^^C"), pid_msg("1^^^A~3^^^C~2^^^B"),
        ]), [["A:1", "B:2", "C:3"]]),
        ("empty", lambda m: m.link_patients([]), []),
    ],
    # 6. Bridge to FHIR
    "p18_oru_to_fhir": [
        ("full ORU", lambda m: m.oru_to_fhir(ORU), {
            "patient": {
                "resourceType": "Patient",
                "identifier": [{"system": "HOSP", "value": "12345"}, {"system": "CLINIC_B", "value": "98765"}],
                "name": [{"family": "NGUYEN", "given": ["AN", "THI"]}],
                "birthDate": "1990-05-15",
                "gender": "female",
            },
            "observations": [
                {"resourceType": "Observation", "status": "final", "subject": {"reference": "Patient/12345"},
                 "code": {"coding": [{"system": "http://loinc.org", "code": "2160-0", "display": "Creatinine"}]},
                 "valueQuantity": {"value": 1.8, "unit": "mg/dL"},
                 "interpretation": [{"coding": [{"code": "H"}]}]},
                {"resourceType": "Observation", "status": "final", "subject": {"reference": "Patient/12345"},
                 "code": {"coding": [{"system": "http://loinc.org", "code": "14749-6", "display": "Glucose"}]},
                 "valueQuantity": {"value": 5.4, "unit": "mmol/L"},
                 "interpretation": [{"coding": [{"code": "N"}]}]},
                {"resourceType": "Observation", "status": "preliminary", "subject": {"reference": "Patient/12345"},
                 "code": {"coding": [{"system": "http://loinc.org", "code": "8251-1", "display": "Service comment"}]},
                 "valueString": "Hemolyzed sample"},
            ],
        }),
        ("sparse ORU", lambda m: m.oru_to_fhir(ORU_SIMPLE), {
            "patient": {
                "resourceType": "Patient",
                "identifier": [{"system": "HOSP", "value": "67890"}],
                "name": [{"family": "BROWN", "given": ["SAM"]}],
                "birthDate": "1978-02",
                "gender": "unknown",
            },
            "observations": [
                {"resourceType": "Observation", "status": "unknown", "subject": {"reference": "Patient/67890"},
                 "code": {"coding": [{"system": "L", "code": "GLU", "display": "Glucose"}]},
                 "valueQuantity": {"value": 90.0, "unit": "mg/dL"}},
            ],
        }),
    ],
}


def run_problem(module_name, use_solution):
    module = importlib.import_module(("solutions." if use_solution else "") + module_name)
    cases = PROBLEMS[module_name]
    passed = 0
    for label, call, expected in cases:
        try:
            got = call(module)
        except NotImplementedError:
            print(f"{module_name}: not started")
            return 0, len(cases)
        except Exception as e:
            got = e
        expects_error = isinstance(expected, type) and issubclass(expected, Exception)
        if (isinstance(got, expected) if expects_error else got == expected):
            passed += 1
        else:
            print(f"  FAIL [{label}]\n       expected {expected!r}\n       got      {got!r}")
    print(f"{module_name}: {passed}/{len(cases)}")
    return passed, len(cases)


if __name__ == "__main__":
    args = sys.argv[1:]
    use_solution = "--solution" in args
    prefixes = [a for a in args if a != "--solution"]
    names = [n for n in PROBLEMS if not prefixes or any(n.startswith(p) for p in prefixes)]
    total_passed = total = 0
    for name in names:
        p, t = run_problem(name, use_solution)
        total_passed += p
        total += t
    print(f"\nTOTAL {total_passed}/{total}")
    sys.exit(0 if total_passed == total else 1)
