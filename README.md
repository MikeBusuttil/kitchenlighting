# Kitchen lighting

## Getting started

```bash
python3 12v/build.py
python3 5v/build.py
```

## Project files

| Design     | Spec                   | Shopping list                    | Best practice            | Minimum                |
| ---------- | ---------------------- | -------------------------------- | ------------------------ | ---------------------- |
| 12 V RGB   | [spec.md](12v/spec.md) | [shopping.csv](12v/shopping.csv) | [best.svg](12v/best.svg) | [min.svg](12v/min.svg) |
| 5 V APA102 | [spec.md](5v/spec.md)  | [shopping.csv](5v/shopping.csv)  | [best.svg](5v/best.svg)  | [min.svg](5v/min.svg)  |

Each `build.py` generates both SVGs using only the Python standard library. Assembly notes and part references are in the specs; component names and values are labelled directly on the diagrams.

## Contributing

- markdown tables: `|`s should line up
- diagram labelling:
  - label directly (avoid using a legend)
  - avoid redundancy (ie. explaining a connection that the diagram clearly displays)
