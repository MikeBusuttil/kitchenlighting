# Kitchen lighting project

## starting materials:
- Arduino Nano 33 IoT
- 160" strip of mosfet-driven 12V LEDs (14.4w/m)
- a 64-row breadboard (+,-,a-e,f-j,+,-, columns) & tons of connector cables
- a 12v 6A PSU (center is positive, outer diameter is 5.5mm, inner 2.1mm)

## Goals
- All components should be connected to the breadboard
- When on, all connected LEDs should emit the same color & brightness
- rows 40-43 (a-e) will be where the spools of LED's connect:
  - 40: 12v
  - 41: G
  - 42: R
  - 43: B
- draw a schematic exactly how it'll look with the Arduino connected to pins c1-c15 & g1-15 and USB port on top