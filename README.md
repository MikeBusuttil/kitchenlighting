# Kitchen lighting

Two breadboard proofs of concept using an Arduino Nano 33 IoT: a 12 V analog RGB strip and a 5 V APA102 strip. Each folder has its own spec, shopping list, standalone generator, and one generated SVG diagram.

## Getting started

```bash
python3 12v/build_12v.py
python3 5v/build_5v.py
```

## Project files

| Design | Spec | Shopping list | Diagram | Generator |
| --- | --- | --- | --- | --- |
| 12 V RGB | [12 V spec](12v/12v%20spec.md) | [12 V shopping CSV](12v/kitchen-lighting-12v-shopping.csv) | [12 V SVG](12v/kitchen-lighting-12v-breadboard.svg) | [build_12v.py](12v/build_12v.py) |
| 5 V APA102 | [5 V spec](5v/5v%20spec.md) | [5 V shopping CSV](5v/kitchen-lighting-5v-shopping.csv) | [5 V SVG](5v/kitchen-lighting-5v-breadboard.svg) | [build_5v.py](5v/build_5v.py) |
