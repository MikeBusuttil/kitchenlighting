# 12 V RGB PCB

This is a carrier for the user's Arduino Nano 33 IoT and common-anode, 12 V analogue RGB strip. All four RJ11 outputs share the three PWM channels; each positive supply has its own fuse. The factory fits every listed component, including the two female Nano sockets, barrel jack and four vertical RJ11 jacks; the user plugs in the Nano afterward. No fabrication or assembly order has been placed.

## Load and connector limits

The specified 160 in strip is 4.064 m. At 14.4 W/m it draws approximately **58.52 W / 4.877 A at full white**. Four equal 40 in / 1.016 m branches draw **1.219 A each**, before tolerances, leaving about 19% current margin below 1.5 A. The common positive contact carries the sum of the three colour currents. Cut the strip only at its marked cut points, and check the resulting length and current of each branch.

J4–J7 are Würth **615004144121**, vertical, 6-position/4-contact jacks rated **1.5 A per contact**. The jacks occupy two rows of two near the end opposite the power and USB connections. Plugs enter from above, perpendicular to the PCB. The four-way split brings the nominal full strip within the connector ratings; it does not increase the rating of any individual jack. The 3.15 A branch fuses provide fault protection and do not limit a branch to 1.5 A. This remains a prototype awaiting physical validation. [Würth drawing and electrical ratings](https://www.we-online.com/components/products/datasheet/615004144121.pdf)

At the nameplate strip power, 1.5 A corresponds to at most 1.25 m / 49.2 in per jack, with no margin for strip tolerance, cable loss or temperature. A smaller load gives useful margin. PWM dimming changes average current but retains high pulse current; a brightness percentage alone does not establish connector compliance. Measure each branch, and use mating plugs and cables with documented conductor/contact ratings. An ordinary telephone cable is not an assumed power cable.

## Interfaces and wiring

J1 faces the same short edge of the board as the Nano's USB port and accepts the existing **regulated 12 V, 6 A, centre-positive, 5.5 mm OD / 2.1 mm ID** supply plug. Its PJ-063AH receptacle has an 8 A rating; its nominal 2.0 mm centre pin mates with the 2.1 mm plug bore. The auxiliary circuit also consumes supply current. [Same Sky PJ-063AH drawing](https://www.sameskydevices.com/product/resource/pj-063ah.pdf)

PCB pads use six-position numbering; the four loaded contacts are 2/3/4/5. Older part-specific Würth drawings label those four contacts 1/2/3/4, while the current drawing shows the generic six-position pattern. Drawings viewed from the cable side and PCB side are mirrored. Check every cable with a continuity meter before attaching LEDs. This is a custom LED pinout, unsuitable for telephone equipment.

| RJ11 position | Connection                       |
| ------------- | -------------------------------- |
| 1             | No contact                       |
| 2             | Fused +12 V, separate per jack   |
| 3             | R: shared red switched return    |
| 4             | G: shared green switched return  |
| 5             | B: shared blue switched return   |
| 6             | No contact                       |

Keep the positive conductors of the four branches separate after F2–F5. Tying them together at the strip would parallel the fuses and defeat independent branch protection. Each branch connects its +12 V/R/G/B to the corresponding strip conductors; RGB terminals are switched returns, not logic signals or a permanent ground.

With the Nano component side facing up and its USB connector toward the board's USB marking, J2 is the left socket and J3 is the right socket. Both socket pin 1 positions are at the USB end. The sockets are 1×15, 2.54 mm pitch, with 15.24 mm between rows. Low-profile driver circuitry, Q1 and passives sit beneath the Nano, using the specified sockets' 8.51 mm nominal body height for clearance. The tall bulk capacitor sits outside the Nano's outline. Check the seated Nano's underside clearance before powering the assembly.

| Nano function | Socket position | PCB function        |
| ------------- | --------------- | ------------------- |
| VIN           | J2.15           | Diode-isolated 9 V  |
| GND           | J2.14, J3.12    | Common ground       |
| D3            | J3.10           | Red PWM             |
| D5            | J3.8            | Green PWM           |
| D6            | J3.7            | Blue PWM            |

Other Nano pins are unconnected on the carrier. The Nano's GPIO is 3.3 V; its VIN accepts 5–21 V. Leave the Nano's VUSB solder jumper in its original state. [Arduino pinout](https://content.arduino.cc/assets/Pinout-NANO33IoT_latest.pdf) The fitted Samtec SSQ-115-01-G-S sockets have short 2.64 mm solder tails; the similarly named `-03` version has much longer tails and is not the specified part. [Samtec socket family](https://www.samtec.com/products/ssq-115-01-g-s)

## Circuit and component choices

- F1 is **045106.3MRL**, 6.3 A; F2–F5 are **04513.15MRL**, 3.15 A. These are Littelfuse 451-series, 125 V, very-fast-acting 2410 fuses. They are replaceable only by soldering. Their ratings are not current limits; a supply that limits at 6 A may never open F1. Fault clearing depends on available current and the time/current curve. [Littelfuse datasheet](https://www.littelfuse.com/~/media/electronics/datasheets/fuses/littelfuse_fuse_451_453_datasheet.pdf.pdf)
- Q4 provides reverse-polarity protection: **AOD4185**, drain toward F1 and source toward V12. R13 pulls its gate toward ground through 10 kΩ; D1 is a 12 V gate/source zener, cathode toward the source. [AOD4185 datasheet](https://www.aosmd.com/sites/default/files/res/datasheets/AOD4185.pdf)
- D2, **SMBJ15A**, shunts positive transients from V12 to ground. Its specified peak clamp is 24.4 V, below the regulator's 35 V and MOSFETs' 40 V maximum input/drain ratings. It is not a sustained-overvoltage regulator, and no surge qualification has been performed. [Littelfuse SMBJ datasheet](https://m.littelfuse.com/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smbj_datasheet.pdf.pdf)
- C1 is **EEHZL1V471P**, 470 µF/35 V hybrid, 10 mm diameter × 10.2 mm nominal height. Its low ESR and ripple capacity suit the PWM supply node; verify ripple heating with the actual PSU and cable. The catalogue's 100 kHz ripple figure is not an unconditional low-frequency PWM rating. Use the standard `P` part: the `V` version has additional mounting terminals. [Panasonic part specifications](https://industrial.panasonic.com/ww/products/pt/hybrid-aluminum/models/EEHZL1V471P), [package drawings](https://industrial.panasonic.com/cdbs/www-data/pdf/RDD0000/ast-ind-303928.pdf)
- U3, **L78M09CDT-TR**, produces nominal 9 V for the drivers and Nano. C2 is 330 nF at its input; C3/C4 are 10 µF and 100 nF at its output. R14, 1.8 kΩ, supplies a minimum load with the Nano absent. ST recommends at least 330 nF input bypass; output capacitance improves transient response and is not required for stability. Reserve approximately 0.7 W of dissipation at a 200 mA auxiliary load. Its tab is ground. Low input voltage can reduce the 9 V output because this regulator needs approximately 2 V of headroom. [ST L78M datasheet](https://www.st.com/resource/en/datasheet/l78m.pdf)
- D3 feeds Nano VIN from V9 and blocks USB-derived VIN from feeding V9. **UCC27524ADR** drivers tolerate input signals while their supply is absent and hold their outputs low during undervoltage. Each driver has 100 nF plus 4.7 µF local bypass. GPIO inputs have 1 kΩ series resistors and 100 kΩ pulldowns. The unused driver input is grounded. [TI UCC27524A datasheet](https://www.ti.com/lit/ds/symlink/ucc27524a.pdf)
- Q1–Q3 are **AOD4184A** low-side switches, rated 40 V with specified on-resistance of at most 9.5 mΩ at 4.5 V gate drive. Each gate has 33 Ω series resistance and a 100 kΩ source pulldown. D4–D6 clamp cable-inductance spikes: anode at the respective RGB drain, cathode at V12. [MOSFET datasheet](https://www.aosmd.com/res/data_sheets/AOD4184A.pdf), [Vishay SSC54 diode datasheet](https://www.vishay.com/docs/88885/ssc53l.pdf)

Logic high turns a colour on. Firmware must start D3/D5/D6 low before enabling PWM. All four jacks necessarily show the same commanded colour and brightness. Hardware pulldowns keep the lights off while the Nano resets or is removed.

## Fabrication and assembly submission

Revision C is **50 × 100 mm (1.97 × 3.94 in), two copper layers, 2 oz copper on both sides, 1.6 mm FR-4, ENIG**, with solder mask and top silkscreen. It fits the 2 in width and 4 in length limits. The barrel jack and Nano USB port face the same 50 mm edge. J1 requires plated slots; mounting holes and connector locating holes are non-plated as specified by the drill files. Keep the RF exclusion area free of copper and added metal. u-blox recommends clearance around and beneath the NINA-W102 antenna; enclosure material and nearby cables also affect range. Validate Wi-Fi in the intended enclosure. [u-blox antenna integration guidance](https://content.u-blox.com/sites/default/files/NINA-W10_DataSheet_UBX-17065507.pdf)

The routed board uses a 3.5 mm VIN_RAW input trunk, a 3.3 mm VIN_FUSED trunk, a 3.0 mm shared V12 bus, 2.0 mm feeds to the branch fuses, and 1.2 mm RGB and fused-output tracks. Q4 has a short 1.2 mm source escape. Four additional 0.9 mm drilled ground vias near J1 connect the main bottom return directly to the input ground plane. Both copper layers contain filled ground planes; each RGB MOSFET source has four 0.5 mm drilled ground vias. The shared V12 bus runs on the bottom layer to the four centrally placed branch fuses, with four 0.9 mm drilled vias at the supply transition and one 0.9 mm drilled via per fuse feed. Each gate driver and its bypass network have two local ground vias. The Nano antenna exclusion area is free of copper on both layers. The native stackup specifies 0.07 mm copper per side. At the stated 4.877 A full-strip load, Q4's calculated conduction loss is about 0.36 W using its 15 mΩ maximum resistance at 10 V gate drive. With equally loaded colours, each RGB switch dissipates about 0.025 W using 9.5 mΩ. These are room-temperature conduction estimates, excluding switching losses, resistance increase with temperature, and connector losses. Routing checks and these calculations do not validate temperature rise; measure the assembled prototype as described below.

All PCB files are in `12v/pcb/`; the shared requirements remain in [`../spec.md`](../spec.md).

| Drawing                                    | Browser                       | PDF                         | SVG                         |
| ------------------------------------------ | ----------------------------- | --------------------------- | --------------------------- |
| Schematic                                  | [Open](pcb.html)              | [PDF](pcb.pdf)              | [SVG](pcb.svg)              |
| Placement, dimensions and component legend | [Open](pcb-layout.html)       | [PDF](pcb-layout.pdf)       | [SVG](pcb-layout.svg)       |
| Plated drill map                           | [Open](pcb-PTH-drl_map.html)  | [PDF](pcb-PTH-drl_map.pdf)  | [SVG](pcb-PTH-drl_map.svg)  |
| Non-plated drill map                       | [Open](pcb-NPTH-drl_map.html) | [PDF](pcb-NPTH-drl_map.pdf) | [SVG](pcb-NPTH-drl_map.svg) |

| File                                   | Purpose                                      |
| -------------------------------------- | -------------------------------------------- |
| [pcb.kicad_pcb](pcb.kicad_pcb)         | Native routed board                          |
| [pcb.kicad_sch](pcb.kicad_sch)         | Native schematic                             |
| [pcb.kicad_pro](pcb.kicad_pro)         | Project settings                             |
| [pcb-gerbers.zip](pcb-gerbers.zip)     | Copper, mask, legend, outline and drill data |
| [pcb-bom.csv](pcb-bom.csv)             | Fitted components and exact part numbers     |
| [pcb-positions.csv](pcb-positions.csv) | Component placement coordinates              |
| [pcb-assembly.zip](pcb-assembly.zip)   | Assembly handoff package                     |
| [pcb-checks.json](pcb-checks.json)     | Generated verification results               |
| [pcb-drc.txt](pcb-drc.txt)             | KiCad design-rule report                     |

Each HTML drawing can be opened directly in a browser and uses its companion SVG, with links to the PDF and SVG files. Keep those companion files together when copying a drawing. The browser drawings are regenerated with the PDFs and included in the assembly package.

To refresh only the browser versions of every repository PDF, run `.venv/bin/python 12v/pcb/browser_exports.py` from the repository root. This does not rerun KiCad or alter the source PDFs.

The placement PDF shows one reference per component, using the fabrication labels on the component outlines, and a legend of functions, values and key specifications. The nearby silkscreen references remain on the physical PCB so they can be read after components are fitted; the PDF hides those duplicate labels. The legend is added only to the drawing and does not appear on the manufactured board.

Submit the Gerber archive for PCB fabrication and the assembly package for a **fully populated mixed SMT/through-hole assembly quote**. Include J1–J7: barrel jack, both Nano sockets, and all four RJ11 jacks must be soldered by the assembler. H1–H4 are holes, not purchased components. The Nano, supply, LEDs and cables are user-supplied and excluded from assembly. An SMT-only quote does not meet this request. Specify manufacturer procurement or consigned parts where the assembler lacks stock; exact stock, price and automatic catalogue matching have not been guaranteed. See [the cost estimate](pcb-cost-estimate.md) for a dated CAD budget and its assumptions.

Have the assembler review polarity, pin 1, placement rotation, plated slots, and the custom RJ11 footprint against the drawings. Use the native CAD and assembly drawing to resolve coordinate conventions. Approve substitutions only after checking pinout, footprint, ratings and behaviour. CAD checks establish file consistency; they do not establish thermal performance or EMC compliance.

Gerbers, drill files and placement coordinates use the same lower-left board origin, in millimetres with positive Y upward. Placement coordinates are KiCad footprint origins; rotations are KiCad top-view angles. The assembler must apply its part-library pickup/rotation conventions, especially for the through-hole sockets whose origins are at pin 1. Leave clearance above the vertical RJ11 jacks for plugs, cable bend radius and latch release; the enclosure must allow plugs to be inserted and removed from above.

Revision C changes the board outline and component placement. Mounting-hole centres, relative to the lower-left fabrication origin, are H1 (4, 43), H2 (46, 96), H3 (46, 4), and H4 (46, 26) mm; they are not a symmetric corner pattern. Use the current drill files and assembly drawing when making an enclosure. The Nano's USB body projects approximately 0.7 mm beyond the top board edge; the barrel-jack mouth sits approximately 0.4 mm inside that edge. Allow clearance for both mating plugs. The vertical RJ11 jack body is 15.9 mm high before inserting a plug.

Follow the environment setup in the [root README](../../README.md#getting-started), then re-export committed CAD from the repository root with `.venv/bin/python 12v/pcb/pcb.py`. Reconstruct it from `pcb_design.py` and `pcb-routes.json` with `.venv/bin/python 12v/pcb/pcb.py --rebuild`; this overwrites regenerated CAD. Run the checks with `.venv/bin/python -m unittest discover -s 12v/pcb -p 'test_*.py'`. `--place` is a development option. The build requires KiCad, its symbol/footprint libraries, Poppler, and a Python interpreter with KiCad's `pcbnew` module. The documented uv environment uses `/usr/bin/python3` and `--system-site-packages` to make the system KiCad module available. Inspect the resulting reports before submitting regenerated files.

The validated toolchain is KiCad 7.0.11. Default export preserves schematic placement and board copper edits, refills existing zones, and verifies connections against `pcb_design.py`. Update that circuit definition when changing component values or footprints so the BOM remains consistent. The checks file records SHA-256 hashes of the generated deliverables. The build does not place an order or claim that a hardware prototype has passed testing.

## First-board checks

1. With everything disconnected, inspect polarity and soldering. Check the power rails for shorts and verify every jack contact, fuse and cable conductor against the schematic. Confirm socket orientation and row spacing before inserting the Nano.
2. Leave the Nano and LED cables out. Apply 12 V from a bench supply initially limited to approximately 100 mA. Verify V12, approximately 9 V at V9, and a diode drop less at NANO_VIN. Check all three MOSFET gates stay near ground. Unexpected current, heating or incorrect rails requires disconnecting power and investigating.
3. Remove 12 V, fit the Nano and power it by USB only. Confirm V9 and the LED supply remain unpowered. Program D3/D5/D6 low, then test USB plus 12 V and repeated power/reset sequences. The lights should remain off until commanded.
4. Start with a short, measured LED section well within 1.5 A per jack. Test red, green, blue, white and intermediate PWM duty cycles on each jack and together. Confirm all four branches follow the same commands and measure their currents separately. The intended full-strip arrangement is four approximately 1.016 m sections, with no branch exceeding 1.5 A at full white.
5. Check V9/Nano VIN during Wi-Fi activity and PWM transitions. Measure regulator, MOSFET, capacitor, jack and cable temperatures after reaching steady state. Check drain spikes and supply ripple with appropriate oscilloscope probing. Verify Wi-Fi with the final enclosure and cable placement. These are physical prototype checks; the generated reports do not claim they have been performed.

Keep each branch within its connector and cable ratings, including during full-white tests. The total strip current plus the Nano and drivers must remain within the supply's 6 A rating.
