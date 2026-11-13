# HL7 v2 Practice

One practice set that follows the path a message takes through a real interface engine:
read a message → write a message → send/receive over MLLP → validate + route → reconcile → bridge to FHIR.
Problems 01–09 build the basic parse/build helpers; problems 10–18 are simulated integration-engineer tickets that reuse those helpers.

```
python3 test_practice.py              # test every problem (untouched ones show "not started")
python3 test_practice.py p05          # one problem (prefix match)
python3 test_practice.py --solution   # reference solutions in solutions/ (don't peek!)
```

Write your code in the `pNN_*.py` files. Sample messages are at the top of `test_practice.py`; read them first.
Later problems should **reuse** earlier code (import or copy). LOINC codes here are for practice only, not a clinical reference.

| # | Problem | Level | What it trains / real-world job | Reuses |
|---|---|---|---|---|
| | **1. Reading messages** | | | |
| 01 | `segment_names` | Easy | split lines, split fields | |
| 02 | `count_segments` | Easy | dict counting | 01 |
| 03 | `message_type` | Easy | MSH off-by-one, component split | |
| 04 | `format_hl7_date` | Easy | string slicing by length | |
| 05 | `get_value` | Medium | path parsing `SEG-F.C.S` | |
| 06 | `patient_summary` | Medium | compose helpers, repeats → list | 04, 05 |
| 07 | `abnormal_results` | Medium | loop over repeated segments, filter, format | 05 |
| | **2. Writing messages** | | | |
| 08 | `build_ack` | Medium | build a message: swap fields, reference the original | 03, 05 |
| 09 | `set_value` | Hard | set a nested value + padding, keep everything else intact | 05 |
| | **3. Transport (MLLP)** | | | |
| 10 | `mllp` wrap/unwrap | Easy | MLLP framing (bytes framing) | |
| 11 | `MllpReader` | Hard | read a TCP stream split at arbitrary points (stateful buffer) | 10 |
| | **4. Engine front door** | | | |
| 12 | `validate_header` | Easy | reject broken messages at the door (validation checklist) | 05 |
| 13 | `adt_action` | Easy | ADT feed → action for downstream (dict lookup) | 03 |
| 14 | `validate_results` | Medium | enforce LOINC at ingest (loop + rules) | 07 |
| | **5. Reconciliation** | | | |
| 15 | `reconcile_acks` | Medium | end-of-day ACK reconciliation (hash map join) | 08 (`MSH-10` ↔ `MSA-2`) |
| 16 | `match_results` | Medium | route results to the right order (join 2 datasets) | 05 |
| 17 | `link_patients` | Medium | MPI: merge IDs from many facilities into one person (union-find, LC 721) | 05 |
| | **6. Bridge to FHIR** | | | |
| 18 | `oru_to_fhir` | Hard | ORU → Patient + Observation (nested mapping + convert) | 04, 06, 07 |

---

# Section 1 — Reading messages

## 01. `segment_names(message) -> list[str]` (Easy)

Return the segment names in order. Line endings may be `\r`, `\n`, or `\r\n`. Skip empty lines.

```
ADT → ['MSH', 'EVN', 'PID', 'NK1', 'NK1', 'PV1']
""  → []
```


## 02. `count_segments(message) -> dict[str, int]` (Easy)

Count how many times each segment appears.

```
ORU → {'MSH': 1, 'PID': 1, 'OBR': 1, 'OBX': 3, 'NTE': 1}
```


## 03. `message_type(message) -> tuple[str, str]` (Easy)

Return `(MSH-9.1, MSH-9.2)`. No event → event = `""`. Ignore `MSH-9.3`.

```
ADT (MSH-9 = ADT^A04^ADT_A01) → ('ADT', 'A04')
ORU (MSH-9 = ORU^R01)         → ('ORU', 'R01')
MSH-9 = ACK                   → ('ACK', '')
```


## 04. `format_hl7_date(ts) -> str` (Easy)

HL7 timestamp = `YYYY[MM[DD[HH[MM[SS]]]]]`; the longer it is, the more precise. Format it for humans, printing only the parts present:

```
'1990'            → '1990'
'199005'          → '1990-05'
'19900515'        → '1990-05-15'
'2026111109'      → '2026-11-11 09'
'202611110930'    → '2026-11-11 09:30'
'20261111093045'  → '2026-11-11 09:30:45'
''                → ''
```


## 05. `get_value(message, path) -> str` (Medium)

Return the value in an HL7 v2 message at the given path.

**Path format:** `SEG-F`, `SEG-F.C`, or `SEG-F.C.S`
- `SEG`: 3-letter segment name (`MSH`, `PID`, `OBX`...)
- `F`: field number (1-based)
- `C`: component number (1-based), split by `^`
- `S`: subcomponent number (1-based), split by `&`

Rules:
1. Segments are separated by `\r`, `\n`, or `\r\n` (real files often get their line endings converted).
2. If a segment appears more than once (e.g. several `OBX`), use **the first one**.
3. If a field has repeats (`~`), use **the first repeat**.
4. **MSH is special:** `MSH-1` = `|` (the separator itself), `MSH-2` = `^~\&` (returned as-is, not split). So `MSH-n` (n ≥ 3) is off by one compared with other segments.
5. Not found (missing segment, field/component/subcomponent out of range, or empty) → return `""`.
6. Separators are fixed: `| ^ ~ \ &` (no need to read them from MSH-2 yet).

```
MSH|^~\&|LAB|HOSP|EMR|HOSP|202611110930||ORU^R01|MSG42|P|2.5.1
PID|1||12345^^^HOSP^MR||NGUYEN&VAN^AN^B||19900515|F|||12 LE LOI^^HUE^^530000^VN||(234)555-0101~(234)555-0202
```

| path | output |
|---|---|
| `PID-5.2` | `AN` |
| `PID-5.1.1` | `NGUYEN` |
| `PID-13` | `(234)555-0101` |
| `MSH-9.2` | `R01` |
| `PID-4` | `""` |

Follow-up (optional):
- Support a repeat index: `PID-13[2]` → `(234)555-0202`.
- Read separators from `MSH-2` instead of hardcoding them.
- `set_value(message, path, value)`: that is problem 09.


## 06. `patient_summary(message) -> dict | None` (Medium)

Extract patient info from `PID`. No `PID` → `None`.

| key | from | note |
|---|---|---|
| `mrn` | `PID-3.1` | |
| `family` | `PID-5.1.1` | surname, without the prefix |
| `given` | `PID-5.2` | |
| `dob` | `PID-7` | formatted with problem 04 |
| `sex` | `PID-8` | |
| `phones` | `PID-13` | **all** repeats, as a list; none → `[]` |

```
ADT → {'mrn': '12345', 'family': 'NGUYEN', 'given': 'AN', 'dob': '1990-05-15',
       'sex': 'F', 'phones': ['(234)555-0101', '(234)555-0202']}
```


## 07. `abnormal_results(message) -> list[str]` (Medium)

Walk **every** `OBX`, keep the ones with an abnormal flag (`OBX-8` not empty and not `N`), formatted as:
`"<OBX-3.2> <OBX-5> <OBX-6> (<OBX-8>)"`

```
ORU → ['Hemoglobin 11.2 g/dL (L)', 'White Cells 12.8 10*9/L (H)']
ADT → []
```


# Section 2 — Writing messages

## 08. `build_ack(message, ack_code, now) -> str` (Medium)

Build the ACK replying to the original message. Output is 2 segments joined by `\r`:

```
MSH|^~\&|<MSH-5>|<MSH-6>|<MSH-3>|<MSH-4>|<now>||ACK^<MSH-9.2>|ACK<MSH-10>|<MSH-11>|<MSH-12>
MSA|<ack_code>|<original MSH-10>
```

- Sender/receiver swap: the receiving app/facility (`MSH-5/6`) now becomes the sender.
- `MSA-2` must equal the original `MSH-10` so the other side knows which message is being acknowledged.

```
build_ack(ORU, 'AA', '202611111016') →
MSH|^~\&|EMR|HOSP|LAB|HOSP|202611111016||ACK^R01|ACKMSG42|P|2.5.1\rMSA|AA|MSG42
```


## 09. `set_value(message, path, value) -> str` (Hard)

The inverse of `get_value`: return a new message with the value at `path` replaced. Same path format as problem 05.

Rules:
1. Everything else stays exactly the same. Output joins segments with `\r`.
2. Segment appears more than once → change **the first one**.
3. Field has repeats → change only **the first repeat**, keep the others.
4. Field/component/subcomponent doesn't exist yet → **pad** with empty separators up to that position.
5. Segment doesn't exist yet → append a new segment at the end of the message.
6. `MSH-1`, `MSH-2` → `raise ValueError`. `MSH-n` (n ≥ 3) is off by one, as in problem 05.
7. `value` contains no separators (no escaping needed).

```
PID-5.2   = 'ANH'  : NGUYEN&VAN^AN^B   → NGUYEN&VAN^ANH^B
PID-5.5   = 'DR'   : NGUYEN&VAN^AN^B   → NGUYEN&VAN^AN^B^^DR
PID-4.3   = 'Z'    : PID-4 empty       → ^^Z
PID-13    = 'X'    : 0101~0202         → X~0202
ZPI-3     = 'VIP'  : no ZPI            → append 'ZPI|||VIP'
```


# Section 3 — Transport (MLLP)

## 10. MLLP wrap / unwrap (Easy)

> **INT-101:** A new lab sends over MLLP. Write 2 helpers to wrap/unwrap a frame.

- `wrap(message: str) -> bytes`: `0x0B` + message (ASCII) + `0x1C 0x0D`.
- `unwrap(frame: bytes) -> str`: the reverse. Frame doesn't start with `0x0B` or doesn't end with `0x1C 0x0D` → `raise ValueError`.

```
wrap("MSH|...\rPID|...") → b"\x0bMSH|...\rPID|...\x1c\r"
```
Note: the `\r` between segments is **not** the end of the frame.


## 11. MLLP stream reader (Hard)

> **INT-301:** TCP doesn't guarantee 1 `recv()` = 1 message. Write a reader that survives any kind of split.

```python
class MllpReader:
    def feed(self, chunk: bytes) -> list[str]: ...
```
- Each `feed` returns the **complete** messages just finished (could be 0, 1, or many).
- Partial data is kept for the next chunk — even when `0x1C` and `0x0D` land in 2 different chunks.
- Garbage bytes before `0x0B` → dropped.


# Section 4 — Engine front door: validate + route

## 12. Validate header (Easy)

> **INT-103:** The engine's queue is backing up because of junk messages. Block them at the door and return a list of error codes.

`validate_header(message: str, expected_version: str = "2.5.1") -> list[str]`

- First segment isn't `MSH` → return `["NOT_MSH"]` immediately.
- Otherwise check in **exactly this order**, collecting every error:
  1. `BAD_ENCODING`: `MSH-2` ≠ `^~\&`
  2. `NO_MESSAGE_TYPE`: `MSH-9.1` or `MSH-9.2` empty
  3. `NO_CONTROL_ID`: `MSH-10` empty
  4. `BAD_PROCESSING_ID`: `MSH-11` not one of `P`, `T`, `D`
  5. `VERSION_MISMATCH`: `MSH-12.1` ≠ `expected_version` (`MSH-12` may have components, e.g. `2.4^AUS&&ISO3166_1`)
- A missing field = empty. Valid → `[]`.


## 13. ADT router (Easy)

> **INT-102:** Transport/billing only need to know what to do, not how to read HL7. Map ADT event → action.

`adt_action(message: str) -> str`

| `MSH-9` | return |
|---|---|
| `ADT^A01` | `OPEN_ENCOUNTER` |
| `ADT^A02` | `MOVE_PATIENT` |
| `ADT^A03` | `CLOSE_ENCOUNTER` |
| `ADT^A04` | `OPEN_OUTPATIENT` |
| `ADT^A08` | `UPDATE_PATIENT` |
| `ADT^A11` | `CANCEL_ADMIT` |
| `ADT^A31` | `UPDATE_PERSON` |
| other ADT event | `IGNORE` |
| not ADT | `NOT_ADT` |

Trap: `ADT^A04^ADT_A01` is **A04**, not A01.


## 14. Validate results (LOINC on ingest) (Medium)

> **INT-202:** Results go "missing" because of bad LOINC codes and nobody reports an error. Validate each OBX.

`validate_results(message: str, known_loinc: set[str]) -> list[str]`

For each OBX in order (`<id>` = `OBX-1`), check and collect every error:
1. `OBX-3.3` ≠ `LN` → `"OBX <id>: not LOINC"`; otherwise if `OBX-3.1` is not in `known_loinc` → `"OBX <id>: unknown LOINC <code>"`
2. `OBX-2` = `NM` but `OBX-5` doesn't parse as a number → `"OBX <id>: non-numeric value"`
3. `OBX-11` empty → `"OBX <id>: missing status"`


# Section 5 — Reconciliation

## 15. Reconcile ACKs (Medium)

> **INT-201:** At end of day we need to know which messages the other side received.

`reconcile_acks(sent: list[str], acks: list[str]) -> dict[str, str]`

- Key = `MSH-10` of each sent message. Value = `MSA-1` of the ACK whose `MSA-2` = key.
- No ACK → `"MISSING"`.
- Same `MSH-10` sent ≥ 2 times → `"DUPLICATE_ID"` (regardless of ACKs).
- Several ACKs for the same ID (retries) → the **last** ACK wins.
- ACK pointing to an ID not in `sent` → key `"ORPHAN:<id>"`, value = `MSA-1`.


## 16. Match results to orders (Medium)

> **INT-203:** A doctor reports "ordered 2 days ago, still no result". Reconcile orders vs results.

`match_results(orders: list[str], results: list[str]) -> dict[str, list[str]]`

Each message (ORM or ORU) has exactly 1 `OBR`. Join key = placer order number `OBR-2`; test code = `OBR-4.1`.

| output key | contains |
|---|---|
| `matched` | order has a result with the same test code |
| `code_mismatch` | order has a result but `OBR-4.1` differs |
| `unknown_order` | result points to an order that doesn't exist |
| `pending` | order has no result yet |

Each list holds placer order numbers, **sorted**.


## 17. Link patients (MPI) (Medium)

> **INT-204:** Same person, but one ID per facility → the system sees 2–3 patients. Merge them.

`link_patients(messages: list[str]) -> list[list[str]]`

- Each `PID-3` repeat → identifier `"<PID-3.4>:<PID-3.1>"` (authority:id). Skip repeats missing the id or the authority.
- Identifiers in **the same message** = the same person. The same identifier in several messages = link those people together.
- Same ID number but different authority (`HOSP:777` vs `CLINIC_B:777`) = **different people**.
- Message without PID → skip.
- Output: each group sorted; the list of groups sorted.


# Section 6 — Bridge to FHIR

## 18. ORU → FHIR (lite) (Hard)

> **INT-302:** A new downstream only accepts FHIR. Convert ORU into Patient + Observations.

`oru_to_fhir(message: str) -> dict` → `{"patient": {...}, "observations": [...]}`

**Patient** (from PID):
| key | from |
|---|---|
| `resourceType` | `"Patient"` |
| `identifier` | each `PID-3` repeat → `{"system": PID-3.4, "value": PID-3.1}` |
| `name` | `[{"family": PID-5.1.1, "given": [PID-5.2, PID-5.3 if present]}]` |
| `birthDate` | first 8 chars of `PID-7` → `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`; empty → **omit the key** |
| `gender` | `M`→`male`, `F`→`female`, `O`→`other`, anything else→`unknown` |

**Observation** (one per OBX, in order):
| key | from |
|---|---|
| `resourceType` | `"Observation"` |
| `status` | `OBX-11`: `F`→`final`, `P`→`preliminary`, `C`→`corrected`, `X`→`cancelled`, anything else→`unknown` |
| `subject` | `{"reference": "Patient/<PID-3.1 of the first repeat>"}` |
| `code` | `{"coding": [{"system": ..., "code": OBX-3.1, "display": OBX-3.2}]}`; system = `http://loinc.org` if `OBX-3.3` = `LN`, otherwise keep `OBX-3.3` as-is |
| `valueQuantity` | if `OBX-2` = `NM`: `{"value": float(OBX-5), "unit": OBX-6.1}` (unit may be `mmol/L^mmol/L^UCUM`) |
| `valueString` | if `OBX-2` is not `NM`: `OBX-5` |
| `interpretation` | if `OBX-8` is not empty: `[{"coding": [{"code": OBX-8}]}]`; empty → **omit the key** |
