"""Component legend for the placement PDF, using the circuit's fitted parts.

Only the human-readable function names and grouping live here. Values, exact
part identities, and connector details come from ``pcb_design.PARTS`` so the
legend cannot silently retain an old BOM value after a circuit change.
"""
from collections import Counter
import re

from pcb_design import PARTS


LEGEND_HEADERS = ("Reference", "Component / function", "Value / key specification")

# Reference label, individual references, human-readable function, value source.
_GROUPS = (
    ("J1", ("J1",), "DC barrel power input", "barrel"),
    ("J2, J3", ("J2", "J3"), "Nano female sockets", "socket"),
    ("J4-J7", ("J4", "J5", "J6", "J7"), "Vertical RJ11 RGB outputs", "rj11"),
    ("F1", ("F1",), "Input fuse", "value"),
    ("F2-F5", ("F2", "F3", "F4", "F5"), "RJ11 branch fuses", "value"),
    ("U1, U2", ("U1", "U2"), "Dual MOSFET gate drivers", "mpn"),
    ("U3", ("U3",), "Linear voltage regulator", "regulator"),
    ("Q1-Q3", ("Q1", "Q2", "Q3"), "RGB low-side N-channel MOSFETs", "mpn"),
    ("Q4", ("Q4",), "Reverse-polarity P-channel MOSFET", "mpn"),
    ("D1", ("D1",), "Gate-protection Zener diode", "zener"),
    ("D2", ("D2",), "Input surge suppressor (TVS)", "mpn"),
    ("D3", ("D3",), "Nano VIN isolation Schottky diode", "mpn"),
    ("D4-D6", ("D4", "D5", "D6"), "RGB cable-clamp Schottky diodes", "mpn"),
    ("C1", ("C1",), "Bulk input capacitor", "value"),
    ("C2", ("C2",), "Regulator input bypass capacitor", "value"),
    ("C3", ("C3",), "Regulator output capacitor", "value"),
    ("C4, C5, C7", ("C4", "C5", "C7"), "Regulator / driver bypass capacitors", "value"),
    ("C6, C8", ("C6", "C8"), "Driver local supply capacitors", "value"),
    ("R1-R3", ("R1", "R2", "R3"), "PWM input series resistors", "value"),
    ("R4-R6, R10-R12", ("R4", "R5", "R6", "R10", "R11", "R12"),
     "Input / MOSFET-gate pulldown resistors", "value"),
    ("R7-R9", ("R7", "R8", "R9"), "MOSFET-gate series resistors", "value"),
    ("R13", ("R13",), "Reverse-polarity gate bias resistor", "value"),
    ("R14", ("R14",), "Regulator minimum-load resistor", "value"),
    ("H1-H4", ("H1", "H2", "H3", "H4"), "M3 mounting holes (not fitted parts)", "hole"),
)


def _display_value(value):
    """Expand compact CAD units for readers who do not use resistor notation."""
    value = value.split(" / minimum load", 1)[0]
    value = re.sub(r"(\d+(?:\.\d+)?)([un])\b",
                   lambda m: f"{m[1]} {'µ' if m[2] == 'u' else 'n'}F", value)
    match = re.fullmatch(r"(\d+)k(\d*)", value)
    if match:
        return f"{match[1]}{'.' + match[2] if match[2] else ''} kΩ"
    match = re.fullmatch(r"(\d+)R", value)
    return f"{match[1]} Ω" if match else value


def _specification(part, source):
    if source == "mpn":
        return part["mpn"]
    if source == "regulator":
        return f"{part['mpn']}; {part['value'].rsplit(' / ', 1)[-1]}"
    if source == "barrel":
        rating, plug, *_ = part["note"].split("; ")
        return (f"{part['value'].replace(' IN /', ',')}; "
                f"{rating.removesuffix(' jack')}; "
                f"{plug.removesuffix(' mating plug')}")
    if source == "socket":
        return f"{len(part['pins'])}-way; {part['note'].split(';')[0]}"
    if source == "rj11":
        return "; ".join(part["note"].split("; ")[:2])
    if source == "zener":
        return f"{part['value'].removesuffix(' gate clamp')}; {part['mpn']}"
    if source == "hole":
        return part["note"].split("; ")[-1]
    return _display_value(part["value"])


def legend_rows(parts=None):
    """Return 3-column rows covering every supplied PCB reference exactly once.

    Reject stale groupings when the circuit changes. Shared rows must still use
    identical part numbers and footprints, and shared value rows must agree on
    their electrical value.
    """
    parts = list(PARTS if parts is None else parts)
    by_ref = {part["ref"]: part for part in parts}
    covered = Counter(ref for _, refs, _, _ in _GROUPS for ref in refs)
    if len(by_ref) != len(parts) or set(covered) != set(by_ref) or any(
            count != 1 for count in covered.values()):
        raise ValueError("Placement legend must cover every PCB reference exactly once")

    rows = []
    for label, refs, function, source in _GROUPS:
        group = [by_ref[ref] for ref in refs]
        if len({(part["mpn"], part["footprint"]) for part in group}) != 1:
            raise ValueError(f"Placement legend group {label} contains different parts")
        specs = {_specification(part, source) for part in group}
        if len(specs) != 1:
            raise ValueError(f"Placement legend group {label} contains different specifications")
        rows.append((label, function, specs.pop()))
    return rows
