# Kitchen lighting project

## materials
- Arduino Nano 33 IoT
- 160" strip of mosfet-driven 12V LEDs (14.4w/m)
- a 12v 6A PSU (center is positive, outer diameter is 5.5mm, inner 2.1mm)

## PCB

- Create the specs & draw the schematic for a PCB with all the best practice components already soldered on that can be submitted online for easy fabrication.  The PCB should expose:
  - a female header for allowing plug-in of the nano (however many pins that is)
  - 4 RJ-11 female jacks (top-entry) where the 4 primary conductors of the jack are connected to +12V, R, G, B
  - the 12v barrel jack next to USB jack of the Nano coming out of the short side of the PCB
- the width of the board cannot exceed 2.3"
- the height of the board cannot exceed 4"

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

### sketch

Create a sketch (or whatever the file is called that gets uploaded to the Nano) for 12v/min that has 3 states toggled by the button on the nano.  It starts in:
1. full brightness state where RGB is all at full brightness, 
2. mood lighting where the color is softer and the brightness is toned down
3. trippy mode where the lights cycle through all colors of the rainbow (at some period ~5s for the whole rainbow) while the brightness cycles between full and off at some other period (~9s)
