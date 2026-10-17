Create a sketch (or whatever the file is called that gets uploaded to the Nano) for 12v/min that has 3 states toggled by the button on the nano.  It starts in:
1. full brightness state where RGB is all at full brightness, 
2. mood lighting where the color is softer and the brightness is toned down
3. trippy mode where the lights cycle through all colors of the rainbow (at some period ~5s for the whole rainbow) while the brightness cycles between full and off at some other period (~9s)

- build it
  - assemble all parts
    - get magnet for breadboard
      - see where Im gonna mount it
  - measure current at full brightness to see if its going to be a problem
    - Measure combined length required & cut excess
- design control circuit
  - generate SVG & HTML as well as PDF
    - fix the readme so the links all work nice
      - is there a way to open HTML files in github readmes?
  - dockerize all those random packages
- The HTML links below use GitHub Pages for rendered diagrams. One-time setup: in the repository’s **Settings → Pages → Build and deployment**, set **Source** to **Deploy from a branch**, choose **master** and **/ (root)**, then click **Save**. The links become available after the files are pushed and the Pages deployment succeeds.

## v1

- mount lights under dishes
- mount lights above air fryer

- tap into sink light power (at bulb)
  - mount power source & controller (hidden)
  - connect PSU to outlet
- connect dish lights to power source
  - fish through cabinets against front face with no visible signs
- connect air fryer lights
- configure controller to output the desired temperature and brightness
  - Figure out temp & brightness connection 

Phase 2:
- allow color/brightness adjustments

Phase 3:
- living room mood lighting:
  - behind cabinet
  - inside console
- trigger by unused vestibule switch
- control color through app
- include kitchen counter lights
