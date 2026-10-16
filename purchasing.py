"""DigiKey purchase lists for the four breadboard layouts.

Existing hardware and future full-strip components are excluded. The 12 V
minimum uses AO3400A MOSFETs and series gate resistors, plus two RJ11 outputs.
Its SIPK03-1 adapters (headers included) are ordered separately from the
manufacturer; see 12v/shopping.csv. Best retains its gate drivers, gate resistors,
pulldowns, bypass capacitors and optional C7. The 12 V resistor orders use economical
ten-piece quantities from shopping.csv. The 5 V minimum uses existing Nano USB
power; best adds a USB-C breakout to power the Nano, LEDs and buffer together.
"""

import csv
from pathlib import Path


# Quantity, DigiKey SKU (individual/cut tape), manufacturer part, references.
PURCHASE_LISTS = {
    "12v": {
        "min": (
            (3, "785-1000-1-ND", "AO3400A", "Q1 Q2 Q3"),
            (10, "CF14JT2K20CT-ND", "CF14JT2K20", "R1 R2 R3"),
            (1, "CP-102AH-ND", "PJ-102AH", "J0"),
            (2, "732-3172-ND", "615004144121", "J1 J2"),
        ),
        "best": (
            (3, "IRFZ44NPBF-ND", "IRFZ44NPBF", "Q1 Q2 Q3"),
            (2, "TC4427ACPA-ND", "TC4427ACPA", "U1 U2"),
            (10, "CF14JT100RCT-ND", "CF14JT100R", "R4 R5 R6"),
            (10, "CF14JT10K0CT-ND", "CF14JT10K0", "R1 R2 R3 R7 R8 R9"),
            (2, "BC1101CT-ND", "K104K15X7RF5TH5", "C3 C5"),
            (2, "10-ECE-A1EKS4R7BCT-ND", "ECE-A1EKS4R7B", "C4 C6"),
            (1, "10-ECA-1EM101BCT-ND", "ECA-1EM101B", "C7 (optional)"),
            (1, "CP-102AH-ND", "PJ-102AH", "J0"),
        ),
    },
    "5v": {
        "min": (),
        "best": (
            (1, "296-4655-5-ND", "SN74AHCT125N", "U1"),
            (2, "CF14JT33R0CT-ND", "CF14JT33R0", "R3 R4"),
            (2, "CF14JT10K0CT-ND", "CF14JT10K0", "R1 R2"),
            (1, "BC1101CT-ND", "K104K15X7RF5TH5", "C1"),
            (1, "P19631CT-ND", "EEU-FC1A102B", "C2"),
            (1, "1528-2873-ND", "4090", "J0 USB-C breakout (header included)"),
        ),
    },
}


def export_purchase_csvs(output_dir: Path) -> list[Path]:
    """Write min.csv and best.csv beside a design's build script."""
    output_dir = Path(output_dir)
    paths = []
    for variant, parts in PURCHASE_LISTS[output_dir.name].items():
        path = output_dir / f"{variant}.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow([
                "Quantity", "DigiKey Part Number", "Manufacturer Part Number",
                "Customer Reference",
            ])
            writer.writerows(parts)
        paths.append(path)
    return paths
