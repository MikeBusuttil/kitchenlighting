#!/usr/bin/env python3
"""Generate two 5 V APA102 diagrams using only Python's standard library.

Run from the project root: python3 5v/build_5v.py
Writes kitchen-lighting-5v-breadboard.svg (best practice) and
kitchen-lighting-5v-minimum-breadboard.svg (minimum), beside this script.
The in-memory wiring and occupied mappings support independent connectivity checks.
"""
from html import escape
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
NAME = 'kitchen-lighting-5v-breadboard'
MINIMUM_NAME = 'kitchen-lighting-5v-minimum-breadboard'
W, H = 2380, 2380
CLOCK, DATA = '#286bbb', '#258450'
INK, MUTED, BORDER = '#192c3a', '#536775', '#d2dce3'
RED, GREEN, BLUE, POWER = '#c0383c', '#258450', '#286bbb', '#aa5217'
COL = dict(zip('abcde', range(350, 455, 26)))
COL.update(dict(zip('fghij', range(532, 637, 26))))
COL.update({'L+':258, 'L-':284, 'R+':714, 'R-':740})
LEFT = ['D13 / SCK','3V3','AREF','A0','A1','A2','A3','A4','A5','A6','A7','5V / VUSB','RESET','GND','VIN']
RIGHT = ['D12','D11 / COPI','D10','D9','D8','D7','D6','D5','D4','D3','D2','GND','RESET','RX','TX']

def yy(row): return 260 + 26*(row-1)
def hole(col,row): return COL[col], yy(row)

s = []

def rect(x,y,w,h,fill='white',stroke=BORDER,r=10):
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

def text(x,y,value,size=20,color=INK,bold=False,anchor='start',mono=False):
    font='DejaVu Sans Mono' if mono else 'DejaVu Sans'
    s.append(f'<text x="{x}" y="{y}" font-family="{font},sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{anchor}">{escape(value)}</text>')

def line(x1,y1,x2,y2,color=INK,width=2):
    s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')

def circle(x,y,r=5,fill='white',stroke=INK,width=2):
    s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

def wire(points,color,width=5):
    pts=' '.join(f'{x},{y}' for x,y in points)
    for sw,co in [(width+5,'#f5f7fa'),(width,color)]:
        s.append(f'<polyline points="{pts}" fill="none" stroke="{co}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')
    for x,y in (points[0],points[-1]): circle(x,y,6,color,'white',2)

def panel(x,y,w,h,title):
    rect(x,y,w,h)
    text(x+22,y+34,title,23,bold=True)
    line(x+22,y+48,x+w-22,y+48,BORDER,1)

# Component leads are recorded independently of drawing routes.  Each physical
# hole takes exactly one lead; terminals on the same bank/row share a net.
wiring=[]
occupied={}
def record(label,start,end,notes=''):
    for endpoint in (start,end):
        if re.fullmatch(r'(?:[a-j]|[LR][+-])(?:[1-9]|[1-5][0-9]|6[0-4])',endpoint):
            assert endpoint not in occupied, (endpoint,label,occupied.get(endpoint))
            occupied[endpoint]=label
    wiring.append((label,start,end,notes))

def parse_hole(endpoint):
    match=re.fullmatch(r'([a-j]|[LR][+-])(\d+)',endpoint)
    return hole(match[1],int(match[2]))

def board(minimum=False):
    rect(220,214,562,1717,'#e8e9e5','#a9b6ba',18)
    rect(314,233,158,1680,'#fdfcf8','#d2d5d0',4)
    rect(514,233,150,1680,'#fdfcf8','#d2d5d0',4)
    rect(482,241,21,1660,'#c6cbc9','#c6cbc9',3)
    for col in ['L+','L-','R+','R-']:
        x=COL[col]; color='#c57979' if '+' in col else '#7d9ab8'
        for start,end in [(1,31),(34,64)]:
            if not minimum or (col.startswith('R') and start==34):
                rect(x-8,yy(start)-9,16,yy(end)-yy(start)+18,
                     '#f6ddd3' if '+' in col else '#dce4ea','none',5)
        for start,end in [(1,31),(34,64)]: line(x-11,yy(start)-12,x-11,yy(end)+12,color,2)
        text(x,228,'+' if '+' in col else '−',19,color,True,'middle')
    for col in 'abcdefghij': text(COL[col],228,col,19,MUTED,True,'middle')
    for row in range(1,65):
        text(303,yy(row)+5,str(row),15,MUTED,anchor='end',mono=True)
        text(678,yy(row)+5,str(row),15,MUTED,mono=True)
        for col in COL: circle(*hole(col,row),3.8,'#636d6e','#a1aaa9',1)
    rect(380,237,200,404,'#087e7b','#006763',6)
    rect(450,201,61,56,'#c4cbce','#60747f',3)
    rect(459,207,43,17,'#425862','#647b84',2)
    text(480,195,'USB ↑',18,MUTED,True,'middle')
    rect(452,345,57,69,'#244956','#244956',2)
    rect(434,536,93,64,'#a1b2ba','#718b94',3)
    text(480,436,'NANO',18,'white',True,'middle')
    text(480,460,'33 IoT',18,'white',True,'middle')
    for row,(left,right) in enumerate(zip(LEFT,RIGHT),1):
        for col,name in [('c',left),('g',right)]:
            x,y=hole(col,row); rect(x-5,y-5,10,10,'#d6ae5a','#a78140',1)
            record(f'Nano header {col}{row}',f'{col}{row}',f'Nano {name}')
        text(COL['c']+10,yy(row)+4,left.split(' / ')[0],11,'white')
        text(COL['g']-10,yy(row)+4,right.split(' / ')[0],11,'white',anchor='end')

jumpers = []

def jumper(label, start, end, color, note):
    record(label,start,end,note)
    jumpers.append((label,start,end,color,note))


def draw_jumpers():
    # Bends describe insulated wire placement, never additional connections.
    # Keep the signal wires clear of the Nano and component bodies.
    bends={
        'P1': [(326,yy(1)),(326,yy(25))],
        'P2': [(654,yy(2)),(654,yy(18)),(338,yy(18)),(338,yy(22))],
        'O1': [(454,yy(31)+13),(428,yy(31)+13),(428,yy(41)-13),(454,yy(41)-13)],
        'O2': [(454,yy(28)+13),(441,yy(28)+13),(441,yy(42)-13),(454,yy(42)-13)],
        'V2': [(376,yy(44))],
        'V3': [(532,yy(40))],
        'N3': [(376,yy(39))],
        'N4': [(532,yy(47))],
    }
    labels={
        'P1': (335,480), 'P2': (601,yy(18)-9),
        'O1': (400,1172), 'O2': (450,1224),
        'V0': (565,yy(58)-9), 'V1': (648,yy(21)-9),
        'V2': (296,yy(44)-9), 'V3': (649,yy(40)-9),
        'V4': (648,yy(22)-9), 'V5': (648,yy(25)-9),
        'N0': (565,yy(60)-9), 'N1': (289,yy(14)-9),
        'N2': (289,yy(27)-9), 'N3': (289,yy(39)-9),
        'N4': (648,yy(47)-9), 'N5': (289,yy(24)-9),
        'N6': (289,yy(21)-9), 'N7': (648,yy(26)-9),
        'N8': (648,yy(23)-9),
        'B1': (228,yy(33)), 'B2': (310,yy(32)+13),
        'B3': (674,yy(32)+13), 'B4': (748,yy(33)),
        'B5': (480,yy(50)-9), 'B6': (480,yy(52)-9),
    }
    render_jumpers(bends,labels)


def render_jumpers(bends,labels):
    for label,start,end,color,note in jumpers:
        s.append(f'<g id="jumper-{label}" data-start="{start}" data-end="{end}">')
        s.append(f'<title>{escape(f"{label}: {start} → {end}. {note}")}</title>')
        wire([parse_hole(start),*bends.get(label,()),parse_hole(end)],color,4)
        s.append('</g>')
    # Restore endpoint dots above crossings, then label each wire once.
    for label,start,end,color,note in jumpers:
        for endpoint in (start,end): circle(*parse_hole(endpoint),6,color,'white',2)
    for label,start,end,color,note in jumpers:
        x,y=labels[label]
        rect(x-2,y-12,24,16,'#f5f7fa','none',2)
        text(*labels[label],label,12,color,True)


def resistor(label,start,end,value,color):
    note=f'{value}, 1/4 W; '+('upright body with bent return lead' if value=='10 kΩ' else 'body flat; form leads to 12.7 mm spacing')
    record(label,start,end,note)
    x,y=parse_hole(start); x2,y2=parse_hole(end)
    line(x,y,x2,y2,color,2)
    center=y+19 if value=='10 kΩ' else (y+y2)/2
    length=26 if value=='10 kΩ' else 54
    rect(x-7,center-length/2,14,length,'#edce8c',INK,2)
    bands=['#673b26','#171717','#df781e'] if value=='10 kΩ' else ['#e77c22','#e77c22','#171717']
    for k,co in enumerate(bands): line(x-6,center-8+k*8,x+6,center-8+k*8,co,3)
    for h in (start,end): circle(*parse_hole(h),4,color,'white',1)
    text(x-11,center+4,label,12,color,True,'end')


def output_rows():
    # Four physical output rows, matching the user's requested order exactly.
    for row,label,color in [(40,'GND',INK),(41,'CI',CLOCK),(42,'DI',DATA),(43,'+5 V',POWER)]:
        rect(333,yy(row)-11,139,22,'#fff0ce',color,3)
        for col in 'abcde': circle(*hole(col,row),3.8,'#636d6e','#a1aaa9',1)
        text(476,yy(row)+5,label,15,color,True)


def barrel_jack():
    # J0 is rotated toward the bottom edge; plug clears other components.
    record('J0 pin 1 / center','b58','J0.1','Positive regulated 5 V; verify cable polarity before connecting')
    record('J0 pin 2 / sleeve','b60','J0.2','Unswitched sleeve / ground; verify with plug inserted')
    record('J0 pin 3 / switched sleeve','d59','J0.3','Unused; leave all other left-bank row 59 holes empty')
    rect(331,yy(58)-9,90,145,'#303a43',INK,5)
    rect(348,yy(58)+117,56,23,'#141c22','#53636c',4)
    for col,row,label in [('b',58,'1 +'),('b',60,'2 −'),('d',59,'3 NC')]:
        x,y=hole(col,row); circle(x,y,5,'#c9b680',INK,1)
        text(x+10,y+5,label,12,'white' if col=='b' else MUTED,True)
    rect(358,yy(58)+140,36,51,'#363e43',INK,4)
    line(376,yy(58)+191,376,yy(64)+82,POWER,6)
    text(446,yy(64)+40,'J0 · opening ↓',16,INK,True)
    text(376,yy(64)+110,'5 V USB → barrel cable',16,MUTED,anchor='middle')


def nano_usb():
    # Nano USB socket power path is distinct from the LED positive supply.
    line(450,218,175,218,'#687a85',3)
    text(167,210,'USB ← PSU / PC',15,INK,True,'end')
    text(167,233,'to Nano',15,MUTED,anchor='end')


def led_strip():
    # Visible short strip: CI/DI input end is connected; CO/DO are the onward output end.
    rect(62,yy(40)-15,103,382,'#f5eee0','#bbae8f',4)
    text(112,yy(40)-32,'1–5 APA102',16,INK,True,'middle')
    for idx,(label,color) in enumerate([('GND',INK),('CI',CLOCK),('DI',DATA),('+5V',POWER)]):
        ry=yy(40+idx)
        rect(137,ry-7,23,14,'#c6a764',color,2)
        text(94,ry+5,label,13,color,True,'middle')
        start=f'a{40+idx}'; record('Strip '+label,start,'Strip '+label,'Connect input end marked CI/DI; output end CO/DO unused')
        wire([parse_hole(start),(160,ry)],color,3)
    for k in range(5):
        ly=yy(40)+129+k*42
        rect(91,ly-13,43,28,'#e4e4d9','#978c74',3)
        rect(103,ly-6,19,14,'#f2d75e','#cbb547',2)
    text(112,yy(40)+390,'CO / DO unused',13,MUTED,anchor='middle')


def build():
    global s,wiring,occupied
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>Kitchen lighting: 5 V APA102 best-practice breadboard layout</title>',
       '<desc>Nano 33 IoT powered through its USB socket. J0 supplies the positive and ground rails for an SN74AHCT125N logic buffer and one to five APA102 pixels. Both rail pairs are linked, with wire bridges across all four midpoint breaks. Nano VIN and VUSB are unconnected. Every jumper is drawn from hole to hole; crossings are insulated.</desc>']
    wiring=[]; occupied={}; jumpers.clear()
    rect(0,0,W,H,'#f4f7fa','#f4f7fa',0)
    text(40,58,'Kitchen lighting · 5 V APA102 · best practice',35,bold=True)
    text(40,94,'Nano 33 IoT · USB at top · + rails = 5 V · − rails = GND · every jumper drawn',22,MUTED)
    text(2340,55,'5 V · SHORT-STRIP PoC',19,'#007d80',True,'end')
    rect(40,117,2300,77,'#fff3dd','#e4cf9f',7)
    text(58,146,'Connect 1–5 pixels for this prototype, about 8.3 cm maximum at 60 LEDs/m. Keep the full 160-inch strip disconnected.',22,INK,True)
    text(58,176,'Budget up to 0.30 A for 5 LEDs, plus the Nano. Use a regulated 5 V USB supply rated at least 1 A for this small test.',20)
    board()
    # DIP14 notch up: left pins ascend, right pins descend toward board bottom.
    rect(467,yy(21)-11,50,178,'#253b46','#132c38',5)
    s.append(f'<path d="M 479 {yy(21)-11} a 13 9 0 0 0 26 0" fill="#c6cbc9" stroke="#132c38"/>')
    text(492,yy(24)+3,'U1',17,'white',True,'middle')
    for pin in range(1,15):
        col='e' if pin<=7 else 'f'
        row=20+pin if pin<=7 else 35-pin
        x,y=hole(col,row)
        line(x,y,467 if col=='e' else 517,y,'#b3bec3',5)
        circle(x,y,4,'#d1bb7a',INK,1)
        text(460 if col=='e' else 523,y+4,str(pin),10,INK,anchor='end' if col=='e' else 'start')
        record(f'U1 pin {pin}',f'{col}{row}',f'U1.{pin}','SN74AHCT125N DIP14; notch points toward USB')
    output_rows()
    resistor('R1','b22','b24','10 kΩ',DATA)
    resistor('R2','b25','b27','10 kΩ',CLOCK)
    resistor('R3','c23','c28','33 Ω',DATA)
    resistor('R4','d26','d31','33 Ω',CLOCK)
    record('C1','h21','h23','100 nF ceramic, 50 V; nonpolarized; h21 +5 V, h23 GND')
    x,y=hole('h',21); x2,y2=hole('h',23)
    line(x,y,x2,y2,POWER,2)
    rect(x-7,(y+y2)/2-13,14,26,'#bb914e','#8d6c35',3)
    for h in ['h21','h23']: circle(*parse_hole(h),4,POWER,'white',1)
    text(x+12,(y+y2)/2+5,'C1',12,MUTED,True)
    record('C2','i43','i45','1000 µF, 10 V Panasonic EEU-FC1A102B; From is positive; To is negative; 10 mm diameter, 5 mm lead pitch')
    x,y=hole('i',44)
    circle(x,y,51,'#244b5d',INK,2)
    s.append(f'<path d="M {x-29} {y+37} Q {x} {y+58} {x+29} {y+37}" fill="none" stroke="#d0dce1" stroke-width="10"/>')
    for h in ['i43','i45']: circle(*parse_hole(h),4,'#d5c289',INK,1)
    text(x,yy(43)-8,'+',17,'white',True,'middle')
    text(x,yy(45)+21,'−',17,'white',True,'middle')
    text(x,yy(42)-15,'C2',16,MUTED,True,'middle')
    for label,start,end,color,note in [
        ('P1','a1','a25',CLOCK,'Nano D13 → U1 clock input pin 5'),
        ('P2','i2','a22',DATA,'Nano D11 → U1 data input pin 2'),
        ('O1','e31','e41',CLOCK,'R4 → strip CI / clock'),
        ('O2','e28','e42',DATA,'R3 → strip DI / data'),
        ('V0','e58','R+58',POWER,'J0 +5 V → right + rail'),
        ('V1','j21','R+21',POWER,'+5 V → U1 VCC pin 14 / C1'),
        ('V2','b43','L+44',POWER,'+5 V → strip positive'),
        ('V3','f43','R+40',POWER,'+5 V → C2 positive'),
        ('V4','j22','R+22',POWER,'Disable unused channel 4: pin 13 HIGH'),
        ('V5','j25','R+25',POWER,'Disable unused channel 3: pin 10 HIGH'),
        ('N0','e60','R-60',INK,'J0 sleeve → right − rail'),
        ('N1','a14','L-14',INK,'Shared ground → Nano GND'),
        ('N2','a27','L-27',INK,'Ground → U1 pin 7'),
        ('N3','b40','L-39',INK,'Ground → strip GND'),
        ('N4','f45','R-47',INK,'Ground → C2 negative'),
        ('N5','a24','L-24',INK,'Enable clock channel: pin 4 LOW'),
        ('N6','a21','L-21',INK,'Enable data channel: pin 1 LOW'),
        ('N7','j26','R-26',INK,'Unused input pin 9 → ground'),
        ('N8','j23','R-23',INK,'Unused input pin 12 / C1 → ground'),
        ('B1','L+31','L+34',POWER,'Bridge left + rail midpoint break'),
        ('B2','L-31','L-34',INK,'Bridge left − rail midpoint break'),
        ('B3','R+31','R+34',POWER,'Bridge right + rail midpoint break'),
        ('B4','R-31','R-34',INK,'Bridge right − rail midpoint break'),
        ('B5','L+50','R+50',POWER,'Link left and right +5 V rails'),
        ('B6','L-52','R-52',INK,'Link left and right ground rails'),
    ]: jumper(label,start,end,color,note)
    barrel_jack()
    nano_usb()
    led_strip()
    draw_jumpers()
    text(502,2054,'+ rails: 5 V · − rails: GND · B1–B4 bridge breaks',16,MUTED,True,'middle')
    # Component table includes every lead; jumper table completes the physical netlist.
    panel(850,214,1490,687,'Component locations · physical top view')
    notes=[
        'Colored lines are actual jumpers. Dots mark plugged ends; crossings do not connect.',
        'a–e connect within each row; f–j connect within each row. The trench separates them.',
        'Nano: c1–c15 / g1–g15, USB at top. VIN (c15) and VUSB (c12) stay unconnected.',
        'U1 = SN74AHCT125N, DIP14. Notch faces UP; use AHCT, not a plain 74HC125.',
        'U1 left: pin 1 e21, 2 e22, 3 e23, 4 e24, 5 e25, 6 e26, 7 e27.',
        'U1 right: pin 8 f27, 9 f26, 10 f25, 11 f24, 12 f23, 13 f22, 14 f21.',
        'R1 10 kΩ: b22 ↔ b24.  R2 10 kΩ: b25 ↔ b27. Stand these two upright.',
        'R3 33 Ω: c23 ↔ c28 (data).  R4 33 Ω: d26 ↔ d31 (clock). Mount flat.',
        'C1 100 nF ceramic: h21 ↔ h23. Nonpolarized; keep close to U1.',
        'C2 1000 µF / 10 V: positive i43, negative i45. Stripe is the negative lead.',
        'C2: Panasonic EEU-FC1A102B, 10 mm diameter / 5 mm lead pitch.',
        'J0 Adafruit 373 / PJ-102AH: + b58, sleeve b60, unused switch d59.',
        'Jack opening faces DOWN. Its leads need gentle forming to match the 2.54 mm grid.',
        'Keep all other a–e59 holes empty. Leave U1 output pins 8 and 11 unconnected.',
        'Output a40 GND, a41 CLOCK → CI, a42 DATA → DI, a43 +5 V.',
        'Connect the strip INPUT end. Labels CO / DO identify its onward output end.'
    ]
    for i,note in enumerate(notes): text(875,289+i*36,note,19,INK if i<11 else MUTED)
    panel(850,922,1490,483,'Jumper list · L / R = left / right rail · + = 5 V · − = GND')
    for idx,(label,start,end,color,note) in enumerate(jumpers):
        column=idx//13; row=idx%13; x=880+column*715; y=1003+row*30
        text(x,y,label,19,color,True)
        text(x+49,y,f'{start:>4} ↔ {end:<4}',17,INK,mono=True)
        short=note.replace('Unused input ','Input ').replace('Disable unused channel 4: ','Unused OE: ').replace('Disable unused channel 3: ','Unused OE: ').replace('Enable clock channel: ','Clock OE: ').replace('Enable data channel: ','Data OE: ')
        text(x+217,y,short,16,MUTED)
    panel(850,1426,1490,628,'Power and operation')
    powernotes=[
        'The Nano receives power through its own USB socket.',
        'J0 feeds the right + / − rails. B5 / B6 link them to the left + / − rails.',
        'B1–B4 bridge all four rail breaks at rows 31–34; check rail continuity before power.',
        'N1 joins Nano GND to the − rail. Neither VIN nor VUSB carries strip power.',
        'Assumed J0 cable: USB-A → 5.5 × 2.1 mm barrel, center positive, 5 V only.',
        'Use two charger outputs, or PC USB for Nano plus a separate 5 V LED supply.',
        'U1 translates 3.3 V Nano data/clock to 5 V logic for the strip.',
        'Set every pixel to the same RGB value and brightness in the firmware loop.',
        'Start with 1 pixel, then at most 5. Measure current before increasing the load.',
        'Budget up to 60 mA per pixel: 5 pixels ≈0.30 A, plus Nano/buffer current.',
        'A 160-inch strip at 60 LEDs/m is about 244 pixels: up to 14.6 A by this estimate.',
        'The full strip needs a separate current-rated power build; never feed it through Nano.',
        'The breadboard is only for this small test, not the full strip current.',
    ]
    for i,note in enumerate(powernotes): text(875,1502+i*35,note,20,INK if i<8 else MUTED)
    # Primary source links remain clickable in the SVG output.
    for y,title,url in [
        (1985,'Sources: TI SN74AHCT125 datasheet','https://www.ti.com/lit/ds/symlink/sn74ahct125.pdf'),
        (2020,'Adafruit APA102 power guidance','https://learn.adafruit.com/adafruit-dotstar-leds/power-and-connections'),
    ]:
        s.append(f'<a href="{escape(url,quote=True)}">')
        text(875,y,title,16,CLOCK)
        s.append('</a>')
    s.append('<a href="https://docs.arduino.cc/resources/pinouts/ABX00027-full-pinout.pdf">')
    text(1450,2020,'Arduino Nano 33 IoT pinout',16,CLOCK)
    s.append('</a>')
    record('Nano USB power','USB charger or PC','Nano USB socket','Separate USB cable; do not connect Nano VIN or VUSB to the LED positive bus')
    record('J0 power cable','Regulated 5 V USB charger','J0 barrel plug','USB to 5.5 × 2.1 mm barrel; verify center positive and cable rating')
    panel(40,2080,2300,237,'Before connecting power')
    text(64,2152,'Use 5 V only. Disconnect power before changing wires; check for shorts and verify C2 polarity and the barrel cable center-positive voltage.',21,INK,True)
    text(64,2192,'Power the Nano by USB. Keep Nano VIN and VUSB unconnected. Connect a40–a43 to the strip input marked GND / CI / DI / +5 V.',20)
    text(64,2232,'Start with one pixel. Five pixels is a small-load test; the charger rating is available capacity, not a breadboard short-circuit current limit.',20)
    text(64,2272,'This build is the 5 V APA102 stage only. The 12 V strip, MOSFET circuit and L7805CV regulators are not connected.',20,MUTED)
    text(42,2353,'5 V REV B · 12 OCT 2026 · Standalone SVG · Full jumper routes with linked 5 V / GND rails and midpoint bridges.',17,MUTED)
    s.append('</svg>')
    path=OUT/(NAME+'.svg')
    path.write_text('\n'.join(s),encoding='utf-8')
    print(f'Wrote {path}; {len(occupied)} distinct occupied holes.')
    return path

def build_minimum():
    """Direct 3.3 V signals; only the Nano, J0, strip, supply and wires remain."""
    global s,wiring,occupied
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>Kitchen lighting: 5 V APA102 minimum breadboard layout</title>',
       '<desc>Minimum-component experiment with an Arduino Nano 33 IoT, barrel jack J0, regulated 5 V supply and one to five APA102 pixels. Nano D13 connects directly to CI and D11 directly to DI at 3.3 V. Direct control is not guaranteed to work with every strip. No buffer, resistors or capacitors are fitted. Only the lower right power rails are used, with shared ground and separate USB power for the Nano. All connecting wires are drawn.</desc>']
    wiring=[]; occupied={}; jumpers.clear()
    rect(0,0,W,H,'#f4f7fa','#f4f7fa',0)
    text(40,58,'Kitchen lighting · 5 V APA102 · minimum',35,bold=True)
    text(40,94,'Nano 33 IoT + barrel jack + strip · direct data / clock · lower right + / − rails only',22,MUTED)
    text(2340,55,'5 V · MINIMUM PoC',19,'#007d80',True,'end')
    rect(40,117,2300,77,'#fff3dd','#e4cf9f',7)
    text(58,146,'1–5 pixels only. Strip power is 5 V; Nano data and clock are 3.3 V. The Nano receives power through its USB socket.',22,INK,True)
    text(58,176,'Direct 3.3 V control may work with your APA102 strip, but it is not guaranteed. This version omits all signal and supply conditioning.',20)
    board(minimum=True)
    output_rows()
    barrel_jack()
    nano_usb()
    led_strip()
    for label,start,end,color,note in [
        ('P1','a1','b41',CLOCK,'Nano D13 / SCK → strip CI, direct 3.3 V clock'),
        ('P2','i2','b42',DATA,'Nano D11 / COPI → strip DI, direct 3.3 V data'),
        ('V0','e58','R+58',POWER,'J0 center positive → lower right + rail'),
        ('V1','e43','R+43',POWER,'Lower right + rail → strip +5 V'),
        ('N0','e60','R-60',INK,'J0 sleeve → lower right − rail'),
        ('N1','i12','R-38',INK,'Nano GND (g12 row) → lower right − rail'),
        ('N2','e40','R-40',INK,'Lower right − rail → strip GND'),
    ]: jumper(label,start,end,color,note)
    render_jumpers({
        'P1': [(326,yy(1)),(326,yy(17)),(376,yy(17))],
        'P2': [(654,yy(2)),(654,yy(18)),(402,yy(18)),(402,yy(42)-13),(376,yy(42)-13)],
        'V1': [(454,yy(43)+13),(688,yy(43)+13),(688,yy(43))],
        'N1': [(766,yy(12)),(766,yy(38))],
        'N2': [(454,yy(39)-13),(740,yy(39)-13)],
    },{
        'P1': (343,972), 'P2': (411,1024),
        'V0': (565,yy(58)-9), 'V1': (565,yy(43)+34),
        'N0': (565,yy(60)-9), 'N1': (739,960),
        'N2': (565,yy(39)-22),
    })
    text(502,2054,'Only lower right rails used · + = 5 V · − = GND',16,MUTED,True,'middle')

    panel(850,214,1490,687,'Minimum build · physical top view')
    notes=[
        'Keep: Nano 33 IoT, J0 barrel jack, 1–5 APA102 pixels, regulated 5 V supply and wires.',
        'U1, C1, C2 and R1–R4 are omitted completely.',
        'The Nano sends clock and data straight to the strip, with no level shifter.',
        'Nano: c1–c15 / g1–g15, USB at top. VIN (c15) and VUSB (c12) stay unconnected.',
        'Clock: a1 shares Nano D13 at c1. Data: i2 shares Nano D11 at g2.',
        'Nano ground: i12 shares GND at g12; N1 goes directly to the lower right − rail.',
        'J0 Adafruit 373 / PJ-102AH: + b58, sleeve b60, unused switch d59.',
        'Jack opening faces DOWN. Keep all other a–e59 holes empty.',
        'Output: a40 GND, a41 CLOCK → CI, a42 DATA → DI, a43 +5 V.',
        'Connect the strip INPUT end; leave the CO / DO output end unconnected.',
        'Only right-side rail rows 34–64 are used. No midpoint or left/right bridges are needed.',
        'Dots mark plugged wire ends. Insulated wires cross without connecting.',
        'a–e connect within each row; f–j connect within each row. The trench separates them.',
    ]
    for i,note in enumerate(notes): text(875,289+i*42,note,20,INK if i<9 else MUTED)

    panel(850,922,1490,483,'Seven jumpers · R+ = right + rail · R− = right − rail')
    for idx,(label,start,end,color,note) in enumerate(jumpers):
        y=1003+idx*46
        text(880,y,label,21,color,True)
        text(955,y,f'{start:>4} ↔ {end:<4}',20,INK,mono=True)
        text(1150,y,note,21,MUTED)
    text(875,1352,'Also shown: four strip leads, Nano USB cable, and the 5 V USB-to-barrel cable into J0.',20,MUTED)

    panel(850,1426,1490,628,'Power and setup')
    powernotes=[
        'The Nano receives power through its own USB socket.',
        'J0 receives regulated 5 V through a center-positive 5.5 × 2.1 mm barrel cable.',
        'V0 and N0 feed the lower right + and − rails; V1 and N2 feed the strip.',
        'N1 connects Nano GND to that same − rail. A shared ground is essential.',
        'Nano GPIO pins provide control signals only; J0 supplies all strip power.',
        'Keep Nano VIN, VUSB and 3V3 separate from the strip +5 V rail.',
        'Use two charger outputs, or PC USB for Nano plus a separate 5 V LED supply.',
        'Start with one pixel, then at most five. Keep the full 160-inch strip disconnected.',
        'For this test, allow up to 0.30 A for five pixels, plus the Nano; use a 5 V / 1 A supply.',
        'Set every connected pixel to the same RGB value and brightness in the firmware.',
        'If this strip does not accept 3.3 V inputs, use the best-practice diagram with U1.',
    ]
    for i,note in enumerate(powernotes): text(875,1502+i*39,note,20,INK if i<7 else MUTED)
    for y,title,url in [
        (1985,'Adafruit: 3.3 V control is not guaranteed','https://learn.adafruit.com/adafruit-dotstar-leds/power-and-connections'),
        (2020,'Arduino Nano 33 IoT pinout','https://docs.arduino.cc/resources/pinouts/ABX00027-full-pinout.pdf'),
    ]:
        s.append(f'<a href="{escape(url,quote=True)}">')
        text(875,y,title,16,CLOCK)
        s.append('</a>')
    record('Nano USB power','USB charger or PC','Nano USB socket','Separate USB cable; do not connect Nano VIN or VUSB to the LED positive bus')
    record('J0 power cable','Regulated 5 V USB charger','J0 barrel plug','USB to 5.5 × 2.1 mm barrel; verify center positive and cable rating')
    panel(40,2080,2300,237,'Connection check')
    text(64,2152,'Use regulated 5 V only. Verify the barrel cable is center positive and the + / − rails are not shorted before connecting power.',21,INK,True)
    text(64,2192,'Nano D13 → CI, Nano D11 → DI. Nano GND, J0 sleeve and strip GND must share the lower right − rail.',20)
    text(64,2232,'Power the Nano by USB. Connect a40–a43 to the strip input marked GND / CI / DI / +5 V. Leave VIN and VUSB unconnected.',20)
    text(64,2272,'Only 1–5 pixels belong on this breadboard power path. This minimum circuit retains J0 and omits U1, C1, C2 and all four resistors.',20,MUTED)
    text(42,2353,'5 V MINIMUM REV A · 12 OCT 2026 · Standalone SVG · Direct 3.3 V signals · Barrel jack retained · Seven drawn jumpers.',17,MUTED)
    s.append('</svg>')
    path=OUT/(MINIMUM_NAME+'.svg')
    path.write_text('\n'.join(s),encoding='utf-8')
    print(f'Wrote {path}; {len(occupied)} distinct occupied holes.')
    return path


if __name__=='__main__':
    build()
    build_minimum()
