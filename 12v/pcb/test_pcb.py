"""Electrical and mechanical regression invariants for the 12 V carrier.

Run with ``python3 -m unittest discover -s 12v/pcb -p 'test_pcb.py'``. These checks
need only the standard library; they do not replace KiCad DRC, measurement of
current/temperature, or verification of the assembled hardware.

The assertions encode interface facts and safety-critical circuit paths,
independently of the design generator's loops and placement implementation.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from pcb_design import (BOARD, BY_REF, PARTS, ROOT, OUTPUT_COUNT, STRIP_LENGTH_M,
                        STRIP_W_PER_M, SUPPLY_V, CONNECTOR_RATING_A)
from pcb_schematic import child, children, compare_netlist, parse


def net(ref, pin):
    return BY_REF[ref]['pins'][str(pin)]


def members(name):
    return {(p['ref'], pin) for p in PARTS
            for pin, value in p['pins'].items() if value == name}


class MechanicalInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = parse((ROOT / 'pcb.kicad_pcb').read_text())
        cls.footprints = {
            next(t[2] for t in children(fp, 'fp_text') if t[1] == 'reference'): fp
            for fp in children(cls.board, 'footprint')
        }

    def test_fabricated_outline_fits_two_by_four_inches(self):
        """Check the exported outline as well as the declared design envelope."""
        edges = [edge for edge in children(self.board, 'gr_line')
                 if child(edge, 'layer')[1] == 'Edge.Cuts']
        self.assertEqual(len(edges), 4, 'Expected a closed rectangular board outline')
        endpoints = [tuple(map(float, child(edge, key)[1:3]))
                     for edge in edges for key in ('start', 'end')]
        actual = (min(x for x, _ in endpoints), min(y for _, y in endpoints),
                  max(x for x, _ in endpoints), max(y for _, y in endpoints))
        for envelope in (BOARD, actual):
            with self.subTest(envelope=envelope):
                x0, y0, x1, y1 = envelope
                self.assertGreater(x1 - x0, 0)
                self.assertGreater(y1 - y0, 0)
                self.assertLessEqual(x1 - x0, 2 * 25.4)
                self.assertLessEqual(y1 - y0, 4 * 25.4)
        self.assertEqual(actual, tuple(BOARD), 'Native board has a stale outline')
        x0, y0, x1, y1 = actual
        self.assertEqual(set(endpoints), {(x0, y0), (x1, y0), (x1, y1), (x0, y1)})
        for corner in set(endpoints):
            self.assertEqual(endpoints.count(corner), 2, 'Outline is not closed')

    def test_barrel_and_nano_usb_open_at_same_board_edge(self):
        """Use physical connector dimensions, independent of placement loops."""
        x0, y0, x1, _ = BOARD
        jack, left, right = (BY_REF[ref] for ref in ('J1', 'J2', 'J3'))
        self.assertEqual(jack['mpn'], 'PJ-063AH')
        # Same Sky drawing: the mouth is 12 mm toward local +Y from pin 1.
        # Rotating the footprint 180 degrees faces the Nano's USB/pin-1 edge.
        self.assertEqual(jack['rotation'] % 360, 180)
        self.assertLessEqual(abs(jack['xy'][1] - 12 - y0), 1.0)
        for socket in (left, right):
            self.assertEqual(socket['rotation'] % 360, 0)
            self.assertGreaterEqual(socket['xy'][1] - y0, 2)
            self.assertLessEqual(socket['xy'][1] - y0, 6)
        self.assertAlmostEqual(right['xy'][0] - left['xy'][0], 15.24)
        self.assertEqual(left['xy'][1], right['xy'][1])
        nano_x = (left['xy'][0] + right['xy'][0]) / 2
        # 18 mm Nano body and 10 mm jack body must fit side-by-side at entry.
        self.assertGreaterEqual(nano_x - 9, x0)
        self.assertLessEqual(nano_x + 9, x1)
        self.assertGreaterEqual(jack['xy'][0] - 5, x0)
        self.assertLessEqual(jack['xy'][0] + 5, x1)
        self.assertGreaterEqual(abs(nano_x - jack['xy'][0]), 14 + 1)

    def test_exported_connectors_keep_placement_and_socket_pitch(self):
        """Catch a stale native board or an incompatible replacement footprint."""
        for ref in ('J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7'):
            with self.subTest(ref=ref):
                spec, fp = BY_REF[ref], self.footprints[ref]
                placement = list(map(float, child(fp, 'at')[1:]))
                self.assertEqual(tuple(placement[:2]), tuple(spec['xy']))
                angle = placement[2] if len(placement) == 3 else 0
                self.assertEqual(angle % 360, spec['rotation'] % 360)
        for ref in ('J2', 'J3'):
            pads = {p[1]: p for p in children(self.footprints[ref], 'pad')}
            self.assertEqual(set(pads), {str(n) for n in range(1, 16)})
            for n in range(1, 16):
                x, y = map(float, child(pads[str(n)], 'at')[1:3])
                self.assertEqual(x, 0)
                self.assertAlmostEqual(y, (n - 1) * 2.54)


class CircuitInvariants(unittest.TestCase):
    def test_nano_usb_end_orientation_and_power_pins(self):
        """Nano 33 IoT sockets must not accidentally use the legacy Nano 5 V pin."""
        left, right = BY_REF['J2'], BY_REF['J3']
        self.assertEqual(set(left['pins']), {str(n) for n in range(1, 16)})
        self.assertEqual(set(right['pins']), {str(n) for n in range(1, 16)})
        self.assertAlmostEqual(right['xy'][0] - left['xy'][0], 15.24)
        self.assertEqual(left['xy'][1], right['xy'][1])
        self.assertEqual((left['rotation'], right['rotation']), (0, 0))
        self.assertEqual(net('J2', 15), 'NANO_VIN')
        self.assertEqual(net('J2', 14), 'GND')
        self.assertEqual(net('J3', 12), 'GND')
        # Left pin 2 is 3V3; pin 12 is 5V/VUSB. Neither powers this carrier.
        self.assertIsNone(net('J2', 2))
        self.assertIsNone(net('J2', 12))
        self.assertEqual({pin for pin, name in left['pins'].items() if name}, {'14', '15'})
        self.assertEqual({pin for pin, name in right['pins'].items() if name}, {'7', '8', '10', '12'})

    def test_gpio_to_led_channels_preserves_colour_and_gate_drive(self):
        # Physical Nano right header: D3=pin10, D5=pin8, D6=pin7, USB end up.
        # UCC27524A: INA=2, OUTA=7; INB=4, OUTB=5. AOD4184A: G=1,D=2,S=3.
        channels = [
            ('R', 'RED', 10, 'U1', 2, 7, 'R1', 'R7', 'R4', 'R10', 'Q1'),
            ('G', 'GREEN', 8, 'U1', 4, 5, 'R2', 'R8', 'R5', 'R11', 'Q2'),
            ('B', 'BLUE', 7, 'U2', 2, 7, 'R3', 'R9', 'R6', 'R12', 'Q3'),
        ]
        for colour, drain, nano_pin, driver, inp, out, series, gate, pd_in, pd_gate, mosfet in channels:
            with self.subTest(colour=colour):
                gpio = net('J3', nano_pin)
                self.assertEqual(gpio, 'PWM_' + colour)
                self.assertEqual(net(series, 1), gpio)
                self.assertEqual(net(series, 2), net(driver, inp))
                self.assertNotEqual(net(series, 1), net(series, 2))
                self.assertEqual(net(gate, 1), net(driver, out))
                self.assertEqual(net(gate, 2), net(mosfet, 1))
                self.assertNotEqual(net(driver, out), net(driver, inp))
                self.assertEqual(net(pd_in, 1), net(driver, inp))
                self.assertEqual(net(pd_gate, 1), net(mosfet, 1))
                self.assertEqual(net(pd_in, 2), 'GND')
                self.assertEqual(net(pd_gate, 2), 'GND')
                self.assertEqual(net(mosfet, 2), drain)
                self.assertEqual(net(mosfet, 3), 'GND')
                self.assertEqual(BY_REF[mosfet]['mpn'], 'AOD4184A')

    def test_tolerant_driver_selection_and_unused_channel(self):
        # Substituting the earlier breadboard driver loses the VDD-independent
        # input-voltage guarantee needed while USB powers the Nano alone.
        for ref in ('U1', 'U2'):
            self.assertEqual(BY_REF[ref]['mpn'], 'UCC27524ADR')
            self.assertEqual(net(ref, 6), 'V9')
            self.assertEqual(net(ref, 3), 'GND')
            self.assertEqual(net(ref, 1), 'V9')  # Active channel A enabled.
        self.assertEqual(net('U1', 8), 'V9')    # Active channel B enabled.
        self.assertEqual(net('U2', 8), 'GND')   # Unused channel B disabled.
        self.assertEqual(net('U2', 4), 'GND')   # No floating unused input.
        self.assertIsNone(net('U2', 5))        # Output must not be shorted low.

    def test_usb_cannot_backfeed_control_supply_through_vin(self):
        # SS14 terminal 1 is cathode, 2 is anode. Current can flow from the
        # regulator to Nano VIN; the opposite direction meets the diode.
        self.assertEqual(net('U3', 3), 'V9')
        self.assertEqual(net('D3', 2), 'V9')
        self.assertEqual(net('D3', 1), net('J2', 15))
        self.assertNotEqual(net('D3', 1), net('D3', 2))
        self.assertEqual(members('NANO_VIN'), {('D3', '1'), ('J2', '15')})
        self.assertEqual({net('R14', 1), net('R14', 2)}, {'V9', 'GND'})

    def test_parallel_rgb_ports_have_separate_fused_positive_feeds(self):
        positive_feeds = set()
        for jack, fuse in [('J4', 'F2'), ('J5', 'F3'), ('J6', 'F4'), ('J7', 'F5')]:
            with self.subTest(jack=jack):
                # 6P4C has contacts 2..5, not the generic 1..4 header numbering.
                self.assertEqual(set(BY_REF[jack]['pins']), {'2', '3', '4', '5'})
                self.assertEqual(BY_REF[jack]['mpn'], '615004144121')
                self.assertEqual([net(jack, n) for n in (3, 4, 5)], ['RED', 'GREEN', 'BLUE'])
                self.assertEqual(net(fuse, 1), 'V12')
                self.assertEqual(net(fuse, 2), net(jack, 2))
                self.assertEqual(members(net(jack, 2)), {(fuse, '2'), (jack, '2')})
                positive_feeds.add(net(jack, 2))
        self.assertEqual(positive_feeds, {'PORT1_12V', 'PORT2_12V', 'PORT3_12V', 'PORT4_12V'})

    def test_full_strip_in_four_equal_sections_stays_within_contact_rating(self):
        # The +12 V contact carries all three colour currents at full white.
        # These are the specified load and manufacturer's connector rating,
        # independent of the component-placement or schematic loops.
        length_m = 160 * 0.0254
        total_current_a = length_m * 14.4 / 12
        ports = [p for p in PARTS if p['mpn'] == '615004144121']
        self.assertEqual({p['ref'] for p in ports}, {'J4', 'J5', 'J6', 'J7'})
        self.assertEqual(OUTPUT_COUNT, len(ports))
        self.assertAlmostEqual(STRIP_LENGTH_M, length_m)
        self.assertEqual((STRIP_W_PER_M, SUPPLY_V, CONNECTOR_RATING_A), (14.4, 12, 1.5))
        self.assertAlmostEqual(length_m / len(ports), 1.016)
        self.assertAlmostEqual(total_current_a / len(ports), 1.2192)
        self.assertLess(total_current_a / len(ports), 1.5)

    def test_reverse_polarity_pfet_uses_drain_at_input_source_at_load(self):
        # AOD4185 pin 2/tab is drain, pin 3 is source. Reversing these defeats
        # the intended reverse-polarity block through its intrinsic diode.
        self.assertEqual(BY_REF['Q4']['mpn'], 'AOD4185')
        self.assertEqual(net('J1', 1), net('F1', 1))
        self.assertEqual(net('F1', 2), net('Q4', 2))
        self.assertEqual(net('Q4', 3), 'V12')
        self.assertEqual(net('J1', 2), 'GND')
        self.assertIsNone(net('J1', 'MP'))
        self.assertEqual(net('R13', 1), net('Q4', 1))
        self.assertEqual(net('R13', 2), 'GND')
        self.assertEqual(net('D1', 1), net('Q4', 3))  # Zener cathode at source.
        self.assertEqual(net('D1', 2), net('Q4', 1))

    def test_exported_schematic_has_exact_components_and_pin_connectivity(self):
        self.assertEqual(len(BY_REF), len(PARTS), 'Duplicate design reference')
        compare_netlist(ROOT / 'pcb.net', {p['ref']: p['pins'] for p in PARTS})


class NetlistValidationRegression(unittest.TestCase):
    """Mutate a small independent XML fixture to prove failures are detected."""
    expected = {'U1': {'1': 'V9', '2': None}, 'Q1': {'1': 'V9'}, 'H1': {}}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='kitchen-netlist-test-')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'circuit.net'
        self.xml = ET.fromstring('''<export>
          <components><comp ref="U1"/><comp ref="Q1"/><comp ref="H1"/></components>
          <nets>
            <net code="1" name="/V9"><node ref="U1" pin="1"/><node ref="Q1" pin="1"/></net>
            <net code="2" name="unconnected-(U1-Pad2)"><node ref="U1" pin="2"/></net>
          </nets>
        </export>''')

    def check(self):
        ET.ElementTree(self.xml).write(self.path, encoding='unicode')
        return compare_netlist(self.path, self.expected)

    def test_complete_netlist_accepts_explicit_no_connect(self):
        actual = self.check()
        self.assertEqual(actual['U1']['1'], 'V9')

    def test_missing_mechanical_component_is_rejected(self):
        components = self.xml.find('components')
        components.remove(components.find("comp[@ref='H1']"))
        with self.assertRaisesRegex(ValueError, 'Missing component: H1'):
            self.check()

    def test_unexpected_component_is_rejected(self):
        ET.SubElement(self.xml.find('components'), 'comp', ref='J9')
        with self.assertRaisesRegex(ValueError, 'Unexpected component: J9'):
            self.check()

    def test_duplicate_component_reference_is_rejected(self):
        ET.SubElement(self.xml.find('components'), 'comp', ref='U1')
        with self.assertRaisesRegex(ValueError, 'Duplicate component reference: U1'):
            self.check()

    def test_wrong_supply_connection_is_rejected(self):
        self.xml.find('./nets/net').set('name', '/GND')
        with self.assertRaisesRegex(ValueError, 'expected V9, got GND'):
            self.check()

    def test_spare_pin_short_to_supply_is_rejected(self):
        spare = self.xml.find("./nets/net[@code='2']")
        node = spare.find('node')
        spare.remove(node)
        self.xml.find('./nets/net').append(node)
        with self.assertRaisesRegex(ValueError, 'expected no connection, got V9'):
            self.check()

    def test_unexpected_pin_is_rejected(self):
        ET.SubElement(self.xml.find('./nets/net'), 'node', ref='Q1', pin='9')
        with self.assertRaisesRegex(ValueError, 'Unexpected pin: Q1.9'):
            self.check()

    def test_pin_assigned_to_two_nets_is_rejected(self):
        ET.SubElement(self.xml.find("./nets/net[@code='2']"), 'node', ref='Q1', pin='1')
        with self.assertRaisesRegex(ValueError, 'Duplicate netlist pin: Q1.1'):
            self.check()


if __name__ == '__main__':
    unittest.main()
