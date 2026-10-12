#!/usr/bin/env python3
"""Generate best-practice and minimum 12 V kitchen-lighting SVG diagrams.

From the project root: python3 12v/build_12v.py
Both SVGs are written beside this script. Only Python's standard library is used.
The minimum uses three TN0702N3-G MOSFETs and the lower right power rails.
"""
from html import escape
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
NAME = 'kitchen-lighting-12v-breadboard'
MINIMUM_NAME = 'kitchen-lighting-12v-minimum-breadboard'
W, H = 2380, 2380
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

def local(label, start, end, color=INK, note='', via=()):
    record(label, start, end, note)
    wire([parse_hole(start), *via, parse_hole(end)], color, 3)


# Paired endpoint flags are deliberate: they leave every physical hole legible.
# The same label on two holes denotes one uninterrupted insulated jumper.
flags = []

def paired(label, start, end, color=INK, note=''):
    record(label, start, end, note)
    flags.append((label, start, end, color))


def component_resistor(label, start, end, value, color):
    record(label, start, end, f'{value}, 1/4 W; stand body upright; form return lead to reach second hole')
    x,y = parse_hole(start); x2,y2 = parse_hole(end)
    line(x,y,x2,y2,color,2)
    # End-on resistor body with bent return lead, not a false flat-body fit.
    rect(x-7,y+7,14,24,'#edce8c',INK,2)
    for dy,c in [(12,'#673b26'),(18,'#181818'),(24,'#cc771e' if value=='10 kΩ' else '#673b26')]:
        line(x-6,y+dy,x+6,y+dy,c,3)
    for h in (start,end): circle(*parse_hole(h),4,color,'white',1)
    text(x-10,y+16,label,12,color,True,'end')


def cap(label, start, end, value, polarized=False, optional=False):
    record(label, start, end, f'{value}; '+('From is positive, To is negative; ' if polarized else 'nonpolarized; ')+('optional; ' if optional else '')+'form leads gently to fit')
    x,y=parse_hole(start); x2,y2=parse_hole(end)
    line(x,y,x2,y2,POWER,2)
    if polarized:
        rect(x-8,(y+y2)/2-15,16,30,'#23495e',INK,4)
        line(x+4,(y+y2)/2-11,x+4,(y+y2)/2+11,'#d2dde3',3)
        text(x+11,y+10,'+',12,POWER,True)
    else: rect(x-7,(y+y2)/2-12,14,24,'#bb914e','#8d6c35',3)
    for h in (start,end): circle(*parse_hole(h),4,POWER,'white',1)
    text(x+10,(y+y2)/2+5,label,11,MUTED,True)


def board(minimum=False):
    rect(220,214,562,1717,'#e8e9e5','#a9b6ba',18)
    rect(314,233,158,1680,'#fdfcf8','#d2d5d0',4)
    rect(514,233,150,1680,'#fdfcf8','#d2d5d0',4)
    rect(482,241,21,1660,'#c6cbc9','#c6cbc9',3)
    for col in ['L+','L-','R+','R-']:
        x=COL[col]; color='#c57979' if '+' in col else '#7d9ab8'
        if minimum and col.startswith('R'):
            rect(x-8,yy(34)-9,16,yy(64)-yy(34)+18,
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
    if not minimum: drivers()


def drivers():
    for u,first in [('U1',21),('U2',31)]:
        rect(467,yy(first)-11,50,100,'#253b46','#132c38',5)
        s.append(f'<path d="M 479 {yy(first)-11} a 13 9 0 0 0 26 0" fill="#c6cbc9" stroke="#132c38"/>')
        text(492,yy(first)+51,u,17,'white',True,'middle')
        for pin,col,row in [(1,'e',first),(2,'e',first+1),(3,'e',first+2),(4,'e',first+3),(5,'f',first+3),(6,'f',first+2),(7,'f',first+1),(8,'f',first)]:
            x,y=hole(col,row); line(x,y,467 if col=='e' else 517,y,'#b3bec3',5)
            circle(x,y,4,'#d1bb7a',INK,1)
            text(460 if col=='e' else 523,y+4,str(pin),10,INK,anchor='end' if col=='e' else 'start')
            record(f'{u} pin {pin}',f'{col}{row}',f'{u}.{pin}','TC4427ACPA, notch toward USB; pin 1/8 NC')


def output_rows(labelsize=15):
    for row,label,color in [(40,'+12 V',POWER),(41,'G',GREEN),(42,'R',RED),(43,'B',BLUE)]:
        rect(333,yy(row)-11,139,22,'#fff0ce',color,3)
        for col in 'abcde': circle(*hole(col,row),3.8,'#636d6e','#a1aaa9',1)
        text(476,yy(row)+5,label,labelsize,color,True)


def barrel_jack():
    # Downward-facing jack avoids the MOSFETs and sends the plug off the board end.
    record('J0 pin 1 / center','b58','J0.1','Adafruit 373 / PJ-102AH; +12 V only after verifying PSU center-positive polarity')
    record('J0 pin 2 / sleeve','b60','J0.2','Unswitched sleeve / common ground; verify with plug inserted')
    record('J0 pin 3 / switched sleeve','d59','J0.3','Unused; leave all other a-e holes in row 59 empty')
    rect(331,yy(58)-9,90,145,'#303a43',INK,5)
    rect(348,yy(58)+117,56,23,'#141c22','#53636c',4)
    for col,row,label in [('b',58,'1 +'),('b',60,'2 −'),('d',59,'3 NC')]:
        x,y=hole(col,row); circle(x,y,5,'#c9b680',INK,1)
        text(x+10,y+5,label,12,'white' if col=='b' else MUTED,True)
    rect(358,yy(58)+140,36,51,'#363e43',INK,4)
    line(376,yy(58)+191,376,yy(64)+83,INK,6)
    text(444,yy(64)+42,'J0 · opening ↓',16,INK,True)
    text(376,yy(64)+109,'12 V PSU plug',16,MUTED,anchor='middle')


def led_strip():
    # An actual short LED segment, the only output load outside this board.
    rect(65,yy(40)-15,101,224,'#f5eee0','#bbae8f',4)
    text(115,yy(40)-32,'SHORT STRIP',17,INK,True,'middle')
    for idx,(label,color) in enumerate([('+',POWER),('G',GREEN),('R',RED),('B',BLUE)]):
        ry=yy(40+idx)
        rect(137,ry-7,23,14,'#c6a764',color,2)
        text(93,ry+5,label,15,color,True,'middle')
        start=f'a{40+idx}'; record('LED '+label,start,'Strip '+label,'Short segment only; + / G / R / B order verified from strip photo')
        wire([parse_hole(start),(180+idx*11,ry),(160,ry)],color,3)
    for dy in [122,168]:
        rect(94,yy(40)+dy-13,43,28,'#e4e4d9','#978c74',3)
        rect(106,yy(40)+dy-6,19,14,'#f2d75e','#cbb547',2)


def build():
    global s, wiring, occupied
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         '<title>Kitchen lighting: 12 V RGB best-practice breadboard proof of concept</title>',
         '<desc>Nano 33 IoT, two TC4427ACPA drivers, three IRFZ44NPBF MOSFETs and a breadboard barrel jack. Paired wire labels identify both ends of one jumper. Output a40 +12 V, a41 green, a42 red, a43 blue. Only a short 12 V strip segment is connected.</desc>']
    wiring=[]; occupied={}; flags.clear()
    rect(0,0,W,H,'#f4f7fa','#f4f7fa',0)
    text(40,58,'Kitchen lighting · 12 V RGB · best practice',35,bold=True)
    text(40,94,'All components on the board · Nano 33 IoT USB at top · side rails unused',22,MUTED)
    text(2340,55,'REV H · SHORT STRIP PoC',19,'#007d80',True,'end')
    rect(40,117,2300,77,'#fff3dd','#e4cf9f',7)
    text(58,145,'Start with ONE marked cut segment. Maximum test length: 25 cm (0.30 A LED load at 14.4 W/m).',23,INK,True)
    text(58,175,'Use the existing 12 V supply. Its 6 A rating is capacity, not a breadboard fault-current limit. The full spool stays disconnected.',20)
    board()
    # Small local connections are drawn directly. Long wires use paired labels.
    paired('P1','i10','a22',RED,'Nano D3 → U1 pin 2 / red; HIGH=ON')
    paired('P2','i8','a24',GREEN,'Nano D5 → U1 pin 4 / green; HIGH=ON')
    paired('P3','i7','a32',BLUE,'Nano D6 → U2 pin 2 / blue; HIGH=ON')
    for label,start,end in [('L1','a26','a28'),('L2','e26','a23'),('L3','d26','f25'),('L4','a36','a38'),('L5','c36','a33'),('L6','d36','f35'),('L7','e36','a34')]:
        local(label,start,end,INK,'Ground jumper' if label!='L7' else 'Ground U2 unused input pin 4')
    component_resistor('R1','b22','b26','10 kΩ',RED)
    component_resistor('R2','c24','c28','10 kΩ',GREEN)
    component_resistor('R3','b32','b36','10 kΩ',BLUE)
    cap('C3','h23','h25','100 nF, 50 V ceramic')
    cap('C4','i23','i25','4.7 µF, 25 V',True)
    cap('C5','h33','h35','100 nF, 50 V ceramic')
    cap('C6','i33','i35','4.7 µF, 25 V',True)
    output_rows()
    for q,col,row,color in [('Q1','c',47,RED),('Q2','c',52,GREEN),('Q3','g',47,BLUE)]:
        # Front-view G-D-S order becomes top-to-bottom with the face toward a/left.
        x=COL[col]
        rect(x-11,yy(row)-12,22,77,'#37454f',INK,3)
        rect(x-9,yy(row)-21,18,13,'#bdc4c7',INK,1)
        for k,pin in enumerate('GDS'):
            hh=f'{col}{row+k}'; record(f'{q} {pin}',hh,f'{q}.{pin}','IRFZ44NPBF; upright; printed face toward board left; tab is drain')
            circle(*parse_hole(hh),4,'#cfb982',INK,1)
        text(x+18,yy(row)+14,q,14,color,True)
        text(x+18,yy(row)+34,'face ←',10,MUTED)
    for label,start,end,color in [('R4','b45','b47',RED),('R5','b50','b52',GREEN),('R6','i45','i47',BLUE)]:
        component_resistor(label,start,end,'100 Ω',color)
    for label,start,end,color in [('R7','a47','a49',RED),('R8','a52','a54',GREEN),('R9','j47','j49',BLUE)]:
        component_resistor(label,start,end,'10 kΩ',color)
    for label,start,end,color,note in [
        ('G1','j22','a45',RED,'U1 pin 7 → R4 → Q1 gate'),
        ('G2','j24','a50',GREEN,'U1 pin 5 → R5 → Q2 gate'),
        ('G3','j32','j45',BLUE,'U2 pin 7 → R6 → Q3 gate'),
        ('D1','e48','e42',RED,'Q1 drain → red strip output'),
        ('D2','e53','e41',GREEN,'Q2 drain → green strip output'),
        ('D3','h48','e43',BLUE,'Q3 drain → blue strip output'),
        ('S1','d49','g62',INK,'Q1 source → common ground'),
        ('S2','d54','i62',INK,'Q2 source → common ground'),
        ('S3','h49','j62',INK,'Q3 source → common ground'),
        ('V0','e58','f58',POWER,'Jack center +12 V → distribution'),
        ('V1','g58','f60',POWER,'Extend +12 V distribution'),
        ('V2','h58','a15',POWER,'+12 V → Nano VIN'),
        ('V3','i58','j23',POWER,'+12 V → U1 pin 6'),
        ('V4','j58','j33',POWER,'+12 V → U2 pin 6'),
        ('V5','g60','e40',POWER,'+12 V → strip output'),
        ('N0','e60','f56',INK,'Jack unswitched sleeve → common ground'),
        ('N1','g56','a14',INK,'Common ground → Nano GND'),
        ('N2','h56','b28',INK,'Common ground → U1 ground bank'),
        ('N3','i56','b38',INK,'Common ground → U2 ground bank'),
        ('N4','j56','f62',INK,'Extend ground to MOSFET sources')]:
        paired(label,start,end,color,note)
    cap('C7','h60','h62','100 µF, 25 V',True,True)
    barrel_jack()
    led_strip()
    # Flags are offset into margins, with holes still individually identified.
    for label,start,end,color in flags:
        for endpoint in (start,end):
            x,y=parse_hole(endpoint)
            isleft=endpoint[0] in 'abcde'
            # Dedicated tiny hole labels avoid pretending separate leads share one hole.
            dx=-18 if isleft else 18
            circle(x,y,5,color,'white',1.5)
            line(x,y,x+dx,y,color,2)
            tx=x+dx-3 if isleft else x+dx+3
            text(tx,y-5,label,10,color,True,'end' if isleft else 'start')
    text(502,2054,'All four side rails unused',18,MUTED,True,'middle')
    # Right-hand legend makes every paired wire and exact lead placement explicit.
    panel(850,214,1490,690,'Read this as a physical top view')
    paragraphs=[
        'A label at two holes means ONE insulated jumper between those holes.',
        'For example, P1 is i10 ↔ a22. The jumper table below lists both ends of each wire.',
        'a–e connect across each row; f–j connect across each row. The trench isolates them.',
        'Nano: c1–c15 / g1–g15. U1 and U2 notches point UP toward the USB socket.',
        'U1: e21=1, e22=2, e23=3, e24=4; f24=5, f23=6, f22=7, f21=8.',
        'U2: e31=1, e32=2, e33=3, e34=4; f34=5, f33=6, f32=7, f31=8.',
        'Pins 1/8 are NC. U2 pin 4 is grounded; U2 pin 5 is left unconnected.',
        'C3/C5 = 100 nF. C4/C6 = 4.7 µF / 25 V, + at i23/i33; − at i25/i35.',
        'R1–R3 and R7–R9 = 10 kΩ. R4–R6 = 100 Ω. All are ¼ W.',
        'Use upright axial resistors; bend each return lead down to its listed second hole.',
        'Q1: G c47, D c48, S c49.  Q2: G c52, D c53, S c54.',
        'Q3: G g47, D g48, S g49. Printed fronts face LEFT; packages stand upright.',
        'J0: center pin 1 b58; sleeve pin 2 b60; switched pin 3 d59 is UNUSED.',
        'Jack opening faces DOWN. Gently form its non-grid leads; do not force the body.',
        'Power jumpers leave at e58/e60, clear of J0. Leave row 59 left bank isolated.',
        'C7 is optional: 100 µF / 25 V; + h60, − h62. Form its leads as needed.'
    ]
    for idx,p in enumerate(paragraphs): text(875,290+idx*36,p,19,INK if idx<12 else MUTED)
    panel(850,925,1490,658,'Jumper list · plug one end into each listed hole')
    # Table: 23 paired jumpers plus the local short wires in two readable columns.
    entries=[(label,start,end,color) for label,start,end,color in flags]
    entries += [(label,start,end,INK) for label,start,end in [('L1','a26','a28'),('L2','e26','a23'),('L3','d26','f25'),('L4','a36','a38'),('L5','c36','a33'),('L6','d36','f35'),('L7','e36','a34')]]
    for idx,(label,start,end,color) in enumerate(entries):
        column=idx//15; row=idx%15; x=880+column*710; y=1009+row*35
        text(x,y,label,19,color,True)
        text(x+60,y,f'{start:>3}  ↔  {end:<3}',19,INK,mono=True)
        # Notes are a short, useful function rather than long electrical explanations.
        function=next((r[3] for r in wiring if r[0]==label),'').split(';')[0]
        function=function.replace('Common ground','GND').replace('common ground','GND').replace('distribution','bus')
        text(x+263,y,function,16,MUTED)
    panel(850,1603,1490,447,'Orientation check before inserting the MOSFETs')
    # Front view, explicitly an orientation inset and not another installed component.
    rect(891,1680,119,133,'#35424d',INK,5)
    rect(896,1659,109,43,'#c1c9cd',INK,3)
    circle(950,1676,9,'#f4f7fa',INK,2)
    text(950,1738,'IRFZ44N',17,'white',True,'middle')
    text(950,1765,'FRONT',15,'white',True,'middle')
    for x,label in [(910,'G'),(950,'D'),(990,'S')]:
        line(x,1813,x,1868,'#88969d',7); text(x,1895,label,20,INK,True,'middle')
    text(1045,1687,'Front view: G · D · S, left to right. Metal tab = drain.',21,INK,True)
    text(1045,1731,'On this board, turn the printed front toward the a / left edge.',20)
    text(1045,1775,'Then the gate goes in the smallest row number, source in the largest.',20)
    text(1045,1819,'The narrow rectangles on the board are the upright packages seen edge-on.',20)
    text(1045,1863,'Their three leads MUST occupy three separate rows, never one row.',20,RED,True)
    text(875,1933,'TO-220 leads may be too thick for some breadboards. Insert only if they seat normally;',20,MUTED)
    text(875,1970,'do not force them. Use suitable thin-pin adapters if needed; package sizes are illustrative.',20,MUTED)
    text(875,2011,'The jack also needs small lead bends: its actual pin spacing is 3 / 6 mm, not 2.54 / 5.08 mm.',19,MUTED)
    panel(40,2080,2300,237,'Before power-up')
    text(64,2152,'Power OFF before rewiring. Check for shorts, electrolytic polarity, and center-positive 12 V at the jack before connecting the board.',21,INK,True)
    text(64,2192,'Start with one cut segment; measure actual current before extending to ≤25 cm. The 0.30 A figure covers LEDs, plus Nano/driver current.',20)
    text(64,2232,'USB-only programming with 12 V off: unplug P1 / P2 / P3 at i10 / i8 / i7. Keep all three MOSFET tabs from touching other leads.',20)
    text(64,2272,'5 V strip, buck converter and level shifter are not installed. L7805CV regulators and the original controller are not used.',20,MUTED)
    text(42,2353,'REV H · 12 OCT 2026 · Short-strip proof of concept. Final full-strip wiring needs a current-rated PCB or soldered assembly.',17,MUTED)
    record('Load limit','12 V 6 A PSU','One cut segment initially; no more than 25 cm','14.4 W/m × 0.25 m ÷ 12 V = 0.30 A LED current; plus Nano/drivers. PSU capacity is not fault protection. Verify actual current.')
    record('USB-only programming','12 V off','Unplug i10 / i8 / i7','Avoid driving unpowered TC4427A inputs')
    record('J0 polarity check','PSU plug center','Positive 12 V relative to sleeve','Check with meter before connection; reverse-polarity adapters cannot be used as drawn')
    record('Mechanical fit','TO-220 and barrel jack leads','No force; form gently / use suitable pin adapters','J0 is not an exact 2.54 mm grid footprint. 10 kΩ and 100 Ω resistors mount upright. Jack feeds at e58/e60 clear its body; verify mechanical fit before wiring.')
    s.append('</svg>')
    target = OUT / (NAME + '.svg')
    target.write_text('\n'.join(s), encoding='utf-8')
    print(f'Generated {target}; {len(occupied)} unique occupied holes checked.')


minimum_jumpers=[]


def minimum_mosfets():
    # TN0702 front-view pin order is S-G-D, unlike the IRFZ44N's G-D-S.
    # Flat face toward board left makes S-G-D run from smaller to larger row.
    for q,col,first,color in [('Q1','c',47,RED),('Q2','c',52,GREEN),('Q3','g',47,BLUE)]:
        x=COL[col]; y=yy(first+1)
        for offset in (-1,1):
            line(x,y+offset*13,x,y+offset*26,'#88969d',3)
        s.append(f'<path d="M {x-12} {y-18} L {x-12} {y+18} Q {x+15} {y+18} {x+15} {y} Q {x+15} {y-18} {x-12} {y-18} Z" fill="#37454f" stroke="{INK}" stroke-width="2"/>')
        for k,pin in enumerate('SGD'):
            endpoint=f'{col}{first+k}'
            record(f'{q} {pin}',endpoint,f'{q}.{pin}','TN0702N3-G TO-92; flat face toward board left; pins 1/2/3 = source/gate/drain')
            circle(*parse_hole(endpoint),4,'#cfb982',INK,1)
            text(x-18,yy(first+k)+4,pin,11,INK,True,'end')
        text(x+22,y+4,q,14,color,True)
        text(x+22,y+21,'face ←',10,MUTED)


def draw_minimum_jumpers():
    bends={
        'P1': [(650,yy(10)),(650,yy(17)),(326,yy(17)),(326,yy(48))],
        'P2': [(662,yy(8)),(662,yy(18)),(338,yy(18)),(338,yy(53))],
        'P3': [(770,yy(7)),(770,yy(48))],
        'D1': [(466,yy(49)),(466,yy(42))],
        'D2': [(518,yy(54)),(518,yy(41)-13),(454,yy(41)-13)],
        'D3': [(584,yy(49)+13),(506,yy(49)+13),(506,yy(43)-13),(454,yy(43)-13)],
        'S1': [(454,yy(45))],
        'V1': [(310,yy(15)),(310,yy(36))],
        'V2': [(454,yy(40)-16),(714,yy(40)-16)],
        'N1': [(794,yy(12)),(794,yy(38))],
    }
    labels={
        'P1': (349,850), 'P2': (349,1000), 'P3': (778,900),
        'D1': (472,1440), 'D2': (525,1570), 'D3': (533,yy(49)+34),
        'S1': (627,yy(45)-9), 'S2': (627,yy(52)-9), 'S3': (675,yy(47)-9),
        'V0': (565,yy(58)-9), 'V1': (565,yy(36)-9), 'V2': (565,yy(40)-25),
        'N0': (565,yy(60)-9), 'N1': (801,1090),
    }
    for label,start,end,color,note in minimum_jumpers:
        s.append(f'<g id="jumper-{label}" data-start="{start}" data-end="{end}">')
        s.append(f'<title>{escape(f"{label}: {start} → {end}. {note}")}</title>')
        wire([parse_hole(start),*bends.get(label,()),parse_hole(end)],color,4)
        s.append('</g>')
    for label,start,end,color,note in minimum_jumpers:
        for endpoint in (start,end): circle(*parse_hole(endpoint),6,color,'white',2)
    for label,start,end,color,note in minimum_jumpers:
        x,y=labels[label]
        rect(x-2,y-12,24,16,'#f5f7fa','none',2)
        text(x,y,label,12,color,True)


def build_minimum():
    global s,wiring,occupied
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>Kitchen lighting: 12 V RGB minimum breadboard layout</title>',
       '<desc>Minimum short-strip experiment using an Arduino Nano 33 IoT, three TN0702N3-G logic-level N-channel MOSFETs, and barrel jack J0. Nano D3, D5 and D6 directly control red, green and blue MOSFET gates. No gate drivers, resistors or capacitors are installed. J0 feeds Nano VIN and strip positive in parallel through the lower right power rails. The strip returns through the MOSFETs, never through Nano GPIO. All wires are drawn.</desc>']
    wiring=[]; occupied={}; flags.clear(); minimum_jumpers.clear()
    rect(0,0,W,H,'#f4f7fa','#f4f7fa',0)
    text(40,58,'Kitchen lighting · 12 V RGB · minimum',35,bold=True)
    text(40,94,'Nano 33 IoT + three TN0702 MOSFETs + barrel jack · lower right rails · every jumper drawn',22,MUTED)
    text(2340,55,'12 V · MINIMUM PoC',19,'#007d80',True,'end')
    rect(40,117,2300,77,'#fff3dd','#e4cf9f',7)
    text(58,145,'Use TN0702N3-G MOSFETs for direct 3.3 V gate drive. The best-practice IRFZ44N parts are not substitutes here.',22,INK,True)
    text(58,175,'Start with one cut segment; at most 25 cm / 0.30 A total LED current. These small MOSFETs are for the short test, not the full strip.',20)
    board(minimum=True)
    output_rows(labelsize=13)
    minimum_mosfets()
    barrel_jack()
    led_strip()
    for label,start,end,color,note in [
        ('P1','i10','a48',RED,'Nano D3 → Q1 gate / red'),
        ('P2','i8','a53',GREEN,'Nano D5 → Q2 gate / green'),
        ('P3','i7','j48',BLUE,'Nano D6 → Q3 gate / blue'),
        ('D1','e49','e42',RED,'Q1 drain → strip R'),
        ('D2','e54','e41',GREEN,'Q2 drain → strip G'),
        ('D3','h49','e43',BLUE,'Q3 drain → strip B'),
        ('S1','e47','R-45',INK,'Q1 source → ground rail'),
        ('S2','e52','R-52',INK,'Q2 source → ground rail'),
        ('S3','j47','R-47',INK,'Q3 source → ground rail'),
        ('V0','e58','R+58',POWER,'J0 center → +12 V rail'),
        ('V1','a15','R+36',POWER,'+12 V rail → Nano VIN'),
        ('V2','e40','R+40',POWER,'+12 V rail → strip +'),
        ('N0','e60','R-60',INK,'J0 sleeve → ground rail'),
        ('N1','i12','R-38',INK,'Nano GND → ground rail'),
    ]:
        record(label,start,end,note)
        minimum_jumpers.append((label,start,end,color,note))
    draw_minimum_jumpers()
    text(502,2054,'Lower right rails only · + = 12 V · − = GND',16,MUTED,True,'middle')

    panel(850,214,1490,690,'Minimum build · component locations')
    notes=[
        'Keep the Nano, J0 barrel jack, three TN0702N3-G MOSFETs and a short RGB strip.',
        'Omit U1 / U2, all nine resistors and all five external capacitors.',
        'Q1 / Q2 / Q3 change from IRFZ44N to TN0702N3-G, a small TO-92 part.',
        'Nano: c1–c15 / g1–g15; USB at top. D3 = red, D5 = green, D6 = blue.',
        'TN0702 pins, facing the flat front with legs down: 1 SOURCE, 2 GATE, 3 DRAIN.',
        'Installed flat fronts face LEFT (a-side); S / G / D run top to bottom.',
        'Q1 red: S c47, G c48, D c49.  Q2 green: S c52, G c53, D c54.',
        'Q3 blue: S g47, G g48, D g49. Spread the leads gently to 2.54 mm row spacing.',
        'Every MOSFET lead must occupy a separate row. Their pin order differs from IRFZ44N.',
        'J0: positive b58, ground b60, unused switched contact d59; opening faces DOWN.',
        'Keep all other a–e59 holes empty. Verify the PSU is center-positive 12 V.',
        'Strip output: a40 +12 V, a41 G, a42 R, a43 B.',
        'Use only lower right rail rows 34–64; no rail bridges or left/right links are needed.',
        'Dots mark plugged ends. Insulated wires crossing other wires do not connect.',
        'a–e connect within a row; f–j connect within a row. The trench separates them.',
    ]
    for idx,note in enumerate(notes): text(875,290+idx*38,note,19,INK if idx<12 else MUTED)

    panel(850,925,1490,658,'Fourteen jumpers · R+ = right + rail · R− = right − rail')
    for idx,(label,start,end,color,note) in enumerate(minimum_jumpers):
        y=1009+idx*36
        text(880,y,label,20,color,True)
        text(955,y,f'{start:>4} ↔ {end:<4}',19,INK,mono=True)
        text(1150,y,note,20,MUTED)

    panel(850,1603,1490,447,'TN0702 orientation and direct gate drive')
    rect(893,1674,114,123,'#35424d',INK,12)
    text(950,1716,'TN0702',16,'white',True,'middle')
    text(950,1744,'FLAT',14,'white',True,'middle')
    text(950,1767,'FRONT',14,'white',True,'middle')
    for x,pin,name in [(910,'1','S'),(950,'2','G'),(990,'3','D')]:
        line(x,1797,x,1840,'#88969d',4)
        text(x,1863,pin,15,INK,True,'middle')
        text(x,1889,name,19,INK,True,'middle')
    text(1045,1687,'Front view: SOURCE · GATE · DRAIN, left to right.',21,INK,True)
    text(1045,1728,'Turn the flat face toward the a / left edge of the board.',20)
    text(1045,1769,'TN0702 has a specified on-resistance at a 3 V gate voltage.',20)
    text(1045,1810,'Use the small test load: about 0.10 A per colour, 0.30 A total.',20)
    text(1045,1851,'GPIO HIGH = channel ON; use normal low-frequency PWM.',20)
    text(875,1933,'No pull-downs: gates can float during reset or boot, so the strip may light unpredictably.',19,MUTED)
    text(875,1969,'J0 powers Nano VIN and the strip in parallel. Keep 12 V off every GPIO, 3V3 and VUSB.',19,MUTED)
    s.append('<a href="https://www.microchip.com/content/dam/mchp/documents/APID/ProductDocuments/DataSheets/TN0702-N-Channel-Enhancement-Mode-Vertical-DMOS-FET-Data-Sheet-20005941A.pdf">')
    text(875,2011,'Source: Microchip TN0702 datasheet · electrical limits and package pinout',17,BLUE)
    s.append('</a>')

    panel(40,2080,2300,237,'Connection check')
    text(64,2152,'Use regulated 12 V, center positive. Check the MOSFET S / G / D order and rail polarity before power-up.',21,INK,True)
    text(64,2192,'The strip already contains its LED current-limiting resistors. Its R / G / B wires go to MOSFET drains, never directly to Nano GPIO.',20)
    text(64,2232,'Start with one cut segment; measure current before increasing to 25 cm. The full 160-inch strip needs different power hardware.',20)
    text(64,2272,'All strip current returns through the MOSFET sources to J0 ground. The Nano supplies gate signals only.',20,MUTED)
    text(42,2353,'12 V MINIMUM REV A · 12 OCT 2026 · Three TN0702N3-G MOSFETs · Barrel jack retained · No external resistors, capacitors or drivers.',17,MUTED)
    record('Load limit','12 V 6 A PSU','One cut segment initially; no more than 25 cm','14.4 W/m × 0.25 m ÷ 12 V = 0.30 A total LED current; about 0.10 A per colour. TN0702 is only selected for this short load.')
    record('J0 polarity check','PSU plug center','Positive 12 V relative to sleeve','Check before connecting; J0 feeds Nano VIN and strip + in parallel')
    s.append('</svg>')
    target=OUT/(MINIMUM_NAME+'.svg')
    target.write_text('\n'.join(s),encoding='utf-8')
    print(f'Generated {target}; {len(occupied)} unique occupied holes checked.')
    return target


if __name__ == '__main__':
    build()
    build_minimum()
