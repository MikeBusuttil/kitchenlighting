"""Single source of truth for the 12 V RGB carrier's fitted components/nets.

Coordinates are millimetres in KiCad's top view. J2/J3 pin 1 is at the USB end.
The Nano is supplied by the user; both 15-way female sockets are factory fitted.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BOARD = (50, 50, 100, 150)
# Nano body is elevated by the 8.51 mm sockets; low-profile parts fit beneath it.
NANO_BODY = (54.62, 49.3, 72.62, 94.3)
ANTENNA_KEEPOUT = (54, 92, 74, 102)
OUTPUT_COUNT = 4
STRIP_LENGTH_M = 4.064
STRIP_W_PER_M = 14.4
SUPPLY_V = 12
CONNECTOR_RATING_A = 1.5
PARTS = []


def add(ref, value, mpn, footprint, pins, xy, rotation=0, symbol=None, note=''):
    PARTS.append(dict(ref=ref, value=value, mpn=mpn, footprint=footprint,
                      pins={str(k): v for k, v in pins.items()}, xy=xy,
                      rotation=rotation, symbol=symbol, note=note))


R0805 = 'Resistor_SMD:R_0805_2012Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
DPAK = 'Package_TO_SOT_SMD:TO-252-3_TabPin2'
SO8 = 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'
FUSE = 'Fuse:Fuse_Littelfuse-NANO2-451_453'
SOCKET = 'pcb:Socket_Samtec_SSQ-115-01-G-S'

add('J1', '12 V IN / centre +', 'PJ-063AH',
    'Connector_BarrelJack:BarrelJack_CUI_PJ-063AH_Horizontal',
    {1: 'VIN_RAW', 2: 'GND', 'MP': None}, (86, 62.4), 180,
    symbol='Connector:Barrel_Jack', note='8 A jack; 5.5 x 2.1 mm mating plug; plated slots required')
left = [None, None, None, None, None, None, None, None, None, None,
        None, None, None, 'GND', 'NANO_VIN']
right = [None, None, None, None, None, None, 'PWM_B', 'PWM_G', None,
         'PWM_R', None, 'GND', None, None, None]
for ref, name, nets, x in [('J2', 'Nano left / USB up', left, 56),
                           ('J3', 'Nano right / USB up', right, 71.24)]:
    add(ref, name, 'SSQ-115-01-G-S', SOCKET,
        dict(enumerate(nets, 1)), (x, 54), symbol='Connector_Generic:Conn_01x15',
        note='2.54 mm pitch; two rows 15.24 mm apart; socket body height 8.51 mm')
for port, xy in enumerate([(60, 124), (82, 124), (60, 143), (82, 143)], 1):
    add(f'J{port+3}', 'RJ11 vertical / + R G B', '615004144121',
        'pcb:RJ11_Wuerth_615004144121',
        {2: f'PORT{port}_12V', 3: 'RED', 4: 'GREEN', 5: 'BLUE'}, xy,
        symbol='Connector_Generic:Conn_01x04',
        note='Top-entry 6P4C; 1.5 A/contact; 1.25 m maximum strip at 14.4 W/m, 12 V')

add('F1', '6.3 A / 125 V fast', '045106.3MRL', FUSE,
    {1: 'VIN_RAW', 2: 'VIN_FUSED'}, (85.5, 67.7), 270, symbol='Device:Fuse')
add('Q4', 'AOD4185 / reverse polarity', 'AOD4185', DPAK,
    {1: 'REV_GATE', 2: 'VIN_FUSED', 3: 'V12'}, (80, 75), 180, symbol='Device:Q_PMOS_GDS')
add('R13', '10k', 'RC0805FR-0710KL', R0805,
    {1: 'REV_GATE', 2: 'GND'}, (77, 65.4), 90, 'Device:R')
add('D1', '12 V gate clamp', 'BZT52C12-7-F', 'Diode_SMD:D_SOD-123',
    {1: 'V12', 2: 'REV_GATE'}, (76, 69), 0, 'Device:D_Zener')
add('D2', 'SMBJ15A', 'SMBJ15A', 'Diode_SMD:D_SMB',
    {1: 'V12', 2: 'GND'}, (93, 88), 0, 'Device:D_Zener')
add('C1', '470u / 35 V', 'EEHZL1V471P', 'Capacitor_SMD:CP_Elec_10x10.5',
    {1: 'V12', 2: 'GND'}, (93, 77.85), 90, 'Device:C_Polarized')
for port, y in enumerate([116, 126, 136, 146], 1):
    add(f'F{port+1}', '3.15 A / 125 V fast', '04513.15MRL', FUSE,
        {1: 'V12', 2: f'PORT{port}_12V'}, (71, y), 270, symbol='Device:Fuse',
        note='Short-circuit fuse; does NOT protect the 1.5 A RJ11 contact from overload')

add('U3', 'L78M09 / 9 V', 'L78M09CDT-TR', DPAK,
    {1: 'V12', 2: 'GND', 3: 'V9'}, (81, 85), symbol='Regulator_Linear:L7809')
add('C2', '330n / 50 V', 'GRM21BR71H334KA01L', C0805,
    {1: 'V12', 2: 'GND'}, (78, 80), 0, 'Device:C')
add('C3', '10u / 25 V', 'EEEFK1E100R', 'Capacitor_SMD:CP_Elec_4x5.8',
    {1: 'V9', 2: 'GND'}, (81, 92), 90, 'Device:C_Polarized')
add('C4', '100n / 50 V', 'GRM21BR71H104KA01L', C0805,
    {1: 'V9', 2: 'GND'}, (85.2, 91.6), 90, 'Device:C')
add('R14', '1k8 / minimum load', 'RC0805FR-071K8L', R0805,
    {1: 'V9', 2: 'GND'}, (76, 92), 90, 'Device:R')
add('D3', 'SS14 / USB isolation', 'SS14-E3/61T', 'Diode_SMD:D_SMA',
    {1: 'NANO_VIN', 2: 'V9'}, (93.3, 94), 0, 'Device:D_Schottky')

# Drivers and bypass parts are below the removable Nano, outside its antenna.
for idx, y in [(1, 66), (2, 77)]:
    pins = {1: 'V9', 2: 'IN_R' if idx == 1 else 'IN_B', 3: 'GND',
            4: 'IN_G' if idx == 1 else 'GND',
            5: 'DRIVE_G' if idx == 1 else None, 6: 'V9',
            7: 'DRIVE_R' if idx == 1 else 'DRIVE_B', 8: 'V9' if idx == 1 else 'GND'}
    add(f'U{idx}', 'UCC27524A', 'UCC27524ADR', SO8, pins, (62, y),
        note='Dual noninverting driver; input voltage independent of supply; used enables high, unused channel grounded')
    add(f'C{idx*2+3}', '100n / 50 V', 'GRM21BR71H104KA01L', C0805,
        {1: 'V9', 2: 'GND'}, (67.5, y-2), 90, 'Device:C')
    add(f'C{idx*2+4}', '4.7u / 50 V', 'GRM32ER71H475KA88L',
        'Capacitor_SMD:C_1210_3225Metric', {1: 'V9', 2: 'GND'},
        (67.5, y+3), 90, 'Device:C')

# Q1 also fits below the Nano; its low-profile body clears the sockets.
channel_positions = [
    (1, 'R', (64.2, 88), (62, 70.9), (62, 73.2), (52, 86), (52, 90), (63.62, 107)),
    (2, 'G', (81, 100), (62, 59.4), (62, 61.8), (76.8, 95), (73, 105), (81, 108)),
    (3, 'B', (93, 100), (62, 81.3), (62, 83.5), (88, 95), (88, 92), (93, 108)),
]
for idx, color, fet, rin, rpull, rgate, rgpull, clamp in channel_positions:
    drain = {'R': 'RED', 'G': 'GREEN', 'B': 'BLUE'}[color]
    add(f'Q{idx}', 'AOD4184A', 'AOD4184A', DPAK,
        {1: f'GATE_{color}', 2: drain, 3: 'GND'}, fet,
        symbol='Device:Q_NMOS_GDS')
    add(f'R{idx}', '1k', 'RC0805FR-071KL', R0805,
        {1: f'PWM_{color}', 2: f'IN_{color}'}, rin, 0, 'Device:R')
    add(f'R{idx+3}', '100k', 'RC0805FR-07100KL', R0805,
        {1: f'IN_{color}', 2: 'GND'}, rpull, 0, 'Device:R')
    add(f'R{idx+6}', '33R', 'RC0805FR-0733RL', R0805,
        {1: f'DRIVE_{color}', 2: f'GATE_{color}'}, rgate, 90 if idx == 1 else 0, 'Device:R')
    add(f'R{idx+9}', '100k', 'RC0805FR-07100KL', R0805,
        {1: f'GATE_{color}', 2: 'GND'}, rgpull, 90 if idx in (1, 2) else 0, 'Device:R')
    add(f'D{idx+3}', 'SS54 / cable clamp', 'SSC54-E3/57T', 'Diode_SMD:D_SMC',
        {1: 'V12', 2: drain}, clamp, 0, 'Device:D_Schottky')

# Holes avoid the Nano, connector bodies and the antenna clearance area.
for i, xy in enumerate([(54, 107), (96, 54), (96, 146), (96, 124)], 1):
    add(f'H{i}', 'M3 mounting', '', 'MountingHole:MountingHole_3.2mm_M3', {}, xy,
        symbol='Mechanical:MountingHole', note='Do not populate; non-plated 3.2 mm hole')

BY_REF = {p['ref']: p for p in PARTS}
NETS = sorted({net for p in PARTS for net in p['pins'].values() if net})
