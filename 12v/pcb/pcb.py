#!/usr/bin/env python3
"""Build/check/package the 12 V RGB carrier using KiCad 7's Python/CLI tools.

Default: export the editable, committed board. --rebuild regenerates it from
pcb_design.py and pcb-routes.json. --place writes an unrouted development board.
The router is optional development tooling, never a fabrication dependency.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

os.environ.setdefault('KICAD7_FOOTPRINT_DIR', '/usr/share/kicad/footprints')
import pcbnew as pcb

from pcb_design import (BOARD, BY_REF, NETS, PARTS, ROOT, OUTPUT_COUNT,
                        STRIP_LENGTH_M, STRIP_W_PER_M, SUPPLY_V, CONNECTOR_RATING_A, ANTENNA_KEEPOUT)

STEM = ROOT / 'pcb'
ROUTES = ROOT / 'pcb-routes.json'


def mm(value):
    return pcb.FromMM(value)


def point(xy):
    return pcb.VECTOR2I(mm(xy[0]), mm(xy[1]))


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def text(board, value, xy, size=1.0, layer=pcb.F_SilkS):
    item = pcb.PCB_TEXT(board)
    item.SetText(value)
    item.SetPosition(point(xy))
    item.SetTextSize(point((size, size)))
    item.SetTextThickness(mm(size * .15))
    item.SetLayer(layer)
    item.SetMirrored(layer == pcb.B_SilkS)
    board.Add(item)


def board_dimensions(board):
    """Overall dimensions on the assembly drawing's non-fabrication layer."""
    x0, y0, x1, y1 = BOARD
    for start, end, length in (
        ((x0, y0), (x1, y0), x1-x0),
        ((x1, y0), (x1, y1), y1-y0),
    ):
        item = pcb.PCB_DIM_ALIGNED(board, pcb.PCB_DIM_ALIGNED_T)
        item.SetLayer(pcb.Cmts_User)
        item.SetStart(point(start))
        item.SetEnd(point(end))
        item.SetHeight(mm(-8))
        item.SetUnitsMode(pcb.DIM_UNITS_MODE_MILLIMETRES)
        item.SetUnitsFormat(pcb.DIM_UNITS_FORMAT_BARE_SUFFIX)
        item.SetPrecision(pcb.DIM_PRECISION_X_XX)
        item.SetSuppressZeroes(True)
        item.SetSuffix(f' ({length / 25.4:.2f} in)')
        item.SetTextSize(point((1.5, 1.5)))
        item.SetTextThickness(mm(.2))
        item.SetTextPositionMode(pcb.DIM_TEXT_POSITION_OUTSIDE)
        item.SetKeepTextAligned(True)
        item.SetLineThickness(mm(.2))
        item.SetArrowLength(mm(1.5))
        item.SetExtensionOffset(mm(1))
        item.SetExtensionHeight(mm(1.5))
        item.Update()
        board.Add(item)


def polygon(board, net, points, layer, *, keepout=False):
    zone = pcb.ZONE(board)
    zone.SetLayer(layer)
    if keepout:
        zone.SetIsRuleArea(True)
        zone.SetDoNotAllowTracks(True)
        zone.SetDoNotAllowVias(True)
        zone.SetDoNotAllowCopperPour(True)
        zone.SetDoNotAllowPads(True)
        zone.SetDoNotAllowFootprints(True)
    else:
        zone.SetNet(board.FindNet(net))
        zone.SetLocalClearance(mm(.30))
        zone.SetMinThickness(mm(.25))
        zone.SetPadConnection(pcb.ZONE_CONNECTION_FULL)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in points:
        outline.Append(mm(x), mm(y))
    board.Add(zone)
    return zone


def project():
    """Keep DRC rules and routing widths in the editable KiCad project."""
    default = dict(name='Default', clearance=.25, track_width=.3,
                   via_diameter=1.0, via_drill=.5, microvia_diameter=.3,
                   microvia_drill=.1, diff_pair_width=.25, diff_pair_gap=.25,
                   diff_pair_via_gap=.25, bus_width=12, wire_width=6)
    power = dict(default, name='Power', track_width=1.2,
                 via_diameter=1.8, via_drill=.9)
    power['nets'] = ['VIN_RAW', 'VIN_FUSED', 'V12', 'RED', 'GREEN', 'BLUE'] + [
        f'PORT{port}_12V' for port in range(1, OUTPUT_COUNT+1)]
    default['nets'] = [n for n in NETS if n not in power['nets']]
    data = {
        'meta': {'filename': 'pcb.kicad_pro', 'version': 1},
        'board': {'design_settings': {
            'rules': {'min_clearance': .25, 'min_track_width': .25,
                      'min_via_diameter': .8, 'min_through_hole_diameter': .3,
                      'min_via_annular_width': .2, 'min_copper_edge_clearance': .5,
                      'min_hole_clearance': .25, 'min_silk_clearance': .1,
                      'min_silk_text_height': .8, 'min_silk_text_thickness': .12},
            'defaults': {'board_outline_line_width': .05},
            'net_settings': {'classes': [default, power]},
        }},
        'net_settings': {'classes': [default, power], 'meta': {'version': 2}},
    }
    STEM.with_suffix('.kicad_pro').write_text(json.dumps(data, indent=2) + '\n')
    libraries = sorted({p['footprint'].split(':')[0] for p in PARTS})
    entries = []
    for name in libraries:
        uri = '${KIPRJMOD}/pcb.pretty' if name == 'pcb' else '${KICAD7_FOOTPRINT_DIR}/' + name + '.pretty'
        entries.append(f'  (lib (name "{name}")(type "KiCad")(uri "{uri}")(options "")(descr ""))')
    (ROOT / 'fp-lib-table').write_text('(fp_lib_table\n'+'\n'.join(entries)+'\n)\n')


def load_board():
    manager = pcb.GetSettingsManager()
    path = str(STEM.with_suffix('.kicad_pro'))
    manager.LoadProject(path)
    board = pcb.LoadBoard(str(STEM.with_suffix('.kicad_pcb')))
    board.SetProject(manager.GetProject(path))
    board.SynchronizeNetsAndNetClasses(False)
    return board


def set_stackup():
    """KiCad 7 does not expose the stackup descriptor through Python."""
    path = STEM.with_suffix('.kicad_pcb')
    source = path.read_text()
    if '(stackup' not in source:
        stackup = '''    (stackup
      (layer "F.SilkS" (type "Top Silk Screen") (color "White"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01) (color "Green"))
      (layer "F.Cu" (type "copper") (thickness 0.07))
      (layer "dielectric 1" (type "core") (thickness 1.44) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.07))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01) (color "Green"))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
      (copper_finish "ENIG")
      (dielectric_constraints no)
    )
'''
        path.write_text(source.replace('  (setup\n', '  (setup\n'+stackup, 1))


def place():
    project()
    board = pcb.BOARD()
    board.SetFileName(str(STEM.with_suffix('.kicad_pcb')))
    title = board.GetTitleBlock()
    title.SetTitle('12 V RGB carrier - top assembly / plug-in Nano 33 IoT')
    title.SetDate('2026-10-12')
    title.SetRevision('C')
    title.SetComment(0, f'{BOARD[2]-BOARD[0]:g} x {BOARD[3]-BOARD[1]:g} mm / FR4 1.6 mm / 2 oz both sides / ENIG')
    title.SetComment(1, 'All carrier parts fitted. Nano supplied separately. J4-J7: vertical RJ11, 1.5 A/contact.')
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(mm(1.6))
    ds.m_MinClearance = mm(.25)
    ds.m_CopperEdgeClearance = mm(.5)
    ds.m_TrackMinWidth = mm(.25)
    ds.m_ViasMinSize = mm(.8)
    ds.m_ViasMinAnnularWidth = mm(.2)
    ds.m_HoleClearance = mm(.25)
    ds.m_SolderMaskExpansion = mm(.05)
    ds.m_SolderMaskMinWidth = mm(.10)
    ds.m_SilkClearance = mm(.10)
    for i, name in enumerate(NETS, 1):
        board.Add(pcb.NETINFO_ITEM(board, name, i))
    libroot = Path(os.environ.get('KICAD_FOOTPRINT_DIR', '/usr/share/kicad/footprints'))
    for spec in PARTS:
        lib, name = spec['footprint'].split(':')
        folder = ROOT / 'pcb.pretty' if lib == 'pcb' else libroot / (lib + '.pretty')
        fp = pcb.FootprintLoad(str(folder), name)
        if fp is None:
            raise ValueError(f"Missing footprint: {spec['footprint']}")
        fp.SetReference(spec['ref'])
        fp.SetValue(spec['value'])
        fp.SetFPID(pcb.LIB_ID(lib, name))
        board.Add(fp)
        fp.SetPosition(point(spec['xy']))
        fp.SetOrientationDegrees(spec['rotation'])
        fp.Value().SetVisible(False)
        fp.Reference().SetTextSize(point((.9, .9)))
        fp.Reference().SetTextThickness(mm(.14))
        if spec['ref'].startswith('H'):
            dy = 4 if spec['xy'][1] < 100 else -4
            fp.Reference().SetPosition(point((spec['xy'][0], spec['xy'][1]+dy)))
        for pad in fp.Pads():
            n = pad.GetNumber()
            if n and n not in spec['pins']:
                raise ValueError(f"{spec['ref']}: unmapped pad {n}")
            net = spec['pins'].get(n)
            if net:
                pad.SetNet(board.FindNet(net))
        # Make source and tab connections solid: the power traces are short.
        if spec['ref'].startswith('Q') or spec['ref'] == 'U3':
            for pad in fp.Pads():
                pad.SetZoneConnection(pcb.ZONE_CONNECTION_FULL)
    x0, y0, x1, y1 = BOARD
    from pcb_labels import apply_labels
    apply_labels(board)
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        edge = pcb.PCB_SHAPE(board)
        edge.SetShape(pcb.SHAPE_T_SEGMENT)
        edge.SetStart(point(a))
        edge.SetEnd(point(b))
        edge.SetWidth(mm(.05))
        edge.SetLayer(pcb.Edge_Cuts)
        board.Add(edge)
    board_dimensions(board)
    # Both copper layers remain clear beneath and around the Nano antenna.
    ax0, ay0, ax1, ay1 = ANTENNA_KEEPOUT
    antenna = [(ax0,ay0),(ax1,ay0),(ax1,ay1),(ax0,ay1)]
    for layer in (pcb.F_Cu, pcb.B_Cu):
        polygon(board, None, antenna, layer, keepout=True)
    nano_x = (BY_REF['J2']['xy'][0] + BY_REF['J3']['xy'][0]) / 2
    text(board, 'USB ^', (nano_x, y0+1.5), 1.0)
    text(board, 'ANTENNA / NO COPPER', ((ax0+ax1)/2, (ay0+ay1)/2), .8)
    # Assembly details remain legible on the back with the Nano and jacks fitted.
    cx = (x0+x1)/2
    text(board, '12 V RGB / REV C', (cx,y0+50), 1.2, pcb.B_SilkS)
    text(board, f'{x1-x0:g} x {y1-y0:g} mm', (cx,y0+53), 1.0, pcb.B_SilkS)
    text(board, 'D3 RED  D5 GREEN  D6 BLUE', (cx,y0+56), .85, pcb.B_SilkS)
    text(board, '1.5 A / PORT - MAX 1.25 m', (cx,y0+59), .85, pcb.B_SilkS)
    text(board, '12 V DC / CENTRE +', (BY_REF['J1']['xy'][0],y0+10), .8, pcb.B_SilkS)
    for port in range(1, OUTPUT_COUNT+1):
        ref = f'J{port+3}'
        x, y = BY_REF[ref]['xy']
        text(board, f'{ref}  PORT {port}', (x,y+2), .8, pcb.B_SilkS)
        text(board, '+ R G B', (x,y+4), .9, pcb.B_SilkS)
    ds.SetAuxOrigin(point((x0, y1)))
    pcb.SaveBoard(str(STEM.with_suffix('.kicad_pcb')), board)
    set_stackup()
    manager = pcb.GetSettingsManager()
    manager.UnloadProject(manager.GetProject(str(STEM.with_suffix('.kicad_pro'))), False)
    project()  # SaveBoard on a new board writes default project settings.
    return load_board()


def track(board, net, points, width, layer):
    for a, b in zip(points, points[1:]):
        item = pcb.PCB_TRACK(board)
        item.SetStart(point(a))
        item.SetEnd(point(b))
        item.SetWidth(mm(width))
        item.SetLayer(layer)
        item.SetNet(board.FindNet(net))
        board.Add(item)


def via(board, net, xy, diameter=1.8, drill=.9):
    item = pcb.PCB_VIA(board)
    item.SetPosition(point(xy))
    item.SetWidth(mm(diameter))
    item.SetDrill(mm(drill))
    item.SetViaType(pcb.VIATYPE_THROUGH)
    item.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
    item.SetNet(board.FindNet(net))
    board.Add(item)


def pad_xy(board, ref, number):
    """Read the placed pad, including component rotation, for route seeds."""
    fp = next(fp for fp in board.GetFootprints() if fp.GetReference() == ref)
    pad = next(p for p in fp.Pads() if p.GetNumber() == str(number))
    return (pcb.ToMM(pad.GetPosition().x), pcb.ToMM(pad.GetPosition().y))


def power_trunks(board):
    """Seed the aggregate supply and local returns before signal routing."""
    track(board, 'VIN_RAW', [pad_xy(board,'J1',1),pad_xy(board,'F1',1)], 3.5, pcb.F_Cu)
    track(board, 'VIN_FUSED', [pad_xy(board,'F1',2),(80.3,69.855),(80.3,75)], 3.3, pcb.F_Cu)
    # Escape the PMOS source without touching its adjacent drain/gate leads.
    track(board, 'V12', [pad_xy(board,'Q4',3),(87.5,72.72)], 1.2, pcb.F_Cu)
    track(board, 'V12', [(87.5,72.5),(89.5,72.5),(89.5,74.5),(87.5,74.5),(87.5,72.5)], 2.0, pcb.F_Cu)
    for x in (87.5,89.5):
        for y in (72.5,74.5):
            via(board, 'V12', (x,y), 1.8,.9)
    # The main bus follows the right-hand control area, then runs beneath
    # the four branch fuses in the gap between the two RJ11 columns.
    track(board, 'V12', [(89.5,72.5),(89.5,90),(92,92.5),(92,110),(71,110),(71,143.545)], 3.0, pcb.B_Cu)
    for port in range(1, OUTPUT_COUNT+1):
        positive = pad_xy(board,f'F{port+1}',1)
        stitch = (68.2,positive[1])
        via(board, 'V12', stitch, 1.8,.9)
        track(board, 'V12', [stitch,positive], 2.0, pcb.F_Cu)
        track(board, 'V12', [stitch,(71,positive[1])], 2.0, pcb.B_Cu)
    for ref, stitch in [('C1',(90.5,82.05)),('D2',(88.5,88))]:
        via(board, 'V12', stitch, 1.8,.9)
        track(board, 'V12', [stitch,pad_xy(board,ref,1)], 2.0, pcb.F_Cu)
        track(board, 'V12', [stitch,(89.5,stitch[1])], 2.0, pcb.B_Cu)
    # The red drain exits between the last socket pad and antenna boundary.
    track(board, 'RED', [(65.46,88),(65.46,91.33),(74,91.33),(74,90.5)], 1.2, pcb.F_Cu)
    via(board, 'RED', (74,90.5), 1.8,.9)
    # Four source vias per channel, outside solder paste and the antenna area.
    source_arrays = {
        'Q1': [(58.2,91.3),(59.7,91.3),(61.2,91.3),(61.4,89.9)],
        'Q2': [(75.4,103.5),(77,103.5),(75.4,104.8),(77,104.8)],
        'Q3': [(87.4,103.5),(89,103.5),(87.4,104.8),(89,104.8)],
    }
    for ref, stitches in source_arrays.items():
        source = pad_xy(board,ref,3)
        for xy in stitches:
            via(board,'GND',xy,1.1,.5)
        if ref == 'Q1':
            track(board,'GND',[source,(59.16,91.3),(58.2,91.3),(61.2,91.3),(61.4,89.9)],1.2,pcb.F_Cu)
        else:
            track(board,'GND',[source,(source[0],103.5),(stitches[0][0],103.5),
                              (stitches[0][0],104.8),(stitches[1][0],104.8),(stitches[1][0],103.5)],1.2,pcb.F_Cu)
    # Regulator ground tab has four short thermal paths into the bottom plane.
    for xy in [(83.5,81),(85,81),(83.5,89),(85,89)]:
        via(board,'GND',xy,1.0,.5)
    # Connect the main bottom return directly to the jack's top ground plane.
    for xy in [(92,60),(94,60),(92,62),(94,62)]:
        via(board,'GND',xy,1.8,.9)
    driver_ground_stitches(board)


def driver_ground_stitches(board):
    """Give each driver and its bypass capacitor a local ground-plane return."""
    for idx in (1, 2):
        ref = f'U{idx}'
        gx, gy = pad_xy(board, ref, 3)
        angle = math.radians(BY_REF[ref]['rotation'])
        stitch = (gx-1.325*math.cos(angle), gy+1.325*math.sin(angle))
        via(board, 'GND', stitch, 1.0,.5)
        track(board, 'GND', [stitch,(gx,gy)], .3, pcb.F_Cu)
        cap = f'C{idx*2+3}'
        gx, gy = pad_xy(board, cap, 2)
        cx, cy = BY_REF[cap]['xy']
        d = math.hypot(gx-cx, gy-cy)
        stitch = (gx+1.3*(gx-cx)/d, gy+1.3*(gy-cy)/d)
        via(board, 'GND', stitch, 1.0,.5)
        track(board, 'GND', [stitch,(gx,gy)], .3, pcb.F_Cu)


def route_export(board):
    data = []
    for item in board.GetTracks():
        if isinstance(item, pcb.PCB_VIA):
            data.append(dict(type='via', net=item.GetNetname(),
                             xy=[pcb.ToMM(item.GetPosition().x), pcb.ToMM(item.GetPosition().y)],
                             diameter=pcb.ToMM(item.GetWidth()), drill=pcb.ToMM(item.GetDrillValue())))
        else:
            data.append(dict(type='track', net=item.GetNetname(), layer=board.GetLayerName(item.GetLayer()),
                             width=pcb.ToMM(item.GetWidth()),
                             points=[[pcb.ToMM(p.x), pcb.ToMM(p.y)] for p in [item.GetStart(), item.GetEnd()]]))
    ROUTES.write_text(json.dumps(data, indent=2) + '\n')


def route_import(board):
    for obj in json.loads(ROUTES.read_text()):
        if obj['type'] == 'track':
            track(board, obj['net'], obj['points'], obj['width'], board.GetLayerID(obj['layer']))
        else:
            via(board, obj['net'], obj['xy'], obj['diameter'], obj['drill'])


def import_ses(board, path):
    """Import standalone Specctra routing; KiCad 7's SES API requires the GUI.

    Fail on changed placement or unsupported geometry rather than interpreting
    an unknown session as a successful route. SES Y is the opposite of KiCad Y.
    """
    from pcb_schematic import parse, child, children
    data = parse(path.read_text())
    routes = child(data, 'routes')
    unit = child(routes, 'resolution')
    if unit[1] != 'um':
        raise ValueError('Only micrometre Specctra sessions are supported')
    scale = 1000 * float(unit[2])
    for comp in children(child(data,'placement'), 'component'):
        for pos in children(comp, 'place'):
            ref, x, y, side, rotation = pos[1:6]
            spec = BY_REF[ref]
            if (abs(float(x)/scale-spec['xy'][0]) > .001 or
                abs(-float(y)/scale-spec['xy'][1]) > .001 or side != 'front' or
                float(rotation) % 360 != spec['rotation'] % 360):
                raise ValueError(f'Session moved {ref}; regenerate routing')
    for item in list(board.GetTracks()):
        board.Remove(item)
    for net in children(child(routes, 'network_out'), 'net'):
        name = net[1]
        if name not in NETS:
            raise ValueError(f'Unknown session net: {name}')
        for element in net[2:]:
            if element[0] == 'wire':
                path_data = child(element, 'path')
                if path_data is None or path_data[1] not in ('F.Cu','B.Cu'):
                    raise ValueError('Unsupported routed wire geometry')
                coords = [float(v)/scale for v in path_data[3:]]
                points = [(coords[i], -coords[i+1]) for i in range(0,len(coords),2)]
                track(board, name, points, float(path_data[2])/scale, board.GetLayerID(path_data[1]))
            elif element[0] == 'via':
                match = re.fullmatch(r'Via\[0-1\]_(\d+):(\d+)_um', element[1])
                if not match:
                    raise ValueError(f'Unsupported via: {element[1]}')
                via(board, name, (float(element[2])/scale,-float(element[3])/scale),
                    int(match[1])/1000, int(match[2])/1000)
            else:
                raise ValueError(f'Unsupported SES element: {element[0]}')


def ground_planes(board):
    # Refillable, solid connections with both faces carrying the common return.
    for zone in list(board.Zones()):
        if not zone.GetIsRuleArea():
            board.Remove(zone)
    x0, y0, x1, y1 = BOARD
    for layer in (pcb.F_Cu, pcb.B_Cu):
        polygon(board, 'GND', [(x0+.5,y0+.5), (x1-.5,y0+.5),
                               (x1-.5,y1-.5), (x0+.5,y1-.5)], layer)
    board.BuildConnectivity()
    pcb.ZONE_FILLER(board).Fill(board.Zones())


def deterministic_zip(path, paths, base=ROOT):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths):
            info = zipfile.ZipInfo(str(p.relative_to(base)), date_time=(2026,10,12,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes())


def assembly_files(board):
    with (ROOT / 'pcb-bom.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Quantity', 'Value', 'Manufacturer Part Number', 'Footprint', 'Assembly', 'Notes'])
        grouped = {}
        for p in PARTS:
            if p['ref'].startswith('H'):
                continue
            key = (p['mpn'], p['value'], p['footprint'], p['note'])
            grouped.setdefault(key, []).append(p['ref'])
        for (mpn, val, fp, note), refs in grouped.items():
            w.writerow([','.join(refs), len(refs), val, mpn, fp,
                        'THT factory solder' if refs[0].startswith('J') else 'Top SMT', note])
    # All positions include THT for turnkey assemblers. Coordinates use the
    # lower-left board origin and mathematical +Y, rotations are KiCad native.
    with (ROOT / 'pcb-positions.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X (mm)', 'Mid Y (mm)', 'Layer', 'Rotation', 'Technology'])
        origin = board.GetDesignSettings().GetAuxOrigin()
        for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
            if fp.GetReference().startswith('H'):
                continue
            p = fp.GetPosition()
            w.writerow([fp.GetReference(), f'{pcb.ToMM(p.x-origin.x):.4f}',
                        f'{pcb.ToMM(origin.y-p.y):.4f}', 'Top', f'{fp.GetOrientationDegrees():.1f}',
                        'THT' if fp.GetReference().startswith('J') else 'SMD'])


def check_board(board):
    edge_points = [p for item in board.GetDrawings() if item.GetLayer() == pcb.Edge_Cuts
                   for p in (item.GetStart(), item.GetEnd())]
    if not edge_points:
        raise ValueError('Board has no fabrication outline')
    bounds = (min(p.x for p in edge_points), min(p.y for p in edge_points),
              max(p.x for p in edge_points), max(p.y for p in edge_points))
    if bounds != tuple(mm(v) for v in BOARD):
        raise ValueError('Board outline differs from pcb_design.py; update the design before exporting')
    if bounds[2]-bounds[0] > mm(50.8) or bounds[3]-bounds[1] > mm(101.6):
        raise ValueError('Board exceeds the 2 inch width / 4 inch length limits')
    jack = next(fp for fp in board.GetFootprints() if fp.GetReference() == 'J1')
    if abs(jack.GetOrientationDegrees() % 360 - 180) > .01 or abs(jack.GetPosition().y-mm(12)-bounds[1]) > mm(1):
        raise ValueError('Barrel jack must face outward at the Nano USB edge')
    refs = [fp.GetReference() for fp in board.GetFootprints()]
    if len(refs) != len(set(refs)) or set(refs) != set(BY_REF):
        raise ValueError('Board footprints must match the circuit component list exactly')
    actual = {}
    for fp in board.GetFootprints():
        spec = BY_REF[fp.GetReference()]
        if fp.GetValue() != spec['value'] or fp.GetFPID().GetLibItemName() != spec['footprint'].split(':')[1]:
            raise ValueError(f"{fp.GetReference()}: update pcb_design.py to match the edited value/footprint before exporting the BOM")
        for pad in fp.Pads():
            key = (fp.GetReference(), pad.GetNumber())
            if pad.GetNumber():
                value = pad.GetNetname() or None
                if key in actual and actual[key] != value:
                    raise ValueError(f'Inconsistent multi-pad net: {key}')
                actual[key] = value
    expected = {(p['ref'], n): v for p in PARTS for n, v in p['pins'].items()}
    if actual != expected:
        raise ValueError(f'Board/netlist mismatch: {set(actual.items()) ^ set(expected.items())}')
    pcb.WriteDRCReport(board, str(ROOT / 'pcb-drc.txt'), pcb.EDA_UNITS_MILLIMETRES, True)
    drc = (ROOT / 'pcb-drc.txt').read_text()
    issues = re.findall(r'^\*\* Found (\d+) (.+?) \*\*', drc, re.M)
    counts = {name: int(count) for count, name in issues}
    if not counts:
        raise ValueError('No parsed DRC summary; cannot declare this board validated')
    return counts


def exports(board, rebuild=False):
    from pcb_schematic import Schematic, build_schematic, compare_netlist
    from browser_exports import export_browser_views
    review_pdfs = [ROOT / 'pcb.pdf', ROOT / 'pcb-layout.pdf']
    if rebuild:
        build_schematic(STEM.with_suffix('.kicad_sch'))
    else:
        outputs = Schematic.export(STEM.with_suffix('.kicad_sch'))
        compare_netlist(outputs['netlist'], {p['ref']: p['pins'] for p in PARTS})
    if rebuild:
        ground_planes(board)
    else:
        board.BuildConnectivity()
        pcb.ZONE_FILLER(board).Fill(board.Zones())
    pcb.SaveBoard(str(STEM.with_suffix('.kicad_pcb')), board)
    counts = check_board(board)
    if any(counts.values()):
        raise ValueError(f'DRC must pass before fabrication export: {counts}; see pcb-drc.txt')
    assembly_files(board)
    with tempfile.TemporaryDirectory(prefix='kitchen-pcb-') as tmp:
        target = Path(tmp)
        run('kicad-cli', 'pcb', 'export', 'gerbers', '--output', str(target) + '/',
            '--layers', 'F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts',
            '--use-drill-file-origin',
            STEM.with_suffix('.kicad_pcb'))
        run('kicad-cli', 'pcb', 'export', 'drill', '--output', str(target) + '/',
            '--drill-origin', 'plot', '--excellon-separate-th', '--generate-map', '--map-format', 'pdf',
            STEM.with_suffix('.kicad_pcb'))
        # Keep the drill drawings available beside their browser companions,
        # as well as inside the fabrication archive.
        for drill_map in sorted(target.glob('*.pdf')):
            destination = ROOT / drill_map.name
            shutil.copyfile(drill_map, destination)
            review_pdfs.append(destination)
        deterministic_zip(ROOT / 'pcb-gerbers.zip', list(target.iterdir()), base=target)
    # Keep physical silkscreen references on the board. For the assembly PDF,
    # show the reference inside each fabrication outline and a component key.
    from pcb_layout import add_legend
    with tempfile.TemporaryDirectory(prefix='kitchen-layout-') as tmp:
        drawing = pcb.LoadBoard(str(STEM.with_suffix('.kicad_pcb')))
        for footprint in drawing.GetFootprints():
            footprint.Reference().SetVisible(False)
        add_legend(drawing)
        drawing_path = Path(tmp) / 'pcb.kicad_pcb'
        pcb.SaveBoard(str(drawing_path), drawing)
        run('kicad-cli', 'pcb', 'export', 'pdf', '--output', ROOT / 'pcb-layout.pdf',
            '--layers', 'F.Fab,F.SilkS,Edge.Cuts,Cmts.User', '--black-and-white',
            '--include-border-title', drawing_path)
    titles = {
        'pcb.pdf': '12 V RGB carrier — schematic',
        'pcb-layout.pdf': '12 V RGB carrier — assembly drawing',
        'pcb-PTH-drl_map.pdf': '12 V RGB carrier — plated drill map',
        'pcb-NPTH-drl_map.pdf': '12 V RGB carrier — non-plated drill map',
    }
    browser_files = []
    browser_documents = {}
    for pdf in review_pdfs:
        companions = export_browser_views(pdf, title=titles.get(pdf.name))
        browser_files.extend(companions)
        browser_documents[pdf.name] = [p.name for p in companions]
    full_strip_A = STRIP_LENGTH_M * STRIP_W_PER_M / SUPPLY_V
    checks = dict(kicad_version=pcb.Version(), parts=len(PARTS), nets=len(NETS),
                  board_pin_map='PASS', schematic_pin_map='PASS', drc=counts,
                  board_mm=[BOARD[2]-BOARD[0], BOARD[3]-BOARD[1]],
                  output_count=OUTPUT_COUNT, full_strip_A=full_strip_A,
                  equal_branch_length_m=STRIP_LENGTH_M / OUTPUT_COUNT,
                  equal_branch_A=full_strip_A / OUTPUT_COUNT,
                  connector_rating_A=CONNECTOR_RATING_A,
                  full_strip_within_connector_rating=(full_strip_A / OUTPUT_COUNT <= CONNECTOR_RATING_A),
                  browser_documents=browser_documents,
                  hardware_validation='NOT PERFORMED; prototype only')
    deliverables = [ROOT / name for name in [
        'pcb.kicad_pcb', 'pcb.kicad_sch', 'pcb.kicad_pro', 'pcb.net',
        'pcb-bom.csv', 'pcb-positions.csv', 'pcb-gerbers.zip',
        'pcb-notes.md', 'pcb-cost-estimate.md', 'pcb-drc.txt',
    ]] + review_pdfs + browser_files
    checks['sha256'] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in deliverables
    }
    (ROOT / 'pcb-checks.json').write_text(json.dumps(checks, indent=2) + '\n')
    files = [p for p in deliverables if p.suffix != '.net']
    files += [ROOT / 'pcb-checks.json', ROOT / 'fp-lib-table']
    files += list((ROOT / 'pcb.pretty').glob('*.kicad_mod'))
    deterministic_zip(ROOT / 'pcb-assembly.zip', files)
    print(f'PASS: {len(PARTS)} footprints; {len(NETS)} nets; {counts}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--place', action='store_true', help='write unrouted development board')
    parser.add_argument('--rebuild', action='store_true', help='rebuild from placement and saved routing')
    parser.add_argument('--save-routes', action='store_true', help='save tracks from edited board')
    parser.add_argument('--dsn', action='store_true', help='export Specctra development input')
    parser.add_argument('--import-ses', type=Path, help='import autorouter result')
    args = parser.parse_args()
    board = place() if args.place or args.rebuild else load_board()
    if args.place:
        power_trunks(board)
        pcb.SaveBoard(str(STEM.with_suffix('.kicad_pcb')), board)
    if args.rebuild:
        route_import(board)
    if args.import_ses:
        import_ses(board, args.import_ses)
    if args.save_routes:
        route_export(board)
    if args.import_ses:
        pcb.SaveBoard(str(STEM.with_suffix('.kicad_pcb')), board)
    if args.dsn:
        pcb.ExportSpecctraDSN(board, str(STEM.with_suffix('.dsn')))
    if not args.place and not args.dsn and not args.import_ses and not args.save_routes:
        exports(board, rebuild=args.rebuild)


if __name__ == '__main__':
    main()
