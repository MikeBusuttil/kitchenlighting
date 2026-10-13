"""Reference placement for the compact revision C carrier.

Offsets are in board axes, relative to each fitted footprint's origin. All
references remain visible on the front silkscreen. The dense Nano area uses
the space between pads or beside each component. The assembly PDF displays
only the footprint's own fabrication reference, inside its body outline.
"""
import pcbnew as pcb


REFERENCE_OFFSETS = {
    'J1': (2.25, 2.25), 'J2': (0, -2.95), 'J3': (0, -2.95),
    'J4': (0, -11.4), 'J5': (0, -11.4),
    'J6': (0, -11.4), 'J7': (0, -11.4),
    'H1': (0, -3.75), 'H2': (0, 3.75),
    'H3': (0, -3.75), 'H4': (0, -3.75),
    'F1': (2.5, 0), 'F2': (2.5, -.25), 'F3': (4, .75),
    'F4': (2.5, -1.25), 'F5': (4, 0),
    'Q1': (.5, -4.5), 'Q2': (2, -4.5),
    'Q3': (4.25, -4.25), 'Q4': (3, 4.5),
    'U1': (0, -1.5), 'U2': (0, -1.5), 'U3': (0, -4.5),
    'C1': (-4.5, 0), 'C2': (-2.5, -1.25), 'C3': (-3.2, 0),
    'C4': (-.5, 2.5), 'C5': (-1.75, -1.25), 'C6': (-2.25, .25),
    'C7': (-1.75, -1.25), 'C8': (-2.25, .25),
    'D1': (-.75, -2), 'D2': (2.5, -3.25), 'D3': (0, -2.75),
    'D4': (0, -4.25), 'D5': (0, -2.25), 'D6': (0, -2.25),
    'R1': (-2.5, 0), 'R2': (0, -1.65), 'R3': (-2.5, 0),
    'R4': (-2.5, 0), 'R5': (-2.5, 0), 'R6': (-2.5, 0),
    'R7': (1.75, 0), 'R8': (-2.5, 0), 'R9': (-2.5, 1),
    'R10': (1.75, 0), 'R11': (-1.65, 0), 'R12': (-.25, -1.75),
    'R13': (1.75, 0), 'R14': (-1.65, 0),
}


def apply_labels(board):
    """Apply the DRC-checked label positions without moving any footprint."""
    for footprint in board.GetFootprints():
        dx, dy = REFERENCE_OFFSETS[footprint.GetReference()]
        reference = footprint.Reference()
        reference.SetPosition(footprint.GetPosition() + pcb.VECTOR2I(
            pcb.FromMM(dx), pcb.FromMM(dy)))
        reference.SetLayer(pcb.F_SilkS)
        reference.SetTextSize(pcb.VECTOR2I(pcb.FromMM(.8), pcb.FromMM(.8)))
        reference.SetTextThickness(pcb.FromMM(.12))
        # KiCad combines this local angle with the footprint's orientation.
        reference.SetTextAngle(pcb.EDA_ANGLE(0, pcb.DEGREES_T))
        reference.SetMirrored(False)
        reference.SetVisible(True)
