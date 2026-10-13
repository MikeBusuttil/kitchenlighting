"""Small, deterministic native KiCad schematic writer.

Library graphics and electrical pin definitions come from the installed KiCad
symbol libraries.  The saved schematic embeds the symbols (including flattened
library inheritance), so recipients do not need the source libraries to edit it.
All dimensions are millimetres; component rotations use KiCad's convention.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import math
from pathlib import Path
import re
import subprocess
import uuid
import xml.etree.ElementTree as ET

LIBRARY_ROOT = Path('/usr/share/kicad/symbols')
NAMESPACE = uuid.UUID('8a83be72-c069-4c1c-a06b-877d0408f8a3')


class Atom(str):
    """An unquoted KiCad S-expression token."""


def form(name, *items):
    return [Atom(name), *items]


def number(value):
    return Atom(f'{value:.6f}'.rstrip('0').rstrip('.') if value else '0')


def at(x, y, rotation=0):
    return form('at', number(x), number(y), number(rotation))


def effects(size=1.27, *, hide=False, bold=False, justify=None):
    font = form('font', form('size', number(size), number(size)))
    if bold:
        font.append(Atom('bold'))
    result = form('effects', font)
    if justify:
        result.append(form('justify', Atom(justify)))
    if hide:
        result.append(Atom('hide'))
    return result


def parse(source):
    """Parse library syntax without third-party Python dependencies."""
    tokens = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', source)
    stack = []
    result = None
    for token in tokens:
        if token == '(':
            node = []
            if stack:
                stack[-1].append(node)
            stack.append(node)
        elif token == ')':
            result = stack.pop()
        elif token.startswith('"'):
            # KiCad strings use C-style escaped quotes, backslashes and newlines.
            value = re.sub(r'\\([\\"nrt])', lambda m: {
                '\\': '\\', '"': '"', 'n': '\n', 'r': '\r', 't': '\t'
            }[m[1]], token[1:-1])
            stack[-1].append(value)
        else:
            stack[-1].append(Atom(token))
    if stack or result is None:
        raise ValueError('Unbalanced KiCad S-expression')
    return result


def serialize(node, indent=0):
    if isinstance(node, Atom):
        return str(node)
    if isinstance(node, str):
        return '"' + node.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t') + '"'
    if not isinstance(node, list):
        raise TypeError(type(node))
    # Keep primitive and small geometry expressions legible and compact.
    compact = '(' + ' '.join(serialize(x, indent + 1) for x in node) + ')'
    if '\n' not in compact and len(compact) + indent * 2 < 110:
        return compact
    result = '(' + serialize(node[0], indent + 1)
    for item in node[1:]:
        if isinstance(item, list):
            result += '\n' + '  ' * (indent + 1) + serialize(item, indent + 1)
        else:
            result += ' ' + serialize(item, indent + 1)
    return result + ')'


def child(node, key, default=None):
    return next((item for item in node if isinstance(item, list) and item and item[0] == key), default)


def children(node, key):
    return [item for item in node if isinstance(item, list) and item and item[0] == key]


class SymbolLibrary:
    def __init__(self, root=LIBRARY_ROOT):
        self.root = Path(root)
        self.libraries = {}
        self.resolved = {}

    def load(self, lib_id):
        if lib_id in self.resolved:
            return copy.deepcopy(self.resolved[lib_id])
        library, name = lib_id.split(':', 1)
        if library not in self.libraries:
            source = parse((self.root / (library + '.kicad_sym')).read_text())
            self.libraries[library] = {item[1]: item for item in children(source, 'symbol')}
        source = copy.deepcopy(self.libraries[library][name])
        extends = child(source, 'extends')
        if extends:
            parent = self.load(f'{library}:{extends[1]}')
            override_keys = {item[0] for item in source[2:] if isinstance(item, list) and item[0] not in ('extends', 'property', 'symbol')}
            override_properties = {item[1] for item in children(source, 'property')}
            result = [Atom('symbol'), lib_id]
            for item in parent[2:]:
                if not isinstance(item, list):
                    result.append(item)
                elif item[0] == 'property' and item[1] not in override_properties:
                    result.append(item)
                elif item[0] not in ('property', *override_keys):
                    result.append(item)
            result.extend(item for item in source[2:] if not (isinstance(item, list) and item[0] == 'extends'))
        else:
            source[1] = lib_id
            result = source
        # Child symbol names must follow the derived symbol name, not its parent.
        for unit in children(result, 'symbol'):
            suffix = re.search(r'(_\d+_\d+)$', unit[1])
            if suffix:
                unit[1] = name + suffix[1]
        self.resolved[lib_id] = result
        return copy.deepcopy(result)


@dataclass
class Component:
    ref: str
    lib_id: str
    x: float
    y: float
    rotation: float
    mirror: str | None
    symbol: list
    unit: int = 1

    def pin(self, number):
        matches = []
        for unit in children(self.symbol, 'symbol'):
            suffix = re.search(r'_(\d+)_(\d+)$', unit[1])
            if suffix and int(suffix[1]) not in (0, self.unit):
                continue
            for pin in children(unit, 'pin'):
                if child(pin, 'number')[1] == str(number):
                    matches.append(pin)
        if not matches:
            raise KeyError(f'{self.ref} ({self.lib_id}) has no pin {number}')
        loc = child(matches[0], 'at')
        x, y = float(loc[1]), float(loc[2])
        angle = math.radians(self.rotation)
        screen_x = math.cos(angle) * x - math.sin(angle) * y
        screen_y = -(math.sin(angle) * x + math.cos(angle) * y)
        # KiCad mirrors the rotated instance in sheet coordinates.
        if self.mirror == 'x':
            screen_y = -screen_y
        elif self.mirror == 'y':
            screen_x = -screen_x
        return (round(self.x + screen_x, 6), round(self.y + screen_y, 6))

    @property
    def pins(self):
        return {child(pin, 'number')[1]: self.pin(child(pin, 'number')[1])
                for unit in children(self.symbol, 'symbol')
                for pin in children(unit, 'pin')}


class Schematic:
    def __init__(self, title, paper='A2', *, revision='1.0', date='2026-10-12', library_root=LIBRARY_ROOT):
        self.title = title
        self.uuid = self._uuid('sheet')
        self.paper = paper
        self.revision = revision
        self.date = date
        self.library = SymbolLibrary(library_root)
        self.symbols = {}
        self.components = {}
        self.items = []
        self._counter = 0

    def _uuid(self, name):
        return str(uuid.uuid5(NAMESPACE, self.title + '/' + name))

    def _item_uuid(self, kind):
        self._counter += 1
        return form('uuid', self._uuid(f'{kind}/{self._counter}'))

    def define_box(self, lib_id, width, height, pins, *, pin_length=5.08):
        """Embed a rectangular symbol with explicit electrical pins.

        Each pin is ``(number, name, side, offset, electrical_type)``.  Sides are
        left/right/top/bottom; offset is measured rightward/downward from the
        centre of the corresponding edge.  This supports parts absent from the
        installed libraries without substituting a different device's pinout.
        """
        name = lib_id.split(':', 1)[-1]
        body = form('symbol', name + '_0_1',
                    form('rectangle', form('start', number(-width / 2), number(height / 2)),
                         form('end', number(width / 2), number(-height / 2)),
                         form('stroke', form('width', number(0.254)), form('type', Atom('default'))),
                         form('fill', form('type', Atom('background')))))
        unit = form('symbol', name + '_1_1')
        for pin_number, pin_name, side, offset, electrical_type in pins:
            locations = {
                'left': (-width / 2 - pin_length, -offset, 0),
                'right': (width / 2 + pin_length, -offset, 180),
                'top': (offset, height / 2 + pin_length, 270),
                'bottom': (offset, -height / 2 - pin_length, 90),
            }
            unit.append(form('pin', Atom(electrical_type), Atom('line'), at(*locations[side]),
                             form('length', number(pin_length)),
                             form('name', pin_name, effects(1.0)),
                             form('number', str(pin_number), effects(1.0))))
        self.library.resolved[lib_id] = form('symbol', lib_id,
            form('pin_names', form('offset', number(0.508))),
            form('in_bom', Atom('yes')), form('on_board', Atom('yes')),
            form('property', 'Reference', 'U', at(0, height / 2 + 2.54), effects()),
            form('property', 'Value', name, at(0, -height / 2 - 2.54), effects()),
            body, unit)

    def add(self, ref, lib_id, value, footprint, x, y, rotation=0, mirror=None, *, fields=None,
            reference_at=None, value_at=None, unit=1, in_bom=True, on_board=True):
        if ref in self.components:
            raise ValueError(f'Duplicate reference {ref}')
        symbol = self.library.load(lib_id)
        self.symbols[lib_id] = symbol
        component = Component(ref, lib_id, x, y, rotation, mirror, symbol, unit)
        self.components[ref] = component
        instance = form('symbol', form('lib_id', lib_id), at(x, y, rotation), form('unit', Atom(str(unit))),
                        form('in_bom', Atom('yes' if in_bom else 'no')),
                        form('on_board', Atom('yes' if on_board else 'no')),
                        form('dnp', Atom('no')),
                        form('uuid', self._uuid(ref)))
        if mirror:
            if mirror not in ('x', 'y'):
                raise ValueError('mirror must be x or y')
            instance.append(form('mirror', Atom(mirror)))
        reference_at = reference_at or (x + 5.08, y - 2.54)
        value_at = value_at or (x + 5.08, y)
        instance.extend([
            form('property', 'Reference', ref, at(*reference_at, rotation % 180), effects(1.27, justify='left')),
            form('property', 'Value', value, at(*value_at, rotation % 180), effects(1.27, justify='left')),
            form('property', 'Footprint', footprint, at(x, y), effects(hide=True)),
        ])
        for key, value in (fields or {}).items():
            instance.append(form('property', key, str(value), at(x, y), effects(hide=True)))
        for pin_number in sorted(component.pins):
            instance.append(form('pin', pin_number, form('uuid', self._uuid(f'{ref}/pin/{pin_number}'))))
        self.items.append(instance)
        return component

    def wire(self, *points):
        if len(points) < 2:
            raise ValueError('A wire needs at least two points')
        for start, end in zip(points, points[1:]):
            if start == end:
                continue
            self.items.append(form('wire', form('pts', form('xy', *map(number, start)), form('xy', *map(number, end))),
                                   form('stroke', form('width', Atom('0')), form('type', Atom('default'))), self._item_uuid('wire')))

    def junction(self, x, y):
        self.items.append(form('junction', form('at', number(x), number(y)), form('diameter', Atom('0')),
                               form('color', Atom('0'), Atom('0'), Atom('0'), Atom('0')), self._item_uuid('junction')))

    def label(self, name, x, y, rotation=0, *, size=1.27):
        self.items.append(form('label', name, at(x, y, rotation), effects(size, justify='left'), self._item_uuid('label')))

    def text(self, text, x, y, *, size=1.27, bold=False, justify='left', rotation=0):
        self.items.append(form('text', text, at(x, y, rotation), effects(size, bold=bold, justify=justify), self._item_uuid('text')))

    def no_connect(self, point):
        self.items.append(form('no_connect', form('at', *map(number, point)), self._item_uuid('no_connect')))

    def _split_wires(self):
        """KiCad's connectivity graph requires explicit endpoints at junctions."""
        wires = [item for item in self.items if item[0] == 'wire']
        points = set()
        for wire in wires:
            points.update((float(p[1]), float(p[2])) for p in child(wire, 'pts')[1:])
        for item in self.items:
            if item[0] in ('junction', 'label'):
                pos = child(item, 'at')
                points.add((float(pos[1]), float(pos[2])))
        for component in self.components.values():
            points.update(component.pins.values())
        for item in self.items:
            if item[0] != 'wire':
                yield item
                continue
            pts = child(item, 'pts')
            x1, y1 = map(float, pts[1][1:])
            x2, y2 = map(float, pts[2][1:])
            dx, dy = x2 - x1, y2 - y1
            length2 = dx * dx + dy * dy
            cuts = []
            for x, y in points:
                t = ((x - x1) * dx + (y - y1) * dy) / length2
                if -1e-8 <= t <= 1 + 1e-8 and abs((x - x1) * dy - (y - y1) * dx) < 1e-6:
                    cuts.append((t, x, y))
            cuts.sort()
            for index, (a, b) in enumerate(zip(cuts, cuts[1:])):
                if abs(a[0] - b[0]) < 1e-8:
                    continue
                segment = copy.deepcopy(item)
                child(segment, 'pts')[1:] = [form('xy', number(a[1]), number(a[2])),
                                             form('xy', number(b[1]), number(b[2]))]
                child(segment, 'uuid')[1] = self._uuid(child(item, 'uuid')[1] + f'/{index}')
                yield segment

    def save(self, path):
        path = Path(path)
        project = path.stem
        instances = []
        for item in self._split_wires():
            item = copy.deepcopy(item)
            if item[0] == 'symbol':
                ref = next(p[2] for p in children(item, 'property') if p[1] == 'Reference')
                item.append(form('instances', form('project', project,
                            form('path', '/' + self.uuid, form('reference', ref), form('unit', Atom('1'))))))
            instances.append(item)
        root = form('kicad_sch', form('version', Atom('20230121')), form('generator', Atom('eeschema')),
                    form('uuid', self.uuid), form('paper', self.paper),
                    form('title_block', form('title', self.title), form('date', self.date), form('rev', self.revision)),
                    form('lib_symbols', *[self.symbols[key] for key in sorted(self.symbols)]),
                    *instances,
                    form('sheet_instances', form('path', '/', form('page', '1'))))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialize(root) + '\n')
        return path

    @staticmethod
    def export(path, formats=('pdf', 'netlist')):
        path = Path(path)
        outputs = {}
        for format_name in formats:
            if format_name == 'netlist':
                output = path.with_suffix('.net')
                args = ['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', str(output), str(path)]
            elif format_name == 'pdf':
                output = path.with_suffix('.pdf')
                args = ['kicad-cli', 'sch', 'export', 'pdf', '-o', str(output), str(path)]
            else:
                raise ValueError(format_name)
            subprocess.run(args, check=True, capture_output=True, text=True)
            outputs[format_name] = output
        return outputs


def read_netlist(path):
    """Return {reference: {pin number: net name}} from a KiCad XML netlist."""
    result = {}
    for net in ET.parse(path).getroot().findall('./nets/net'):
        for node in net.findall('node'):
            result.setdefault(node.attrib['ref'], {})[node.attrib['pin']] = net.attrib['name'].lstrip('/')
    return result


def compare_netlist(path, expected):
    """Require an exact component bijection and matching electrical connectivity.

    ``expected`` maps reference to a mapping of pin-number strings to net names.
    A ``None`` value requires the pin to be absent or explicitly unconnected.
    """
    xml = ET.parse(path).getroot()
    component_refs = [item.attrib['ref'] for item in xml.findall('./components/comp')]
    actual = read_netlist(path)
    errors = []
    seen = set()
    for ref in component_refs:
        if ref in seen:
            errors.append(f'Duplicate component reference: {ref}')
        seen.add(ref)
    for ref in sorted(set(expected) - seen):
        errors.append(f'Missing component: {ref}')
    for ref in sorted(seen - set(expected)):
        errors.append(f'Unexpected component: {ref}')
    seen_pins = set()
    for node in xml.findall('./nets/net/node'):
        key = (node.attrib['ref'], node.attrib['pin'])
        if key in seen_pins:
            errors.append(f'Duplicate netlist pin: {key[0]}.{key[1]}')
        seen_pins.add(key)
        if key[0] not in expected or key[1] not in expected[key[0]]:
            errors.append(f'Unexpected pin: {key[0]}.{key[1]}')
    for ref, pins in expected.items():
        for pin, net in pins.items():
            got = actual.get(ref, {}).get(str(pin))
            if net is None:
                if got is not None and not got.startswith('unconnected-'):
                    errors.append(f'{ref}.{pin}: expected no connection, got {got}')
            elif got != net:
                errors.append(f'{ref}.{pin}: expected {net}, got {got}')
    if errors:
        raise ValueError('Schematic/PCB net mismatch:\n' + '\n'.join(errors))
    return actual


def build_schematic(path=None):
    """Draw the carrier circuit and prove it agrees with the PCB pin/net table."""
    from pcb_design import BOARD, BY_REF, PARTS, ROOT
    path = Path(path or ROOT / 'pcb.kicad_sch')
    s = Schematic('12 V RGB lighting carrier - Nano 33 IoT', revision='C')
    s.text('12 V RGB LIGHTING CARRIER', 20, 22, size=3.2, bold=True)
    s.text('Factory-fitted carrier components; plug-in Arduino Nano 33 IoT supplied separately', 20, 29, size=1.7)
    s.text('FOUR TOP-ENTRY RJ11 OUTPUTS', 365, 22, size=2.0, bold=True)
    s.text('160 in at 14.4 W/m = 4.88 A. Four equal sections = 1.22 A per port.\nEach section: 40 in / 1.016 m. Maximum per port: 1.5 A / 1.25 m.\nAll four ports share the same RGB colour and brightness.', 365, 32, size=1.5)

    left_names = ['D13 / SCK', '3V3', 'AREF', 'A0', 'A1', 'A2', 'A3', 'A4 / SDA',
                  'A5 / SCL', 'A6', 'A7', '5V / VUSB', 'RESET', 'GND', 'VIN']
    right_names = ['D12 / CIPO', 'D11 / COPI', 'D10', 'D9', 'D8', 'D7', 'D6 / PWM B',
                   'D5 / PWM G', 'D4', 'D3 / PWM R', 'D2', 'GND', 'RESET', 'RX', 'TX']
    for name, names, side in [('Nano_Left', left_names, 'left'), ('Nano_Right', right_names, 'right')]:
        s.define_box('Kitchen:' + name, 30.48, 81.28,
                     [(str(i), label, side, (i - 8) * 5.08, 'passive')
                      for i, label in enumerate(names, 1)])
    s.define_box('Kitchen:RJ11_6P4C', 25.4, 30.48,
                 [('2', '+12 V', 'top', 0, 'passive'),
                  ('3', 'R', 'left', -5.08, 'passive'),
                  ('4', 'G', 'left', 0, 'passive'),
                  ('5', 'B', 'left', 5.08, 'passive')])
    s.define_box('Kitchen:UCC27524A', 25.4, 35.56,
                 [('1', 'ENA', 'top', -5.08, 'input'),
                  ('2', 'INA', 'left', -10.16, 'input'),
                  ('3', 'GND', 'bottom', 0, 'power_in'),
                  ('4', 'INB', 'left', 10.16, 'input'),
                  ('5', 'OUTB', 'right', 10.16, 'output'),
                  ('6', 'VDD', 'top', 0, 'power_in'),
                  ('7', 'OUTA', 'right', -10.16, 'output'),
                  ('8', 'ENB', 'top', 5.08, 'input')])
    placed = {}

    def add(ref, x, y, rotation=0, *, symbol=None, reference_at=None, value_at=None):
        p = BY_REF[ref]
        placed[ref] = s.add(ref, symbol or p['symbol'], p['value'], p['footprint'], x, y, rotation,
                            fields={'MPN': p['mpn'], 'Assembly note': p['note']},
                            reference_at=reference_at, value_at=value_at,
                            in_bom=not ref.startswith('H'))
        return placed[ref]

    def pin(ref, num):
        return placed[ref].pin(num)

    def link(ref, num, *points):
        s.wire(pin(ref, num), *points)

    def join(x, y):
        s.junction(x, y)

    # Shared ground is a continuous, visible return conductor.
    ground_y = 365
    s.wire((20, ground_y), (470, ground_y))
    s.label('GND', 30, ground_y)
    s.text('COMMON RETURN', 445, ground_y + 5, size=1.3, bold=True)

    s.text('INPUT PROTECTION', 20, 46, size=1.8, bold=True)
    add('J1', 30, 65, reference_at=(20, 75), value_at=(20, 78))
    add('F1', 65, 62.46, 90, reference_at=(57, 53), value_at=(57, 56))
    add('Q4', 110, 65, 90, reference_at=(96, 53), value_at=(96, 56))
    add('R13', 110, 100, reference_at=(115, 98), value_at=(115, 101))
    add('D1', 130, 75, reference_at=(135, 71), value_at=(135, 74))
    add('C1', 155, 90, reference_at=(160, 87), value_at=(160, 90))
    add('D2', 180, 90, 270, symbol='Device:D_Zener', reference_at=(185, 87), value_at=(185, 90))
    s.wire(pin('J1', 1), pin('F1', 1))
    s.wire(pin('F1', 2), pin('Q4', 2))
    s.label('VIN_RAW', 40, 62.46)
    s.label('VIN_FUSED', 78, 62.46)
    s.wire(pin('Q4', 3), (215, 62.46))
    link('D1', 1, (126.19, 62.46)); join(126.19, 62.46)
    link('D1', 2, (138, 75), (138, 82), (110, 82), pin('Q4', 1))
    link('R13', 1, (110, 82)); join(110, 82)
    link('J1', 2, (40, 67.54), (40, 112), (200, 112))
    s.wire((40, 112), (20, 112), (20, ground_y)); join(40, 112)
    for ref in ('C1', 'D2'):
        x, _ = pin(ref, 1)
        link(ref, 1, (x, 62.46)); join(x, 62.46)
        x, _ = pin(ref, 2)
        link(ref, 2, (x, 112)); join(x, 112)
    link('R13', 2, (110, 112)); join(110, 112)
    # The protected 12 V supply runs above all output branches.
    s.wire((205, 62.46), (205, 105), (580, 105))
    join(205, 62.46)
    s.label('V12', 350, 105)

    s.text('9 V CONTROL SUPPLY / USB ISOLATION', 220, 46, size=1.8, bold=True)
    add('U3', 245, 62.46, reference_at=(232, 52), value_at=(232, 55))
    add('C2', 220, 90, reference_at=(225, 85), value_at=(225, 88))
    add('C3', 270, 90, reference_at=(275, 85), value_at=(275, 88))
    add('C4', 300, 90, reference_at=(305, 85), value_at=(305, 88))
    add('D3', 335, 62.46, 180, reference_at=(325, 52), value_at=(325, 55))
    add('R14', 325, 90, reference_at=(330, 85), value_at=(330, 88))
    s.wire((215, 62.46), pin('U3', 1))
    link('C2', 1, (220, 62.46)); join(220, 62.46)
    s.wire(pin('U3', 3), pin('D3', 2))
    for ref in ('C3', 'C4', 'R14'):
        x, _ = pin(ref, 1)
        link(ref, 1, (x, 62.46)); join(x, 62.46)
    s.wire((200, 112), (325, 112))
    for ref, num in [('U3', 2), ('C2', 2), ('C3', 2), ('C4', 2), ('R14', 2)]:
        x, _ = pin(ref, num)
        link(ref, num, (x, 112)); join(x, 112)
    s.wire((260, 62.46), (260, 135), (280, 135), (280, 315))
    join(260, 62.46)
    s.label('V9', 263, 135)
    link('D3', 1, (355, 62.46), (355, 145), (15, 145), (15, 255.56))
    s.label('NANO_VIN', 90, 145)
    s.text('Reverse polarity PMOS + input TVS; nominal 9 V rail feeds drivers.\nD3 prevents USB-powered Nano VIN from energising the control rail.', 20, 128, size=1.35)

    s.text('PLUG-IN NANO 33 IoT', 25, 165, size=1.8, bold=True)
    s.text('USB connector at this end', 40, 172, size=1.35)
    add('J2', 45, 220, symbol='Kitchen:Nano_Left', reference_at=(32, 177), value_at=(32, 267))
    add('J3', 105, 220, symbol='Kitchen:Nano_Right', reference_at=(92, 177), value_at=(92, 267))
    link('J2', 15, (15, 255.56))
    link('J2', 14, (20, 250.48)); join(20, 250.48)
    link('J3', 12, (135, 240.32), (135, ground_y)); join(135, ground_y)
    for ref in ('J2', 'J3'):
        for num, net in BY_REF[ref]['pins'].items():
            if net is None:
                s.no_connect(pin(ref, num))
    s.text('J2/J3: 15 ways each, 2.54 mm pitch\nSocket rows 15.24 mm apart on PCB.\nOnly D3, D5, D6, VIN and both GND\npins connect to the carrier.', 25, 290, size=1.35)

    s.text('3.3 V PWM INPUTS', 150, 165, size=1.8, bold=True)
    s.text('HIGH = light on', 150, 172, size=1.35)
    add('U1', 235, 220, symbol='Kitchen:UCC27524A', reference_at=(216, 179), value_at=(216, 182))
    add('U2', 235, 300, symbol='Kitchen:UCC27524A', reference_at=(216, 258), value_at=(216, 261))
    rows = [209.84, 230.16, 289.84]
    for idx, y in enumerate(rows, 1):
        add(f'R{idx}', 170, y, 90, reference_at=(162, y - 9), value_at=(162, y - 6))
    # Crossings without a junction dot are electrically separate in KiCad.
    link('J3', 10, (143, 230.16), (143, rows[0]), pin('R1', 1))
    link('J3', 8, (150, 220), (150, rows[1]), pin('R2', 1))
    link('J3', 7, (140, 214.92), (140, rows[2]), pin('R3', 1))
    for resistor, driver, inp, x, cy in [('R4', 'U1', 2, 180, 245),
                                       ('R5', 'U1', 4, 195, 260),
                                       ('R6', 'U2', 2, 200, 325)]:
        idx = int(resistor[1:]) - 3
        y = rows[idx - 1]
        s.wire(pin(f'R{idx}', 2), pin(driver, inp))
        add(resistor, x, cy, reference_at=(x + 5, cy - 2), value_at=(x + 5, cy + 1))
        link(resistor, 1, (x, y)); join(x, y)
        link(resistor, 2, (x, ground_y)); join(x, ground_y)
    for idx, name in enumerate(('PWM_R', 'PWM_G', 'PWM_B'), 1):
        s.label(name, 154, rows[idx - 1], size=1.0)
    for idx, name in enumerate(('IN_R', 'IN_G', 'IN_B'), 1):
        s.label(name, *pin(f'R{idx}', 2), size=1.0)
    # Driver supplies/enable pins and local capacitors are wired, not implied.
    for ref, rail_y in [('U1', 190), ('U2', 270)]:
        pins_high = [num for num in (1, 6, 8) if BY_REF[ref]['pins'][str(num)] == 'V9']
        xs = [pin(ref, num)[0] for num in pins_high]
        s.wire((min(xs), rail_y), (280, rail_y)); join(280, rail_y)
        for num in pins_high:
            x, _ = pin(ref, num)
            link(ref, num, (x, rail_y))
            if x != min(xs):
                join(x, rail_y)
    link('U1', 3, (215, 242.86), (215, ground_y)); join(215, ground_y)
    link('U2', 3, (235, ground_y)); join(235, ground_y)
    link('U2', 4, (215, 310.16)); join(215, 310.16)
    if BY_REF['U2']['pins']['8'] == 'GND':
        link('U2', 8, (240.08, 275), (255, 275), (255, ground_y)); join(255, ground_y)
    s.no_connect(pin('U2', 5))
    for refs, cy, rail_y in [(('C5', 'C6'), 250, 240), (('C7', 'C8'), 330, 315)]:
        for ref, x in zip(refs, (290, 320)):
            add(ref, x, cy, reference_at=(x + 5, cy - 2), value_at=(x + 5, cy + 1))
            link(ref, 1, (x, rail_y))
            if cy == 250:
                link(ref, 2, (x, 265))
            else:
                link(ref, 2, (x, ground_y)); join(x, ground_y)
        if cy == 250:
            s.wire((290, 265), (330, 265), (330, ground_y))
            join(320, 265); join(330, ground_y)
        s.wire((280, rail_y), (320, rail_y)); join(280, rail_y); join(290, rail_y)
    s.text('Input tolerance is independent of driver VDD.\nU2 channel B is disabled; OUTB is unconnected.', 220, 351, size=1.25)

    s.text('LOW-SIDE RGB SWITCHES', 345, 165, size=1.8, bold=True)
    s.wire((465, 105), (465, 290)); join(465, 105)
    s.wire((430, 214.92), (430, ground_y)); join(430, ground_y)
    drain_rows = []
    for idx, color, cy, driver, outpin in [(1, 'R', 209.84, 'U1', 7),
                                         (2, 'G', 270, 'U1', 5),
                                         (3, 'B', 330, 'U2', 7)]:
        add(f'Q{idx}', 390, cy, reference_at=(395, cy - 1), value_at=(395, cy + 2))
        add(f'R{idx+6}', 355, cy, 90, reference_at=(347, cy - 9), value_at=(347, cy - 6))
        add(f'R{idx+9}', 375, cy + 18, reference_at=(380, cy + 16), value_at=(380, cy + 19))
        ox, oy = pin(driver, outpin)
        if abs(oy - cy) < .01:
            s.wire((ox, oy), pin(f'R{idx+6}', 1))
        else:
            bend_x = 340 if idx == 2 else 345
            s.wire((ox, oy), (bend_x, oy), (bend_x, cy), pin(f'R{idx+6}', 1))
        s.wire(pin(f'R{idx+6}', 2), pin(f'Q{idx}', 1))
        link(f'R{idx+9}', 1, (375, cy)); join(375, cy)
        gy = cy + 25
        link(f'R{idx+9}', 2, (375, gy), (430, gy)); join(430, gy)
        link(f'Q{idx}', 3, (430, cy + 5.08))
        if idx != 1:
            join(430, cy + 5.08)
        dy = cy - 10.16
        drain_rows.append(dy)
        drain_net = {'R': 'RED', 'G': 'GREEN', 'B': 'BLUE'}[color]
        bus_x = {'R': 490, 'G': 500, 'B': 510}[color]
        link(f'Q{idx}', 2, (392.54, dy), (bus_x, dy))
        s.label(drain_net, 470, dy, size=1.1)
        clamp_y = cy - 25
        add(f'D{idx+3}', 450, clamp_y, 270, reference_at=(435, clamp_y - 9), value_at=(435, clamp_y - 6))
        link(f'D{idx+3}', 2, (450, dy)); join(450, dy)
        link(f'D{idx+3}', 1, (450, cy - 40), (465, cy - 40))
        if idx != 3:
            join(465, cy - 40)
        s.label(f'DRIVE_{color}', ox + 3, oy, size=1.0)
        s.label(f'GATE_{color}', 377, cy, size=1.0)

    s.text('FOUR PARALLEL RGB OUTPUTS', 490, 115, size=1.6, bold=True)
    ports = [('J4', 'F2', 160), ('J5', 'F3', 217),
             ('J6', 'F4', 274), ('J7', 'F5', 331)]
    for idx, (jack, fuse, cy) in enumerate(ports, 1):
        add(jack, 550, cy, symbol='Kitchen:RJ11_6P4C',
            reference_at=(539, cy + 17), value_at=(539, cy + 20))
        add(fuse, 550, cy - 31, reference_at=(555, cy - 33), value_at=(555, cy - 30))
        _, feed_y = pin(fuse, 1)
        link(fuse, 1, (580, feed_y))
        if idx < len(ports):
            join(580, feed_y)
        s.wire(pin(fuse, 2), pin(jack, 2))
        s.label(f'PORT{idx}_12V', *pin(fuse, 2), size=1.0)
    s.wire((580, 105), (580, pin('F5', 1)[1]))
    for bus_x, num, start_y in [(490, 3, drain_rows[0]), (500, 4, drain_rows[1]), (510, 5, drain_rows[2])]:
        branches = [(jack, pin(jack, num)[1]) for jack, _, _ in ports]
        ys = [start_y, *[y for _, y in branches]]
        s.wire((bus_x, min(ys)), (bus_x, max(ys)))
        for ref, y in branches:
            link(ref, num, (bus_x, y))
            if min(ys) < y < max(ys):
                join(bus_x, y)
        if min(ys) < start_y < max(ys):
            join(bus_x, start_y)
    s.text('J4-J7: Wuerth 615004144121, top entry.\n6 positions, contacts 2 (+12 V), 3 (R), 4 (G), 5 (B).\nPins 1 and 6 have no contacts.', 493, 361, size=1.25)

    # The holes appear in the source as real non-electrical PCB components.
    for idx, x in enumerate((30, 70, 110, 150), 1):
        add(f'H{idx}', x, 388, reference_at=(x + 5, 386), value_at=(x + 5, 389))
    s.text('ASSEMBLY / USE', 20, 377, size=1.5, bold=True)
    width, length = BOARD[2] - BOARD[0], BOARD[3] - BOARD[1]
    s.text(f'{width:g} x {length:g} mm carrier; all components factory fitted. Nano USB and barrel input face the same short edge.\nNano plugs into J2/J3 with USB toward pin 1. Input: regulated 12 V DC, centre positive, 5.5 x 2.1 mm.\nBranch fuses protect against short circuits; they do not enforce the 1.5 A connector limit.', 20, 403, size=1.35)

    # Name every drawn electrical net without replacing its actual wiring.
    named = {item[1] for item in s.items if item[0] == 'label'}
    for p in PARTS:
        if p['ref'] not in placed:
            raise ValueError(f'Schematic is missing {p["ref"]}')
        for num, net in p['pins'].items():
            if net and net not in named:
                s.label(net, *pin(p['ref'], num), size=1.0)
                named.add(net)
    s.save(path)
    outputs = s.export(path)
    compare_netlist(outputs['netlist'], {p['ref']: p['pins'] for p in PARTS})
    return outputs


if __name__ == '__main__':
    print(build_schematic())
