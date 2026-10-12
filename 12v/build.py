#!/usr/bin/env python3
"""Generate best-practice and minimum 12 V kitchen-lighting SVG diagrams.

From the project root: python3 12v/build.py
Both SVGs are written beside this script. Only Python's standard library is used.
The minimum uses three TN0702N3-G MOSFETs and the lower right power rails.
Both layouts feed strip positive directly from a soldered pigtail on J0 pin 1.
"""
from html import escape
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
NAME = 'best'
MINIMUM_NAME = 'min'
W, H = 880, 2150
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
annotations = []

def rect(x,y,w,h,fill='white',stroke=BORDER,r=10):
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

def text(x,y,value,size=20,color=INK,bold=False,anchor='start',mono=False):
    font='DejaVu Sans Mono' if mono else 'DejaVu Sans'
    s.append(f'<text x="{x}" y="{y}" font-family="{font},sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{anchor}">{escape(value)}</text>')

def component_label(x,y,value,size=16,color=INK,anchor='start',rotate=0):
    """Keep component names readable above wire crossings without a legend."""
    transform=f' transform="rotate({rotate} {x} {y})"' if rotate else ''
    attrs=f'x="{x}" y="{y}"{transform} font-family="DejaVu Sans,sans-serif" font-size="{size}" font-weight="600" text-anchor="{anchor}"'
    annotations.append(f'<text {attrs} fill="#f4f7fa" stroke="#f4f7fa" stroke-width="4" stroke-linejoin="round" aria-hidden="true">{escape(value)}</text>')
    annotations.append(f'<text {attrs} fill="{color}">{escape(value)}</text>')


def line(x1,y1,x2,y2,color=INK,width=2):
    s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')

def circle(x,y,r=5,fill='white',stroke=INK,width=2):
    s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

def wire(points,color,width=5):
    pts=' '.join(f'{x},{y}' for x,y in points)
    for sw,co in [(width+5,'#f5f7fa'),(width,color)]:
        s.append(f'<polyline points="{pts}" fill="none" stroke="{co}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')
    for x,y in (points[0],points[-1]): circle(x,y,6,color,'white',2)

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
    s.append(f'<g id="jumper-{label}" data-start="{start}" data-end="{end}"><title>{escape(note)}</title>')
    wire([parse_hole(start), *via, parse_hole(end)], color, 3)
    s.append('</g>')


# Store jumper endpoints so their continuous paths can be routed around parts.
flags = []

def paired(label, start, end, color=INK, note=''):
    record(label, start, end, note)
    flags.append((label, start, end, color))


def component_resistor(ref, start, end, value, color):
    record(ref, start, end, f'{value}, 1/4 W; stand body upright; form return lead to reach second hole')
    x,y = parse_hole(start); x2,y2 = parse_hole(end)
    line(x,y,x2,y2,color,2)
    # End-on resistor body with bent return lead, not a false flat-body fit.
    rect(x-7,y+7,14,24,'#edce8c',INK,2)
    for dy,c in [(12,'#673b26'),(18,'#181818'),(24,'#cc771e' if value=='10 kΩ' else '#673b26')]:
        line(x-6,y+dy,x+6,y+dy,c,3)
    for h in (start,end): circle(*parse_hole(h),4,color,'white',1)
    component_label(x-13,(y+y2)/2,value.replace(' ',''),16,color,'middle',-90)


def cap(ref, start, end, value, polarized=False, optional=False):
    record(ref, start, end, f'{value}; '+('From is positive, To is negative; ' if polarized else 'nonpolarized; ')+('optional; ' if optional else '')+'form leads gently to fit')
    x,y=parse_hole(start); x2,y2=parse_hole(end)
    line(x,y,x2,y2,POWER,2)
    if polarized:
        rect(x-8,(y+y2)/2-15,16,30,'#23495e',INK,4)
        line(x+4,(y+y2)/2-11,x+4,(y+y2)/2+11,'#d2dde3',3)
        component_label(x-11,y+10,'+',13,POWER,'middle')
    else: rect(x-7,(y+y2)/2-12,14,24,'#bb914e','#8d6c35',3)
    for h in (start,end): circle(*parse_hole(h),4,POWER,'white',1)
    displayed=value.split(',')[0].replace(' ','')
    if polarized: displayed+=' / 25V'
    component_label(x+23 if polarized else x-14,(y+y2)/2,displayed,16,INK,'middle',-90)
    if optional: component_label(x+44,(y+y2)/2,'optional',12,MUTED,'middle',-90)


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
        rect(467,yy(first)-28,50,134,'#253b46','#132c38',5)
        s.append(f'<path d="M 479 {yy(first)-28} a 13 9 0 0 0 26 0" fill="#c6cbc9" stroke="#132c38"/>')
        s.append(f'<text x="492" y="{yy(first)+40}" transform="rotate(-90 492 {yy(first)+40})" text-anchor="middle" dominant-baseline="middle" font-family="DejaVu Sans,sans-serif" font-size="17" fill="white">TC4427ACPA</text>')
        for pin,col,row in [(1,'e',first),(2,'e',first+1),(3,'e',first+2),(4,'e',first+3),(5,'f',first+3),(6,'f',first+2),(7,'f',first+1),(8,'f',first)]:
            x,y=hole(col,row); line(x,y,467 if col=='e' else 517,y,'#b3bec3',5)
            circle(x,y,4,'#d1bb7a',INK,1)
            text(460 if col=='e' else 523,y+4,str(pin),10,INK,anchor='end' if col=='e' else 'start')
            record(f'{u} pin {pin}',f'{col}{row}',f'{u}.{pin}','TC4427ACPA, notch toward USB; pin 1/8 NC')


def output_rows(labelsize=15):
    # Row 40 is unused: strip positive bypasses all breadboard contacts.
    text(476,yy(40)+5,'unused',11,MUTED)
    for row,label,color in [(41,'G',GREEN),(42,'R',RED),(43,'B',BLUE)]:
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
    text(444,yy(64)+42,'PJ-102AH',18,INK,True)
    text(376,yy(64)+109,'12 V · centre positive',16,MUTED,anchor='middle')


def led_strip():
    # Solder the positive pigtail to the actual jack terminal, not a row-58 hole.
    rect(65,yy(40)-15,101,224,'#f5eee0','#bbae8f',4)
    text(115,yy(40)-32,'RGB strip',17,INK,True,'middle')
    for idx,(label,color) in enumerate([('+',POWER),('G',GREEN),('R',RED),('B',BLUE)]):
        ry=yy(40+idx)
        rect(137,ry-7,23,14,'#c6a764',color,2)
        text(93,ry+5,label,15,color,True,'middle')
        if label == '+':
            record('LED +','J0.1','Strip +','Insulated wire soldered directly to jack pin 1 / center-positive terminal; bypasses breadboard contacts; row 40 unused')
            s.append('<g id="strip-positive-bypass" data-start="J0.1" data-end="Strip +"><title>Soldered pigtail from actual J0 pin 1 to strip +; not a breadboard jumper</title>')
            wire([hole('b',58),(210,yy(58)),(210,ry),(160,ry)],color,5)
            s.append('</g>')
        else:
            start=f'a{40+idx}'; record('LED '+label,start,'Strip '+label,'Short segment only; colour return still passes through breadboard contacts')
            wire([parse_hole(start),(180+idx*11,ry),(160,ry)],color,3)
    for dy in [122,168]:
        rect(94,yy(40)+dy-13,43,28,'#e4e4d9','#978c74',3)
        rect(106,yy(40)+dy-6,19,14,'#f2d75e','#cbb547',2)


def mosfet_name(x,y,color,part):
    if x==COL['c']:
        component_label(40,y+75,part,17,color)
        line(182,y+71,215,y+71,MUTED,1)
        line(215,y+71,x-12,y+13,MUTED,1)
    else:
        component_label(856,y+27,part,17,color,'middle',-90)
        line(x+13,y+13,837,y+13,MUTED,1)
    component_label(x,y+82,'face ←',12,MUTED,'middle')


def draw_best_jumpers():
    bends={
        'P1': [(650,yy(10)),(650,yy(17)),(326,yy(17)),(326,yy(22))],
        'P2': [(662,yy(8)),(662,yy(18)),(338,yy(18)),(338,yy(24))],
        'P3': [(770,yy(7)),(770,yy(19)),(314,yy(19)),(314,yy(32))],
        'G1': [(698,yy(22)),(698,1160),(326,1160),(326,yy(45))],
        'G2': [(710,yy(24)),(710,1186),(338,1186),(338,yy(50))],
        'G3': [(722,yy(32)),(722,yy(45))],
        'D1': [(466,yy(48)),(466,yy(42))],
        'D2': [(518,yy(53)),(518,yy(41)-13),(454,yy(41)-13)],
        'D3': [(584,yy(48)+13),(506,yy(48)+13),(506,yy(43)-13),(454,yy(43)-13)],
        'S1': [(440,yy(49)),(440,yy(61)),(558,yy(61))],
        'S2': [(452,yy(54)),(452,yy(61)+13),(610,yy(61)+13)],
        'S3': [(596,yy(49)),(596,yy(62))],
        'V1': [(558,yy(59)),(532,yy(59))],
        'V2': [(584,yy(58)-13),(808,yy(58)-13),(808,yy(16)),(310,yy(16)),(310,yy(15))],
        'V3': [(610,yy(57)),(796,yy(57)),(796,yy(23))],
        'V4': [(636,yy(58)+13),(784,yy(58)+13),(784,yy(33))],
        'N0': [(478,yy(60)),(478,yy(56))],
        'N1': [(820,yy(56)),(820,yy(16)+13),(298,yy(16)+13),(298,yy(14))],
        'N2': [(584,yy(56)-13),(748,yy(56)-13),(748,yy(29)),(326,yy(29)),(326,yy(28))],
        'N3': [(610,yy(55)),(736,yy(55)),(736,yy(39)-13),(302,yy(39)-13),(302,yy(38))],
        'N4': [(760,yy(56)),(760,yy(63)),(532,yy(63))],
    }
    for ref,start,end,color in flags:
        note=next(item[3] for item in wiring if item[0]==ref)
        s.append(f'<g id="jumper-{ref}" data-start="{start}" data-end="{end}"><title>{escape(note)}</title>')
        wire([parse_hole(start),*bends.get(ref,()),parse_hole(end)],color,4)
        s.append('</g>')
    for _,start,end,color in flags:
        for endpoint in (start,end): circle(*parse_hole(endpoint),6,color,'white',2)


def build():
    global s, wiring, occupied
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         '<title>Kitchen lighting: 12 V RGB best-practice breadboard proof of concept</title>',
         '<desc>Nano 33 IoT, two TC4427ACPA drivers, three IRFZ44NPBF MOSFETs and barrel jack J0. A soldered pigtail connects J0 pin 1 directly to strip positive, bypassing all breadboard contacts. Row 40 is unused; a41 green, a42 red and a43 blue are the strip returns. Return current still passes through the breadboard; only a short strip segment is connected.</desc>']
    wiring=[]; occupied={}; flags.clear(); annotations.clear()
    rect(0,0,W,H,'#f4f7fa','#f4f7fa',0)
    text(40,62,'12 V · Best practice',34,bold=True)
    text(40,108,'RGB strip · ≤25 cm · ≤0.30 A total LED current',20,MUTED)
    board()
    # Endpoints remain fixed; all jumpers are drawn as continuous paths.
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
        for k,pin in enumerate('GDS'): component_label(x+17,yy(row+k)+4,pin,12,color)
        mosfet_name(x,yy(row),color,'IRFZ44NPBF')
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
        ('N0','e60','f56',INK,'Jack unswitched sleeve → common ground'),
        ('N1','g56','a14',INK,'Common ground → Nano GND'),
        ('N2','h56','b28',INK,'Common ground → U1 ground bank'),
        ('N3','i56','b38',INK,'Common ground → U2 ground bank'),
        ('N4','j56','f62',INK,'Extend ground to MOSFET sources')]:
        paired(label,start,end,color,note)
    cap('C7','h60','h62','100 µF, 25 V',True,True)
    barrel_jack()
    led_strip()
    draw_best_jumpers()
    s.extend(annotations)
    text(40,2096,'USB programming with 12 V off: disconnect D3, D5 and D6.',17,MUTED)
    text(40,2126,'Positive bypass only; RGB returns still use the breadboard. Not a 4 A layout.',16,MUTED)
    record('Load limit','12 V 6 A PSU','One cut segment initially; no more than 25 cm','14.4 W/m × 0.25 m ÷ 12 V = 0.30 A LED current; plus Nano/drivers. PSU capacity is not fault protection. Verify actual current.')
    record('USB-only programming','12 V off','Unplug i10 / i8 / i7','Avoid driving unpowered TC4427A inputs')
    record('J0 polarity check','PSU plug center','Positive 12 V relative to sleeve','Check with meter before connection; reverse-polarity adapters cannot be used as drawn')
    record('Mechanical fit','TO-220 and barrel jack leads','No force; form gently / use suitable pin adapters','J0 is not an exact 2.54 mm grid footprint. 10 kΩ and 100 Ω resistors mount upright. Jack feeds at e58/e60 clear its body; verify mechanical fit before wiring.')
    check_strip_positive_bypass()
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
        mosfet_name(x,yy(first),color,'TN0702N3-G')


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
        'N1': [(794,yy(12)),(794,yy(38))],
    }
    for label,start,end,color,note in minimum_jumpers:
        s.append(f'<g id="jumper-{label}" data-start="{start}" data-end="{end}">')
        s.append(f'<title>{escape(f"{label}: {start} → {end}. {note}")}</title>')
        wire([parse_hole(start),*bends.get(label,()),parse_hole(end)],color,4)
        s.append('</g>')
    for label,start,end,color,note in minimum_jumpers:
        for endpoint in (start,end): circle(*parse_hole(endpoint),6,color,'white',2)


def build_minimum():
    global s,wiring,occupied
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>Kitchen lighting: 12 V RGB minimum breadboard layout</title>',
       '<desc>Minimum short-strip experiment using an Arduino Nano 33 IoT, three TN0702N3-G logic-level N-channel MOSFETs, and barrel jack J0. Nano D3, D5 and D6 directly control red, green and blue MOSFET gates. No gate drivers, resistors or capacitors are installed. Strip positive connects directly to J0 pin 1 by a soldered pigtail; row 40 is unused. The lower right power rails supply Nano VIN and common ground. Strip returns still pass through breadboard contacts and MOSFETs, never through Nano GPIO. All wires are drawn.</desc>']
    wiring=[]; occupied={}; flags.clear(); annotations.clear(); minimum_jumpers.clear()
    rect(0,0,W,H,'#f4f7fa','#f4f7fa',0)
    text(40,62,'12 V · Minimum',34,bold=True)
    text(40,108,'RGB strip · ≤25 cm · ≤0.30 A total LED current',20,MUTED)
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
        ('N0','e60','R-60',INK,'J0 sleeve → ground rail'),
        ('N1','i12','R-38',INK,'Nano GND → ground rail'),
    ]:
        record(label,start,end,note)
        minimum_jumpers.append((label,start,end,color,note))
    draw_minimum_jumpers()
    s.extend(annotations)
    text(40,2096,'Positive bypass only; RGB returns still use the breadboard.',17,MUTED)
    text(40,2126,'TN0702 MOSFETs and return wiring remain for the short test load only.',16,MUTED)
    record('Load limit','12 V 6 A PSU','One cut segment initially; no more than 25 cm','14.4 W/m × 0.25 m ÷ 12 V = 0.30 A total LED current; about 0.10 A per colour. TN0702 is only selected for this short load.')
    record('J0 polarity check','PSU plug center','Positive 12 V relative to sleeve','Check before connecting; J0 feeds Nano VIN and strip + in parallel')
    check_strip_positive_bypass()
    s.append('</svg>')
    target=OUT/(MINIMUM_NAME+'.svg')
    target.write_text('\n'.join(s),encoding='utf-8')
    print(f'Generated {target}; {len(occupied)} unique occupied holes checked.')
    return target


def check_strip_positive_bypass():
    """Keep strip positive off board contacts when regenerating either layout."""
    assert [(start,end) for label,start,end,_ in wiring if label == 'LED +'] == [('J0.1','Strip +')]
    assert not any(re.fullmatch(r'[a-j]40',endpoint) for _,start,end,_ in wiring for endpoint in (start,end))
    assert ('J0 pin 1 / center','b58','J0.1') in [entry[:3] for entry in wiring]
    for colour,row in [('G',41),('R',42),('B',43)]:
        assert any(label == 'LED '+colour and start == f'a{row}' and end == 'Strip '+colour for label,start,end,_ in wiring)


if __name__ == '__main__':
    build()
    build_minimum()
