# Kitchen lighting

## Getting started

```bash
sudo apt install kicad kicad-symbols kicad-footprints poppler-utils python3-venv

python3 12v/build.py
python3 5v/build.py
python3 12v/pcb/pcb.py
```

## Project files

| Design     | Spec                   | Shopping list                    | Best practice            | Minimum                |
| ---------- | ---------------------- | -------------------------------- | ------------------------ | ---------------------- |
| 12 V RGB   | [spec.md](12v/spec.md) | [shopping.csv](12v/shopping.csv) | [best.svg](12v/best.svg) | [min.svg](12v/min.svg) |
| 5 V APA102 | [spec.md](5v/spec.md)  | [shopping.csv](5v/shopping.csv)  | [best.svg](5v/best.svg)  | [min.svg](5v/min.svg)  |

## 12 V PCB

| Drawing                                          | PDF                                 | SVG                                 |
| ------------------------------------------------ | ----------------------------------- | ----------------------------------- |
| Schematic                                        | [PDF](12v/pcb/pcb.pdf)              | [SVG](12v/pcb/pcb.svg)              |
| Assembly layout, dimensions and component legend | [PDF](12v/pcb/pcb-layout.pdf)       | [SVG](12v/pcb/pcb-layout.svg)       |
| Plated drill map                                 | [PDF](12v/pcb/pcb-PTH-drl_map.pdf)  | [SVG](12v/pcb/pcb-PTH-drl_map.svg)  |
| Non-plated drill map                             | [PDF](12v/pcb/pcb-NPTH-drl_map.pdf) | [SVG](12v/pcb/pcb-NPTH-drl_map.svg) |

| File                                                 | Purpose                             |
| ---------------------------------------------------- | ----------------------------------- |
| [pcb-notes.md](12v/pcb/pcb-notes.md)                 | Design, ordering, wiring and checks |
| [pcb-cost-estimate.md](12v/pcb/pcb-cost-estimate.md) | Prototype budget in CAD             |
| [pcb.kicad_pro](12v/pcb/pcb.kicad_pro)               | Editable KiCad project              |
| [pcb-gerbers.zip](12v/pcb/pcb-gerbers.zip)           | PCB fabrication upload              |
| [pcb-assembly.zip](12v/pcb/pcb-assembly.zip)         | Complete assembly handoff           |
| [pcb-bom.csv](12v/pcb/pcb-bom.csv)                   | Fitted parts                        |
| [pcb-positions.csv](12v/pcb/pcb-positions.csv)       | Placement data                      |
| [pcb-checks.json](12v/pcb/pcb-checks.json)           | Generated verification results      |

```bash
python3 12v/pcb/pcb.py            # check and export the committed CAD
python3 12v/pcb/pcb.py --rebuild  # reconstruct CAD from the circuit and saved routing
python3 -m unittest discover -s 12v/pcb -p 'test_*.py'
python3 12v/pcb/browser_exports.py  # refresh browser versions of all repository PDFs
```

## Tests

```sh
python3 -m unittest test_breadboards
```

## Contributing

- markdown tables: `|`s should line up
- diagram preferences:
  - maximize readability:
    - shorter wires is better
  - avoid using a legend:
    - label components directly
    - draw all connections
  - avoid redundancy (ie. explaining a connection that the diagram clearly displays)
