#!/usr/bin/env python3
"""Generate two 5 V APA102 diagrams using only Python's standard library.

Run from the project root: python3 5v/build.py
Writes best.svg, min.svg, matching HTML viewers and DigiKey-compatible
best.csv/min.csv beside this script.
The in-memory wiring and occupied mappings support independent connectivity checks.
"""
from html import escape
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / '.utils'))
from browser_viewer import export_svg_view

OUT = Path(__file__).resolve().parent
NAME = 'best'
MINIMUM_NAME = 'min'
W, H = 880, 2150
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

def rotated_text(x,y,value,size=18,color=INK,bold=False):
    s.append(f'<g transform="rotate(-90 {x} {y})">')
    text(x,y,value,size,color,bold,'middle')
    s.append('</g>')

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
            if not minimum or col in ('L+', 'L-'):
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
        'P1': [(310,yy(1)),(310,yy(25))],
        'P2': [(654,yy(2)),(654,yy(18)),(338,yy(18)),(338,yy(22))],
        'O1': [(454,yy(31)+13),(428,yy(31)+13),(428,yy(41)-13),(454,yy(41)-13)],
        'O2': [(454,yy(28)+13),(441,yy(28)+13),(441,yy(42)-13),(454,yy(42)-13)],
    }
    render_jumpers(bends)


def render_jumpers(bends):
    for label,start,end,color,note in jumpers:
        s.append(f'<g id="jumper-{label}" data-start="{start}" data-end="{end}">')
        s.append(f'<title>{escape(f"{label}: {start} → {end}. {note}")}</title>')
        wire([parse_hole(start),*bends.get(label,()),parse_hole(end)],color,4)
        s.append('</g>')
    # Restore endpoint dots above insulated crossings.
    for label,start,end,color,note in jumpers:
        for endpoint in (start,end): circle(*parse_hole(endpoint),6,color,'white',2)
    # Local rail feeds share rows with the outgoing strip leads. Keep the
    # strip's separate occupied holes visible where those wires overlap.
    for row,color in [(40,INK),(41,CLOCK),(42,DATA),(43,POWER)]:
        circle(*hole('a',row),6,color,'white',2)


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
    if value=='10 kΩ':
        text(x-14,center+5,'10kΩ',15,INK,True,'end')
    else:
        value_x,value_y={'R3':(427,895),'R4':(420,975)}[label]
        rotated_text(value_x,value_y,'33Ω',15,INK,True)


def output_rows():
    # Four physical output rows, matching the user's requested order exactly.
    for row,label,color in [(40,'GND',INK),(41,'CI',CLOCK),(42,'DI',DATA),(43,'+5 V',POWER)]:
        rect(333,yy(row)-11,139,22,'#fff0ce',color,3)
        for col in 'abcde': circle(*hole(col,row),3.8,'#636d6e','#a1aaa9',1)
        text(476,yy(row)+5,label,15,color,True)


def usb_c_jack():
    # Adafruit 4090, rotated 90 degrees counterclockwise: opening faces left.
    # The supplied 8-pin header runs down eight isolated breadboard rows.
    # CC pull-downs are already fitted on the module; model its external pads.
    pins = ('GND', 'VBUS', 'SBU2', 'CC1', 'D-', 'D+', 'SBU1', 'CC2')
    rect(244,yy(54)-13,145,208,'#14627b','#12485b',4)
    rect(234,yy(56)-8,70,94,'#c4cbce','#60747f',5)
    rect(229,yy(56)+2,14,74,'#425862','#647b84',5)
    for row,pin in enumerate(pins,54):
        record(f'J0 {pin}',f'b{row}',f'J0.{pin}',
               'Adafruit 4090; solder supplied header; CC1/CC2 have onboard 5.1 kΩ pull-downs')
        x,y=hole('b',row)
        circle(x,y,5,'#c9b680',INK,1)
        text(x-12,y+4,pin,12,'white',True,'end')
    text(244,yy(54)-24,'J0 · USB-C',19,INK,True)
    rect(183,yy(56)+10,48,58,'#343f47',INK,5)
    line(80,yy(56)+39,183,yy(56)+39,INK,8)
    text(80,yy(56)+85,'5 V USB-C',17,INK,True)
    rect(420,yy(57)-16,276,112,'#f4f7fa','none',4)
    text(435,yy(57)+5,'Adafruit 4090',18,INK,True)
    text(435,yy(58)+5,'2 × 5.1kΩ CC resistors fitted',16,MUTED)
    text(435,yy(60)+5,'Solder included header',16,MUTED)


def nano_usb():
    # The minimum variant also takes LED power from this USB supply via VUSB.
    line(450,218,175,218,'#687a85',3)
    text(167,210,'USB power',18,INK,True,'end')


def led_strip():
    # Visible short strip: CI/DI input end is connected; CO/DO are the onward output end.
    rect(62,yy(40)-15,103,382,'#f5eee0','#bbae8f',4)
    text(112,yy(40)-32,'APA102',16,INK,True,'middle')
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


def build():
    global s,wiring,occupied
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>Kitchen lighting: 5 V APA102 best-practice breadboard layout</title>',
       '<desc>One USB-C input powers the Nano 33 IoT, SN74AHCT125N logic buffer and one to five APA102 pixels. J0 is an Adafruit 4090 USB-C breakout, with onboard CC pull-downs and its supplied header soldered into b54 through b61, socket facing left. VBUS at b55 and GND at b54 supply the rails; the other six pads have no external connections. The Nano VIN header at c15 connects locally through a15 to L+15, and Nano GND connects through a14 to L-14. Both rail pairs are linked, with wire bridges across all four midpoint breaks. Nano VUSB is unconnected; leave its VUSB solder bridge open. The Nano micro-USB socket is only needed for programming. Every jumper is drawn from hole to hole; crossings are insulated.</desc>']
    wiring=[]; occupied={}; jumpers.clear()
    rect(0,0,W,H,'#f4f7fa','#f4f7fa',0)
    text(40,58,'5 V APA102 · Best practice',32,bold=True)
    text(40,94,'1–5 pixels · 0.30 A maximum LED load',19,MUTED)
    text(40,123,'One USB-C input → Nano VIN + LED/buffer 5 V',19,MUTED)
    board()
    # DIP14 notch up: left pins ascend, right pins descend toward board bottom.
    rect(467,yy(21)-22,50,200,'#253b46','#132c38',5)
    s.append(f'<path d="M 479 {yy(21)-22} a 13 9 0 0 0 26 0" fill="#c6cbc9" stroke="#132c38"/>')
    rotated_text(500,yy(24)+1,'SN74AHCT125N',19,'white',True)
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
    rotated_text(x+34,(y+y2)/2,'100nF',16,INK,True)
    # Below the strip terminals, both leads can reach the left rails directly.
    record('C2','c46','c48','1000 µF, 10 V Panasonic EEU-FC1A102B; From is positive; To is negative; 10 mm diameter, 5 mm lead pitch')
    x,y=hole('c',47)
    circle(x,y,51,'#244b5d',INK,2)
    s.append(f'<path d="M {x-29} {y+37} Q {x} {y+58} {x+29} {y+37}" fill="none" stroke="#d0dce1" stroke-width="10"/>')
    for h in ['c46','c48']: circle(*parse_hole(h),4,'#d5c289',INK,1)
    text(x,yy(46)-8,'+',17,'white',True,'middle')
    text(x,yy(48)+21,'−',17,'white',True,'middle')
    text(x,y-1,'1000µF',17,'white',True,'middle')
    text(x,y+20,'10V',15,'white',False,'middle')
    for label,start,end,color,note in [
        ('P1','a1','a25',CLOCK,'Nano D13 → U1 clock input pin 5'),
        ('P2','i2','a22',DATA,'Nano D11 → U1 data input pin 2'),
        ('O1','e31','e41',CLOCK,'R4 → strip CI / clock'),
        ('O2','e28','e42',DATA,'R3 → strip DI / data'),
        ('V0','e55','R+55',POWER,'USB-C J0 VBUS → right + rail'),
        ('V1','j21','R+21',POWER,'+5 V → U1 VCC pin 14 / C1'),
        ('V2','b43','L+43',POWER,'+5 V → strip positive'),
        ('V3','a46','L+46',POWER,'+5 V → C2 positive'),
        ('V4','j22','R+22',POWER,'Disable unused channel 4: pin 13 HIGH'),
        ('V5','j25','R+25',POWER,'Disable unused channel 3: pin 10 HIGH'),
        ('V6','a15','L+15',POWER,'USB-C +5 V → Nano VIN (c15 row)'),
        ('N0','e54','R-54',INK,'USB-C J0 GND → right − rail'),
        ('N1','a14','L-14',INK,'Shared ground → Nano GND'),
        ('N2','a27','L-27',INK,'Ground → U1 pin 7'),
        ('N3','b40','L-40',INK,'Ground → strip GND'),
        ('N4','a48','L-48',INK,'Ground → C2 negative'),
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
    usb_c_jack()
    led_strip()
    draw_jumpers()
    record('Nano programming','PC USB','Nano USB socket','Micro-USB is only needed for programming; USB-C J0 supplies normal operating power through VIN')
    record('J0 power cable','Regulated 5 V USB supply','J0 USB-C socket','USB-C power input; onboard CC1/CC2 pull-downs; no higher-voltage PD request')
    text(440,2010,'Nano VUSB solder bridge open · 5V / VUSB pin unused',17,MUTED,False,'middle')
    text(440,2072,'+ rails: 5 V     − rails: GND',18,MUTED,True,'middle')
    s.append('</svg>')
    path=OUT/(NAME+'.svg')
    path.write_text('\n'.join(s),encoding='utf-8')
    print(f'Wrote {export_svg_view(path, navigation=True)}.')
    print(f'Wrote {path}; {len(occupied)} distinct occupied holes.')
    return path

def build_minimum():
    """Direct 3.3 V signals and USB-fed Nano VUSB power for the short strip."""
    global s,wiring,occupied
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>Kitchen lighting: 5 V APA102 minimum breadboard layout</title>',
       '<desc>Minimum-component experiment with an Arduino Nano 33 IoT and one to five APA102 pixels powered from its USB socket. Close the underside VUSB solder bridge SJ1 to enable USB 5 V at header c12. Feed the left positive rail locally at row 12 and ground at row 14; bridge both left rail midpoint breaks to supply the strip at rows 40 and 43. Nano D13 connects directly to CI and D11 directly to DI at 3.3 V; operation is not guaranteed with every strip. No separate input jack, buffer, resistors or capacitors are fitted. All connecting wires are drawn.</desc>']
    wiring=[]; occupied={}; jumpers.clear()
    rect(0,0,W,H,'#f4f7fa','#f4f7fa',0)
    text(40,58,'5 V APA102 · Minimum',32,bold=True)
    text(40,94,'1–5 pixels · 0.30 A maximum LED load',19,MUTED)
    text(40,123,'Nano USB → 5V / VUSB pin → LEDs',19,MUTED)
    text(40,158,'Close VUSB solder bridge (SJ1, Nano underside).',18,INK,True)
    board(minimum=True)
    output_rows()
    nano_usb()
    led_strip()
    for label,start,end,color,note in [
        ('P1','a1','b41',CLOCK,'Nano D13 / SCK → strip CI, direct 3.3 V clock'),
        ('P2','i2','b42',DATA,'Nano D11 / COPI → strip DI, direct 3.3 V data'),
        ('V0','a12','L+12',POWER,'Nano USB-fed 5V / VUSB (c12 row) → left + rail; close SJ1'),
        ('V1','b43','L+43',POWER,'Lower left + rail → strip +5 V'),
        ('N1','a14','L-14',INK,'Nano GND (c14 row) → left − rail'),
        ('N2','b40','L-40',INK,'Lower left − rail → strip GND'),
        ('B1','L+31','L+34',POWER,'Bridge left + rail midpoint break'),
        ('B2','L-31','L-34',INK,'Bridge left − rail midpoint break'),
    ]: jumper(label,start,end,color,note)
    render_jumpers({
        'P1': [(326,yy(1)),(326,yy(17)),(376,yy(17))],
        'P2': [(654,yy(2)),(654,yy(18)),(402,yy(18)),(402,yy(42)-13),(376,yy(42)-13)],
    })
    record('Nano USB power','Regulated 5 V USB supply','Nano USB socket','Single USB input powers Nano and short strip through closed VUSB solder bridge SJ1 and header c12')
    text(440,2010,'Direct 3.3 V signals: operation is not guaranteed.',18,MUTED,False,'middle')
    text(440,2072,'+ rails: 5 V     − rails: GND',18,MUTED,True,'middle')
    s.append('</svg>')
    path=OUT/(MINIMUM_NAME+'.svg')
    path.write_text('\n'.join(s),encoding='utf-8')
    print(f'Wrote {export_svg_view(path, navigation=True)}.')
    print(f'Wrote {path}; {len(occupied)} distinct occupied holes.')
    return path


if __name__=='__main__':
    build()
    build_minimum()
    from purchasing import export_purchase_csvs
    for path in export_purchase_csvs(OUT):
        print(f'Generated {path} for DigiKey Canada upload.')
