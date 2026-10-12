# Kitchen lighting project

## starting materials:
- Arduino Nano 33 IoT
- 160" strip of APA102 LEDs; 12 LEDs per 20 cm (60 LEDs/m) (60 LEDs per meter)
- a 64-row breadboard (+,-,a-e,f-j,+,-, columns) & tons of connector cables
- a 5v PSU

## Constraints
- All components should be connected to the breadboard
- When on, all connected LEDs should emit the same color & brightness
- rows 40-43 (a-e) will be where the spools of LED's connect:
  - 40: GND
  - 41: CI (clock input; CO is at the output end)
  - 42: DI (data input; DO is at the output end)
  - 43: 5V
- draw a schematic exactly how it'll look with the Arduino connected to pins c1-c15 & g1-15 and USB port on top

## Schematics
- 2 variants:
  - 1 with the minimum number of components to get it to function
  - 1 that follows best practice
