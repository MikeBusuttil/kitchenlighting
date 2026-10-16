#!/usr/bin/env python3
"""Check electrical connectivity independently of the SVG routing.

Run from the project root: python3 -m unittest -v test_breadboards.py
Builds go to a temporary directory and never rewrite the checked-in diagrams.
The expected terminal nets preserve the circuits before the wire-shortening
change; their physical holes and jumper paths may change freely.
"""
from collections import defaultdict
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
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
MOSFETS = {f"Q{q}.{pin}" for q in range(1, 4) for pin in "GDS"}
RGB_STRIP = {"Strip +", "Strip R", "Strip G", "Strip B"}
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
    ("12v", "min"): NANO | JACK | MOSFETS | RGB_STRIP,
    ("5v", "best"): (
        NANO | JACK | APA102_STRIP
        | {f"U1.{pin}" for pin in range(1, 15)}
        | passive_terminals("R", range(1, 5))
        | passive_terminals("C", range(1, 3))
    ),
    ("5v", "min"): NANO | JACK | APA102_STRIP,
}

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
        ("J0.1", "Nano VIN", "Strip +"),
        ("J0.2", "Nano GND", "Q1.S", "Q2.S", "Q3.S"),
        ("Nano D3", "Q1.G"),
        ("Nano D5", "Q2.G"),
        ("Nano D6", "Q3.G"),
        ("Q1.D", "Strip R"),
        ("Q2.D", "Strip G"),
        ("Q3.D", "Strip B"),
    ],
    ("5v", "best"): [
        ("C1.1", "C2.1", "J0.1", "Strip +5V", "U1.10", "U1.13", "U1.14"),
        ("C1.2", "C2.2", "J0.2", "Nano GND", "R1.2", "R2.2", "Strip GND",
         "U1.1", "U1.12", "U1.4", "U1.7", "U1.9"),
        ("Nano D11 / COPI", "R1.1", "U1.2"),
        ("Nano D13 / SCK", "R2.1", "U1.5"),
        ("R3.1", "U1.3"),
        ("R3.2", "Strip DI"),
        ("R4.1", "U1.6"),
        ("R4.2", "Strip CI"),
    ],
    ("5v", "min"): [
        ("J0.1", "Strip +5V"),
        ("J0.2", "Nano GND", "Strip GND"),
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
            elif HOLE.fullmatch(start) or HOLE.fullmatch(end) or label == "LED +":
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


if __name__ == "__main__":
    unittest.main()
