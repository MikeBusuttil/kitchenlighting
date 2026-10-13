# Kitchen lighting project

## materials
- Arduino Nano 33 IoT
- 160" strip of mosfet-driven 12V LEDs (14.4w/m)
- a 12v 6A PSU (center is positive, outer diameter is 5.5mm, inner 2.1mm)

## PCB

- Create the specs & draw the schematic for a PCB with all the best practice components already soldered on that can be submitted online for easy fabrication.  The PCB should expose:
  - a female header for allowing plug-in of the nano (however many pins that is)
  - 2 RJ-11 female jacks where the 4 primary conductors of the jack are connected to +12V, R, G, B
  - a 12v barrel jack

### files

- pcb.pdf
... whatever file(s) are needed for on-line submission

## breadboard

- All components should be connected to a 64-row breadboard (+,-,a-e,f-j,+,-, columns)
- When on, all connected LEDs should emit the same color & brightness
- rows 40-43 (a-e) will be where the spools of LED's connect:
  - 40: 12v
  - 41: G
  - 42: R
  - 43: B
- output 2 PDF with
  - a schematic exactly how it'll look with the Arduino connected to pins c1-c15 & g1-15 and USB port on top
  - a nicely rendered shopping list

### files

- min.pdf a minimal version that'll function
- best.pdf a best practice version
- breadboard.py 
- breadboard.csv
