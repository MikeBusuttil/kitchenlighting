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

## Power for the breadboard prototypes
- Minimum (`min.svg`): USB powers the Nano and a physically short 1-5-pixel LED section. Close the Nano 33 IoT's onboard VUSB solder jumper SJ1 to enable the 5V/VUSB header at c12. Connect a12 to L+12 and Nano GND a14 to L-14; bridge the left rail breaks at rows 31/34, then connect b43 to L+43 and b40 to L-40 for the LEDs. No separate power jack is used. Allow up to 0.30 A for the five pixels plus Nano current within the USB source/cable rating.
- Best practice (`best.svg`): an Adafruit 4090 USB-C breakout supplies 5 V to the Nano, LEDs, and buffer through VBUS and GND. Its two onboard 5.1 kohm CC resistors support a USB-C power source. Solder its included 8-pin breadboard header, then mount in b54-b61 with the connector facing left; GND b54 feeds R-54 through e54, and VBUS b55 feeds R+55 through e55. The other header pads remain unconnected externally. Connect Nano VIN c15 to the shared +5 V rail using a15 to L+15, and Nano GND c14 to the common ground rail using a14 to L-14. Keep the Nano's VUSB solder jumper SJ1 open and c12 unconnected. The USB-C input powers the complete prototype during normal operation; use the Nano's micro-USB cable only for programming. Reuse a suitable USB-C power cable.
- Both variants retain the strip input at a40-a43. Minimum uses direct 3.3 V data/clock; best practice uses the SN74AHCT125 level buffer and its resistors/capacitors. The complete 160-inch strip needs separate power distribution and injection rather than the breadboard or Nano USB path.

The Nano 33 IoT's [official pinout](https://docs.arduino.cc/resources/pinouts/ABX00027-full-pinout.pdf) specifies 5-21 V at VIN, so the best-practice layout uses VIN for its regulated 5 V USB-C supply.
