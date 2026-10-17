#!/usr/bin/env python3
"""Check electrical connectivity independently of the SVG routing.

Run from the project root: python3 -m unittest discover -s .utils -v
Builds go to a temporary directory and never rewrite the checked-in diagrams.
The expected terminal nets preserve each circuit, including the two parallel
RJ11 outputs on the 12 V minimum layout; holes and jumper paths may change.
"""
from collections import defaultdict
from contextlib import redirect_stdout
import csv
import importlib.util
import io
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


UTILS = Path(__file__).resolve().parent
ROOT = UTILS.parent
HOLE = re.compile(r"([a-j]|[LR][+-])(\d+)$")
PASSIVE = re.compile(r"[RC]\d+$")
SVG = "{http://www.w3.org/2000/svg}"

# Both GND headers, and both RESET headers, are internally connected on Nano.
NANO = {
    "Nano " + name
    for name in (
        "D13 / SCK", "3V3", "AREF", "A0", "A1", "A2", "A3", "A4",
        "A5", "A6", "A7", "5V / VUSB", "RESET", "GND", "VIN", "D12",
        "D11 / COPI", "D10", "D9", "D8", "D7", "D6", "D5", "D4",
        "D3", "D2", "RX", "TX",
    )
}
JACK = {"J0.1", "J0.2", "J0.3"}
USB_C_BREAKOUT = {
    "J0." + pin
    for pin in ("VBUS", "GND", "D-", "D+", "CC1", "CC2", "SBU1", "SBU2")
}
MOSFETS = {f"Q{q}.{pin}" for q in range(1, 4) for pin in "GDS"}
ADAPTER_UNUSED = {
    f"A{q}.{pin}" for q in range(1, 4)
    for pin in ("NC_LT", "NC_LB", "NC_RM")
}
RGB_STRIP = {"Strip +", "Strip R", "Strip G", "Strip B"}
RJ11_OUTPUTS = {f"J{port}.{pin}" for port in (1, 2) for pin in (2, 3, 4, 5)}
APA102_STRIP = {"Strip +5V", "Strip GND", "Strip CI", "Strip DI"}


def passive_terminals(prefix, numbers):
    return {f"{prefix}{number}.{pin}" for number in numbers for pin in (1, 2)}


EXPECTED_TERMINALS = {
    ("12v", "best"): (
        NANO | JACK | MOSFETS | RGB_STRIP
        | {f"U{u}.{pin}" for u in (1, 2) for pin in range(1, 9)}
        | passive_terminals("R", range(1, 10))
        | passive_terminals("C", range(3, 8))
    ),
    ("12v", "min"): (
        NANO | JACK | MOSFETS | RJ11_OUTPUTS | ADAPTER_UNUSED
        | passive_terminals("R", range(1, 4))
    ),
    ("5v", "best"): (
        NANO | USB_C_BREAKOUT | APA102_STRIP
        | {f"U1.{pin}" for pin in range(1, 15)}
        | passive_terminals("R", range(1, 5))
        | passive_terminals("C", range(1, 3))
    ),
    ("5v", "min"): NANO | APA102_STRIP,
}
KNOWN_TERMINALS = set().union(*EXPECTED_TERMINALS.values())

# All omitted terminals must remain separate singleton nets. A passive's .1
# and .2 identify its From and To leads; resistors/capacitors are not jumpers.
EXPECTED_CONNECTIONS = {
    ("12v", "best"): [
        ("C3.1", "C4.1", "C5.1", "C6.1", "C7.1", "J0.1", "Nano VIN",
         "Strip +", "U1.6", "U2.6"),
        ("C3.2", "C4.2", "C5.2", "C6.2", "C7.2", "J0.2", "Nano GND",
         "Q1.S", "Q2.S", "Q3.S", "R1.2", "R2.2", "R3.2", "R7.2",
         "R8.2", "R9.2", "U1.3", "U2.3", "U2.4"),
        ("Nano D3", "R1.1", "U1.2"),
        ("Nano D5", "R2.1", "U1.4"),
        ("Nano D6", "R3.1", "U2.2"),
        ("Q1.D", "Strip R"),
        ("Q2.D", "Strip G"),
        ("Q3.D", "Strip B"),
        ("Q1.G", "R4.2", "R7.1"),
        ("Q2.G", "R5.2", "R8.1"),
        ("Q3.G", "R6.2", "R9.1"),
        ("R4.1", "U1.7"),
        ("R5.1", "U1.5"),
        ("R6.1", "U2.7"),
    ],
    ("12v", "min"): [
        ("J0.1", "Nano VIN", "J1.2", "J2.2"),
        ("J0.2", "Nano GND", "Q1.S", "Q2.S", "Q3.S"),
        ("Nano D3", "R1.1"),
        ("Nano D5", "R2.1"),
        ("Nano D6", "R3.1"),
        ("Q1.D", "J1.3", "J2.3"),
        ("Q2.D", "J1.4", "J2.4"),
        ("Q3.D", "J1.5", "J2.5"),
        ("Q1.G", "R1.2"),
        ("Q2.G", "R2.2"),
        ("Q3.G", "R3.2"),
    ],
    ("5v", "best"): [
        ("C1.1", "C2.1", "J0.VBUS", "Nano VIN", "Strip +5V", "U1.10", "U1.13", "U1.14"),
        ("C1.2", "C2.2", "J0.GND", "Nano GND", "R1.2", "R2.2", "Strip GND",
         "U1.1", "U1.12", "U1.4", "U1.7", "U1.9"),
        ("Nano D11 / COPI", "R1.1", "U1.2"),
        ("Nano D13 / SCK", "R2.1", "U1.5"),
        ("R3.1", "U1.3"),
        ("R3.2", "Strip DI"),
        ("R4.1", "U1.6"),
        ("R4.2", "Strip CI"),
    ],
    ("5v", "min"): [
        ("Nano 5V / VUSB", "Strip +5V"),
        ("Nano GND", "Strip GND"),
        ("Nano D11 / COPI", "Strip DI"),
        ("Nano D13 / SCK", "Strip CI"),
    ],
}


def breadboard_bus(endpoint):
    """Map a hole to its copper strip, including the four split rail pairs."""
    match = HOLE.fullmatch(endpoint)
    if not match:
        return endpoint
    col, row = match[1], int(match[2])
    if not 1 <= row <= 64:
        raise AssertionError(f"Invalid breadboard hole: {endpoint}")
    if len(col) == 1:
        return ("left" if col <= "e" else "right", row)
    # Rows 32/33 are drawn as isolated holes, never part of either rail half.
    segment = "top" if row <= 31 else "bottom" if row >= 34 else row
    return (col, segment)


class Circuit:
    def __init__(self, wiring):
        self.parents = {}
        self.terminals = set()
        self.occupied = {}
        for label, start, end, _ in wiring:
            for endpoint in (start, end):
                if HOLE.fullmatch(endpoint):
                    breadboard_bus(endpoint)  # Also validate its row number.
                    if endpoint in self.occupied:
                        raise AssertionError(
                            f"{endpoint} used by {self.occupied[endpoint]} and {label}"
                        )
                    self.occupied[endpoint] = label
            if PASSIVE.fullmatch(label):
                self.connect(start, label + ".1")
                self.connect(end, label + ".2")
            elif (HOLE.fullmatch(start) or HOLE.fullmatch(end)
                  or (start in KNOWN_TERMINALS and end in KNOWN_TERMINALS)):
                self.connect(start, end)
            # Remaining records describe assembly/power instructions, not leads.

    def find(self, node):
        self.parents.setdefault(node, node)
        if self.parents[node] != node:
            self.parents[node] = self.find(self.parents[node])
        return self.parents[node]

    def connect(self, start, end):
        for endpoint in (start, end):
            if not HOLE.fullmatch(endpoint):
                self.terminals.add(endpoint)
        self.parents[self.find(breadboard_bus(start))] = self.find(breadboard_bus(end))

    def terminal_nets(self):
        nets = defaultdict(set)
        for terminal in self.terminals:
            nets[self.find(terminal)].add(terminal)
        return {frozenset(net) for net in nets.values()}


class BreadboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = tempfile.TemporaryDirectory(prefix="breadboard-tests-")
        cls.addClassCleanup(cls.output.cleanup)
        cls.layouts = {}
        for voltage in ("12v", "5v"):
            spec = importlib.util.spec_from_file_location(
                f"breadboard_{voltage}", ROOT / voltage / "build.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.OUT = Path(cls.output.name)
            for layout, function in (("best", module.build), ("min", module.build_minimum)):
                with redirect_stdout(io.StringIO()):
                    function()
                cls.layouts[voltage, layout] = (
                    list(module.wiring), ET.parse(module.OUT / f"{layout}.svg"), module
                )

    def test_breadboard_copper_model(self):
        self.assertEqual(breadboard_bus("a12"), breadboard_bus("e12"))
        self.assertEqual(breadboard_bus("f12"), breadboard_bus("j12"))
        self.assertNotEqual(breadboard_bus("e12"), breadboard_bus("f12"))
        self.assertNotEqual(breadboard_bus("a12"), breadboard_bus("a13"))
        for rail in ("L+", "L-", "R+", "R-"):
            self.assertEqual(breadboard_bus(rail + "1"), breadboard_bus(rail + "31"))
            self.assertEqual(breadboard_bus(rail + "34"), breadboard_bus(rail + "64"))
            self.assertEqual(
                len({breadboard_bus(rail + str(row)) for row in (31, 32, 33, 34)}), 4
            )
        self.assertEqual(len({breadboard_bus(rail + "1") for rail in ("L+", "L-", "R+", "R-")}), 4)

    def test_terminal_connections_and_isolation(self):
        for key, (wiring, _, _) in self.layouts.items():
            with self.subTest(voltage=key[0], layout=key[1]):
                circuit = Circuit(wiring)  # Also rejects any hole with two leads.
                self.assertEqual(circuit.terminals, EXPECTED_TERMINALS[key])
                expected = {frozenset(net) for net in EXPECTED_CONNECTIONS[key]}
                connected = set().union(*expected)
                expected.update(frozenset((pin,)) for pin in EXPECTED_TERMINALS[key] - connected)
                self.assertEqual(circuit.terminal_nets(), expected)

    def test_drawn_jumper_endpoints_match_wiring(self):
        for key, (wiring, svg, module) in self.layouts.items():
            with self.subTest(voltage=key[0], layout=key[1]):
                jumpers = {
                    label: (start, end)
                    for label, start, end, _ in wiring
                    if HOLE.fullmatch(start) and HOLE.fullmatch(end)
                    and not PASSIVE.fullmatch(label)
                }
                drawn = {}
                for group in svg.iter(SVG + "g"):
                    if not group.get("id", "").startswith("jumper-"):
                        continue
                    label = group.get("id").removeprefix("jumper-")
                    self.assertNotIn(label, drawn)
                    drawn[label] = (group.get("data-start"), group.get("data-end"))
                    paths = group.findall(SVG + "polyline")
                    self.assertTrue(paths, f"No wire drawn for {label}")
                    for path in paths:
                        points = [tuple(map(float, point.split(","))) for point in path.get("points").split()]
                        self.assertEqual(points[0], module.parse_hole(drawn[label][0]), label)
                        self.assertEqual(points[-1], module.parse_hole(drawn[label][1]), label)
                self.assertEqual(drawn, jumpers)

    def test_minimum_rj11_positive_bypasses_breadboard_contacts(self):
        wiring, _, _ = self.layouts["12v", "min"]
        direct_connections = Circuit([
            item for item in wiring
            if item[1] in KNOWN_TERMINALS and item[2] in KNOWN_TERMINALS
        ])
        for port in ("J1", "J2"):
            with self.subTest(port=port):
                self.assertEqual(
                    direct_connections.find("J0.1"), direct_connections.find(port + ".2")
                )

    def test_minimum_sot23_adapters_match_physical_leads(self):
        wiring, _, module = self.layouts["12v", "min"]
        leads = {}
        for _, start, end, _ in wiring:
            if start in MOSFETS | ADAPTER_UNUSED and HOLE.fullmatch(end):
                leads[start] = end
            elif end in MOSFETS | ADAPTER_UNUSED and HOLE.fullmatch(start):
                leads[end] = start

        # AO3400A datasheet top view, with its sole drain lead facing left:
        # source is upper-right, gate lower-right. The SparkFun board fans
        # each pad out to the same side and order, at 2.54 mm header pitch
        # with 7.62 mm between banks. Use positions, not adapter silkscreen
        # numbering, which differs between its Eagle file and product photo.
        # https://www.aosmd.com/res/data_sheets/AO3400A.pdf (page 1)
        # https://github.com/sparkfun/SOT23_DIP_Adapter/tree/master/Hardware
        circuit = Circuit(wiring)
        for q in range(1, 4):
            with self.subTest(mosfet=q):
                source = HOLE.fullmatch(leads[f"Q{q}.S"])
                self.assertEqual(source[1], "f")
                first = int(source[2])
                self.assertEqual(leads[f"Q{q}.G"], f"f{first + 2}")
                self.assertEqual(leads[f"Q{q}.D"], f"e{first + 1}")
                unused = {
                    f"A{q}.NC_LT": f"e{first}",
                    f"A{q}.NC_LB": f"e{first + 2}",
                    f"A{q}.NC_RM": f"f{first + 1}",
                }
                for terminal, hole in unused.items():
                    self.assertEqual(leads[terminal], hole)
                    self.assertIn(frozenset((terminal,)), circuit.terminal_nets())
                left = module.parse_hole(f"e{first}")
                right = module.parse_hole(f"f{first}")
                below = module.parse_hole(f"e{first + 1}")
                self.assertEqual(right[0] - left[0], 3 * (below[1] - left[1]))

    def test_minimum_five_volt_diagram_includes_required_solder_bridge(self):
        _, svg, _ = self.layouts["5v", "min"]
        visible_text = " ".join(
            "".join(element.itertext()) for element in svg.iter(SVG + "text")
        )
        self.assertIn("Close VUSB solder bridge", visible_text)


class PurchaseExportTests(unittest.TestCase):
    def test_build_clis_generate_digikey_orders_from_another_directory(self):
        expected_parts = {
            ("12v", "min"): {
                "AO3400A": 3,
                "00717": 3,
                "61300311121": 6,
                "CF14JT2K20": 10,
                "PJ-102AH": 1,
                "615004144121": 2,
            },
            ("12v", "best"): {
                "IRFZ44NPBF": 3,
                "TC4427ACPA": 2,
                "CF14JT100R": 10,
                "CF14JT10K0": 10,
                "K104K15X7RF5TH5": 2,
                "ECE-A1EKS4R7B": 2,
                "ECA-1EM101B": 1,
                "PJ-102AH": 1,
            },
            ("5v", "min"): {},
            ("5v", "best"): {
                "4090": 1,
                "SN74AHCT125N": 1,
                "CF14JT33R0": 2,
                "CF14JT10K0": 2,
                "K104K15X7RF5TH5": 1,
                "EEU-FC1A102B": 1,
            },
        }
        with tempfile.TemporaryDirectory(prefix="breadboard-purchase-tests-") as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            (project / ".utils").mkdir()
            for name in ("purchasing.py", "browser_viewer.py", "browser_viewer.js", "browser_viewer_styles.js"):
                shutil.copy2(UTILS / name, project / ".utils" / name)
            # Copy inputs only: checked-in exports must not mask a missing build.
            for voltage in ("12v", "5v"):
                for source in (ROOT / voltage).rglob("*"):
                    if (source.suffix not in {".py", ".csv"} and source.name != "center-positive.svg"
                            or source.name in {"min.csv", "best.csv"}):
                        continue
                    target = project / voltage / source.relative_to(ROOT / voltage)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
            workdir = root / "unrelated-directory"
            workdir.mkdir()
            for voltage in ("12v", "5v"):
                copied = project / voltage
                result = subprocess.run(
                    [sys.executable, str(copied / "build.py")], cwd=workdir,
                    capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(list(workdir.iterdir()), [])
                for layout in ("best", "min"):
                    with self.subTest(voltage=voltage, layout=layout):
                        self.assertEqual(ET.parse(copied / f"{layout}.svg").getroot().tag, SVG + "svg")
                        viewer = (copied / f"{layout}.html").read_text(encoding="utf-8")
                        self.assertNotIn('<svg ', viewer)
                        self.assertIn(f'&quot;{layout}.svg&quot;', viewer)
                        self.assertNotIn('<header', viewer)
                        self.assertNotIn('<style>', viewer)
                        self.assertNotIn('<script>', viewer)
                        self.assertIn('<script src="../.utils/browser_viewer.js" defer></script>', viewer)
                        self.assertIn('<script src="../.utils/browser_viewer_styles.js"></script>', viewer)
                        self.assertEqual(re.findall(r'<a href="([^"]+)" aria-label=', viewer), [
                            '../5v/min.html', '../12v/min.html',
                            '../5v/best.html', '../12v/best.html',
                        ])
                        with (copied / f"{layout}.csv").open(encoding="utf-8", newline="") as source:
                            reader = csv.DictReader(source)
                            self.assertIn("Quantity", reader.fieldnames)
                            self.assertIn("DigiKey Part Number", reader.fieldnames)
                            rows = list(reader)
                        expected = expected_parts[voltage, layout]
                        self.assertEqual(len(rows), len(expected))
                        self.assertTrue(all(row["DigiKey Part Number"] for row in rows))
                        # Exact contents exclude already-owned and future-upgrade parts.
                        self.assertEqual(
                            {row["Manufacturer Part Number"]: int(row["Quantity"]) for row in rows},
                            expected,
                        )
                        if (voltage, layout) == ("12v", "min"):
                            self.assertEqual(
                                {row["DigiKey Part Number"] for row in rows},
                                {"785-1000-1-ND", "CF14JT2K20CT-ND",
                                 "CP-102AH-ND", "732-3172-ND",
                                 "1568-00717-ND", "732-5316-ND"},
                            )
                        if (voltage, layout) == ("5v", "best"):
                            self.assertIn("1528-2873-ND", {
                                row["DigiKey Part Number"] for row in rows
                            })


if __name__ == "__main__":
    unittest.main()
