#!/usr/bin/env python3
"""Generate best-practice and minimum 12 V kitchen-lighting SVG diagrams.

From the project root: python3 12v/build.py
Both SVGs and min.csv/best.csv (DigiKey purchase lists) are written beside this script.
Only Python's standard library is used.
Best uses IRFZ44NPBF MOSFETs with TC4427ACPA gate drivers.
Minimum uses AO3400A MOSFETs on 0.1-inch SIP adapters with 2.2 kohm series
gate resistors and no pulldowns. It stacks the adapters on the right and routes
Nano PWM outside the rails; drivers and their bypass capacitors are best-only.
Both layouts feed output positive from a soldered pigtail on J0 pin 1.
The minimum adds two parallel RJ11 outputs with conceptual breadboard mounting.
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
    bands = ('#c0383c','#c0383c','#c0383c') if value=='2.2 kΩ' else (
        '#673b26','#181818','#cc771e' if value=='10 kΩ' else '#673b26')
    for dy,c in zip((12,18,24),bands):
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
        for start,end in [(1,31),(34,64)]:
            rect(x-8,yy(start)-9,16,yy(end)-yy(start)+18,
                 '#f6ddd3' if '+' in col else '#dce4ea','none',5)
            line(x-11,yy(start)-12,x-11,yy(end)+12,color,2)
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


def drivers(positions=(('U1',21),('U2',31))):
    for u,first in positions:
        rect(467,yy(first)-28,50,134,'#253b46','#132c38',5)
        s.append(f'<path d="M 479 {yy(first)-28} a 13 9 0 0 0 26 0" fill="#c6cbc9" stroke="#132c38"/>')
        s.append(f'<text x="492" y="{yy(first)+40}" transform="rotate(-90 492 {yy(first)+40})" text-anchor="middle" dominant-baseline="middle" font-family="DejaVu Sans,sans-serif" font-size="17" fill="white">TC4427ACPA</text>')
        for pin,col,row in [(1,'e',first),(2,'e',first+1),(3,'e',first+2),(4,'e',first+3),(5,'f',first+3),(6,'f',first+2),(7,'f',first+1),(8,'f',first)]:
            x,y=hole(col,row); line(x,y,467 if col=='e' else 517,y,'#b3bec3',5)
            circle(x,y,4,'#d1bb7a',INK,1)
            text(460 if col=='e' else 523,y+4,str(pin),10,INK,anchor='end' if col=='e' else 'start')
            record(f'{u} pin {pin}',f'{col}{row}',f'{u}.{pin}','TC4427ACPA, notch toward USB; pin 1/8 NC')


def output_rows(labelsize=15, rows=((41,'G',GREEN),(42,'R',RED),(43,'B',BLUE)), show_unused=True):
    # Row 40 is unused: strip positive bypasses all breadboard contacts.
    if show_unused: text(476,yy(40)+5,'unused',11,MUTED)
    for row,label,color in rows:
        rect(333,yy(row)-11,139,22,'#fff0ce',color,3)
        for col in 'abcde': circle(*hole(col,row),3.8,'#636d6e','#a1aaa9',1)
        text(476,yy(row)+5,label,labelsize,color,True)


def barrel_jack(shift_right=False):
    # Downward-facing jack avoids the MOSFETs and sends the plug off the board end.
    main_col, nc_col, dx = ('c','e',26) if shift_right else ('b','d',0)
    record('J0 pin 1 / center',f'{main_col}58','J0.1','Adafruit 373 / PJ-102AH; +12 V only after verifying PSU center-positive polarity')
    record('J0 pin 2 / sleeve',f'{main_col}60','J0.2','Unswitched sleeve / common ground; verify with plug inserted')
    record('J0 pin 3 / switched sleeve',f'{nc_col}59','J0.3','Unused; leave all other a-e holes in row 59 empty')
    rect(331+dx,yy(58)-9,90,145,'#303a43',INK,5)
    rect(348+dx,yy(58)+117,56,23,'#141c22','#53636c',4)
    for col,row,label in [(main_col,58,'1 +'),(main_col,60,'2 −'),(nc_col,59,'3 NC')]:
        x,y=hole(col,row); circle(x,y,5,'#c9b680',INK,1)
        text(x+10,y+5,label,12,'white' if col==main_col else MUTED,True)
    rect(358+dx,yy(58)+140,36,51,'#363e43',INK,4)
    line(376+dx,yy(58)+191,376+dx,yy(64)+83,INK,6)
    text(444+dx,yy(64)+42,'PJ-102AH',18,INK,True)
    text(376+dx,yy(64)+109,'12 V · centre positive',16,MUTED,anchor='middle')


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
    }
    for ref,start,end,color in flags:
        note=next(item[3] for item in wiring if item[0]==ref)
        s.append(f'<g id="jumper-{ref}" data-start="{start}" data-end="{end}"><title>{escape(note)}</title>')
        wire([parse_hole(start),*bends.get(ref,()),parse_hole(end)],color,4)
        s.append('</g>')
    for _,start,end,color in flags:
        for endpoint in (start,end): circle(*parse_hole(endpoint),6,color,'white',2)


def rail_bridges(minimum=False):
    """Connect the used rail sections; best also links the unused left halves."""
    for label,start,end,color in [
        ('B1','L+31','L+34',POWER), ('B2','L-31','L-34',INK),
        ('B3','R+31','R+34',POWER), ('B4','R-31','R-34',INK),
    ]:
        if minimum and label in ('B2','B3'):
            continue
        local(label,start,end,color,'Bridge power rail midpoint break')
    if minimum:
        local('B6','L-39','R-39',INK,'Link lower left and right ground rails')
    else:
        local('B5','L+1','R+1',POWER,'Link left and right +12 V rails',
              via=((240,yy(1)),(240,150),(700,150),(700,yy(1))))
        local('B6','L-2','R-2',INK,'Link left and right ground rails',
              via=((272,yy(2)),(272,174),(754,174),(754,yy(2))))


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
    rail_bridges()
    paired('P1','i10','a22',RED,'Nano D3 → U1 pin 2 / red; HIGH=ON')
    paired('P2','i8','a24',GREEN,'Nano D5 → U1 pin 4 / green; HIGH=ON')
    paired('P3','i7','a32',BLUE,'Nano D6 → U2 pin 2 / blue; HIGH=ON')
    for label,start,end in [('L1','a26','L-26'),('L2','a23','L-23'),('L3','j25','R-25'),('L4','a36','L-36'),('L5','a33','L-35'),('L6','j35','R-35'),('L7','c33','c34')]:
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
        ('S1','b49','L-49',INK,'Q1 source → ground rail'),
        ('S2','b54','L-54',INK,'Q2 source → ground rail'),
        ('S3','i49','R-49',INK,'Q3 source → ground rail'),
        ('V0','e58','R+58',POWER,'Jack center → +12 V rail'),
        ('V1','j55','R+55',POWER,'+12 V rail → C7 positive'),
        ('V2','a15','L+15',POWER,'+12 V rail → Nano VIN'),
        ('V3','j23','R+23',POWER,'+12 V rail → U1 pin 6'),
        ('V4','j33','R+35',POWER,'+12 V rail → U2 pin 6'),
        ('N0','e60','R-60',INK,'Jack unswitched sleeve → ground rail'),
        ('N1','a14','L-14',INK,'Nano GND → ground rail'),
        ('N2','a28','L-28',INK,'R2 pulldown → ground rail'),
        ('N4','j57','R-57',INK,'C7 negative → ground rail')]:
        paired(label,start,end,color,note)
    cap('C7','h55','h57','100 µF, 25 V',True,True)
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


def minimum_rj11_outputs():
    """Draw two top-entry jacks; their pin fan-outs are conceptual, not footprints."""
    # Contact numbering matches the PCB: 2=+12 V, 3=R, 4=G, 5=B.
    # The socket pads are deliberately off the hole grid. Short leads stand in
    # for a breakout/formed pins; only the listed RGB holes occupy the board.
    pads={}
    pad_y=yy(35)-13
    for ref,x,holes in [
        ('J1',354,{3:'b36',4:'c35',5:'d37'}),
        ('J2',536,{3:'h36',4:'i35',5:'j37'}),
    ]:
        s.append(f'<g id="connector-{ref}" data-part="615004144121" data-mounting="conceptual">')
        s.append('<title>Würth 615004144121 top-entry 6P4C female RJ11; conceptual breadboard placement and pin fan-out</title>')
        text(x+53,yy(28)-9,f'{ref} · RJ11',17,INK,True,'middle')
        text(x+53,yy(29)-10,'615004144121',12,MUTED,anchor='middle')
        rect(x,yy(29),106,122,'#deddd6','#69777f',5)
        rect(x+12,yy(29)+12,82,83,'#29353b','#63747c',3)
        rect(x+33,yy(29)+86,40,18,'#29353b','#29353b',1)
        for idx,(pin,name,color) in enumerate([(2,'+',POWER),(3,'R',RED),(4,'G',GREEN),(5,'B',BLUE)]):
            px=x+14+26*idx
            pads[f'{ref}.{pin}']=(px,pad_y)
            # Gold contacts visible inside the top-facing socket.
            line(x+33+13*idx,yy(29)+20,x+33+13*idx,yy(29)+58,'#c9ae6b',4)
            line(px,yy(29)+114,px,pad_y,'#b3a16a',3)
            component_label(px,pad_y-8,f'{pin} {name}',11,color,'middle')
            circle(px,pad_y,5,color,'white',1)
            if pin!=2:
                endpoint=holes[pin]
                record(f'{ref} pin {pin}',endpoint,f'{ref}.{pin}',
                       f'615004144121; {name} output; conceptual pin fan-out')
                hx,hy=parse_hole(endpoint)
                s.append(f'<g id="lead-{ref}-{pin}" data-start="{endpoint}" data-end="{ref}.{pin}">')
                wire([(hx,hy),(px,hy),(px,pad_y)],color,3)
                s.append('</g>')
        s.append('</g>')
    for label,start,end,points in [
        ('RJ11 positive J1','J0.1','J1.2',
         [hole('c',58),(COL['c'],yy(57)+13),(210,yy(57)+13),(210,pad_y),pads['J1.2']]),
        ('RJ11 positive J2','J1.2','J2.2',
         [pads['J1.2'],(pads['J1.2'][0],yy(38)),(pads['J2.2'][0],yy(38)),pads['J2.2']]),
    ]:
        record(label,start,end,'Insulated soldered positive pigtail; bypasses breadboard contacts')
        s.append(f'<g id="{label.lower().replace(" ","-")}" data-start="{start}" data-end="{end}">')
        s.append('<title>Soldered +12 V connection between actual jack terminals; no breadboard contact</title>')
        wire(points,POWER,4)
        s.append('</g>')


def minimum_mosfets():
    # SIPK03-1 breaks SOT-23 pins 1/3/2 out in header order G-D-S.
    # Assemble its included right-angle header so the adapter stands upright.
    # The small face illustration is schematic; the header holes are exact.
    # Keep one common part-number label with three non-electrical leaders.
    s.append('<g id="mosfet-label">')
    rect(COL['c']-50,yy(51)-14,100,28,'#f4f7fa','none',2)
    text(COL['c'],yy(51)+6,'AO3400A',17,'#000000',True,'middle')
    leaders = [
        ('Q1',[(454,yy(51)),(547,yy(44)+5)]),
        ('Q2',[(454,yy(51)),(547,yy(50)+5)]),
        ('Q3',[(454,yy(51)),(547,yy(56)+5)]),
    ]
    for ref,points in leaders:
        pts=' '.join(f'{x},{y}' for x,y in points)
        s.append(f'<polyline data-target="{ref}" points="{pts}" fill="none" stroke="#000000" stroke-width="1.5"/>')
    s.append('</g>')
    for q,col,first,color in [('Q1','g',44,RED),('Q2','g',50,GREEN),('Q3','g',56,BLUE)]:
        x=COL[col]
        s.append(f'<g id="mosfet-{q}" data-part="AO3400A" data-adapter="SIPK03-1">')
        s.append('<title>AO3400A soldered to an upright SIPK03-1 adapter. Header order G-D-S; SOT-23 pins 1=G, 2=S, 3=D. Adapter face illustrated schematically; header holes are exact.</title>')
        rect(x-11,yy(first)-13,45,80,'#23796a','#145346',3)
        rect(x+8,yy(first)+15,17,25,'#27343a',INK,2)
        for k,(pin,package_pin) in enumerate((('G',1),('D',3),('S',2))):
            endpoint=f'{col}{first+k}'
            record(f'{q} {pin}',endpoint,f'{q}.{pin}',
                   f'AO3400A SOT-23 pin {package_pin} on SIPK03-1; upright adapter header top-to-bottom G-D-S; solder MOSFET and included right-angle header before plugging in')
            line(x,yy(first+k),x+8,yy(first)+20+k*6,'#d1b86d',2)
            circle(*parse_hole(endpoint),4,'#cfb982',INK,1)
            component_label(x+43,yy(first+k)+4,pin,11,color)
        component_label(x,yy(first)-32,q,13,color,'middle')
        s.append('</g>')


def draw_minimum_jumpers():
    bends={
        # Three equally spaced Nano signal lanes, all outside the RHS rails.
        'P1': [(800,yy(10)),(800,yy(41))],
        'P2': [(812,yy(8)),(812,yy(47))],
        'P3': [(824,yy(7)),(824,yy(53))],
        'D1': [(506,yy(45)),(506,yy(36))],
        'D2': [(494,yy(51)),(494,yy(35))],
        'D3': [(482,yy(57)),(482,yy(37))],
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
       '<desc>Minimum short-strip experiment using an Arduino Nano 33 IoT, three AO3400A SOT-23 MOSFETs soldered to upright SIPK03-1 adapters stacked on the right, barrel jack J0, and two Würth 615004144121 female RJ11 output jacks J1/J2. Adapter header holes are exact; adapter faces and RJ11 mounting/pin fan-outs are conceptual illustrations. AO3400A package pins are 1=gate, 2=source, 3=drain; SIPK03-1 header order is gate-drain-source, occupying separate breadboard rows. Both jacks connect in parallel: pin 2 positive, pin 3 red, pin 4 green, pin 5 blue. Nano D3, D5 and D6 run in parallel outside the right power rails, each through a 2.2 kohm series resistor to its MOSFET gate. No gate drivers, bypass capacitors or pulldown resistors are fitted. Gates can float during Nano startup/reset; initialize the PWM outputs LOW before enabling the lights. Series resistors limit initial nominal GPIO gate-charge current to about 1.5 mA; use ordinary low-frequency PWM. Output positive connects to J0 pin 1 by soldered pigtails, bypassing breadboard contacts; row 40 is unused. J0 is shifted one column right, with its positive and ground jumpers connected to the left rails. The left positive rail and right ground rail have midpoint bridges; the lower ground rails are linked at row 39. Both right positive rail halves and the upper-left ground rail are unused. Nano VIN connects to the left + rail at row 15; Nano GND connects to the right - rail at row 12. Strip returns still pass through breadboard contacts and MOSFETs, never through Nano GPIO. The two ports share a combined 25 cm / 0.30 A LED load limit. All wires are drawn.</desc>']
    wiring=[]; occupied={}; flags.clear(); annotations.clear(); minimum_jumpers.clear()
    rect(0,0,W,H,'#f4f7fa','#f4f7fa',0)
    text(40,62,'12 V · Minimum',34,bold=True)
    text(40,108,'RGB outputs · ≤25 cm combined · ≤0.30 A total',20,MUTED)
    board(minimum=True)
    rail_bridges(minimum=True)
    output_rows(labelsize=13,rows=((35,'G',GREEN),(36,'R',RED),(37,'B',BLUE)),show_unused=False)
    barrel_jack(shift_right=True)
    minimum_rj11_outputs()
    minimum_mosfets()
    for ref,start,end,value,color in [
        ('R1','j41','j44','2.2 kΩ',RED),
        ('R2','j47','j50','2.2 kΩ',GREEN),
        ('R3','j53','j56','2.2 kΩ',BLUE),
    ]:
        component_resistor(ref,start,end,value,color)
    for label,start,end,color,note in [
        ('P1','i10','i41',RED,'Nano D3 → R1 → Q1 gate / red; HIGH=ON'),
        ('P2','i8','i47',GREEN,'Nano D5 → R2 → Q2 gate / green; HIGH=ON'),
        ('P3','i7','i53',BLUE,'Nano D6 → R3 → Q3 gate / blue; HIGH=ON'),
        ('D1','f45','e36',RED,'Q1 drain → strip R'),
        ('D2','f51','e35',GREEN,'Q2 drain → strip G'),
        ('D3','f57','e37',BLUE,'Q3 drain → strip B'),
        ('O1','d36','f36',RED,'Link both RJ11 red outputs'),
        ('O2','d35','f35',GREEN,'Link both RJ11 green outputs'),
        ('O3','c37','f37',BLUE,'Link both RJ11 blue outputs'),
        ('S1','j46','R-46',INK,'Q1 source → ground rail'),
        ('S2','j52','R-52',INK,'Q2 source → ground rail'),
        ('S3','j58','R-58',INK,'Q3 source → ground rail'),
        ('V0','a58','L+58',POWER,'J0 center → left +12 V rail'),
        ('V1','a15','L+15',POWER,'+12 V rail → Nano VIN'),
        ('N0','a60','L-60',INK,'J0 sleeve → left ground rail'),
        ('N1','j12','R-12',INK,'Nano GND → ground rail'),
    ]:
        record(label,start,end,note)
        minimum_jumpers.append((label,start,end,color,note))
    draw_minimum_jumpers()
    s.extend(annotations)
    text(40,2036,'Solder AO3400As to SIPK03-1 adapters; fit their included 0.1″ headers.',16,MUTED)
    text(40,2066,'No pull-downs: gates may float during startup/reset. Set PWM LOW first.',16,MUTED)
    text(40,2096,'Upright adapter faces and RJ11 mounting are illustrated schematically.',16,MUTED)
    text(40,2126,'Positive bypass only; RGB returns use the breadboard. 0.30 A combined.',16,MUTED)
    record('Load limit','12 V 6 A PSU','One cut segment initially; no more than 25 cm across both RJ11 ports','14.4 W/m × 0.25 m ÷ 12 V = 0.30 A combined LED current; about 0.10 A per colour. Adding a second port does not increase this limit.')
    record('J0 polarity check','PSU plug center','Positive 12 V relative to sleeve','Check before connecting; J0 feeds Nano VIN and strip + in parallel')
    record('Startup / reset','No pulldowns fitted','Gates can float until Nano drives them','Set PWM outputs LOW first in firmware; this does not guarantee off during reset or before firmware starts.')
    record('Gate drive','Nano 3.3 V PWM','2.2 kohm in series with each gate','About 1.5 mA initial nominal gate-charge current; ordinary low-frequency PWM. No separate gate-driver supply or bypass capacitors.')
    record('Mechanical fit','AO3400A SOT-23 on SIPK03-1','Solder MOSFET and included right-angle header; stand adapter upright','Header order G-D-S occupies separate rows. Package pins 1=G, 2=S, 3=D. Header holes are exact; adapter faces and RJ11 mounting are schematic. Higher-current MOSFETs do not increase the breadboard load limit.')
    check_strip_positive_bypass(rj11=True)
    s.append('</svg>')
    target=OUT/(MINIMUM_NAME+'.svg')
    target.write_text('\n'.join(s),encoding='utf-8')
    print(f'Generated {target}; {len(occupied)} unique occupied holes checked.')
    return target


def check_strip_positive_bypass(rj11=False):
    """Keep strip positive off board contacts when regenerating either layout."""
    assert not any(re.fullmatch(r'[a-j]40',endpoint) for _,start,end,_ in wiring for endpoint in (start,end))
    assert ('J0 pin 1 / center','c58' if rj11 else 'b58','J0.1') in [entry[:3] for entry in wiring]
    if rj11:
        assert [(start,end) for label,start,end,_ in wiring if label.startswith('RJ11 positive ')] == [('J0.1','J1.2'),('J1.2','J2.2')]
        for ref,holes in [('J1',{3:'b36',4:'c35',5:'d37'}),('J2',{3:'h36',4:'i35',5:'j37'})]:
            for pin,endpoint in holes.items():
                assert (f'{ref} pin {pin}',endpoint,f'{ref}.{pin}') in [entry[:3] for entry in wiring]
        return
    assert [(start,end) for label,start,end,_ in wiring if label == 'LED +'] == [('J0.1','Strip +')]
    for colour,row in [('G',41),('R',42),('B',43)]:
        assert any(label == 'LED '+colour and start == f'a{row}' and end == 'Strip '+colour for label,start,end,_ in wiring)


if __name__ == '__main__':
    build()
    build_minimum()
    import sys
    sys.path.insert(0,str(OUT.parent))
    from purchasing import export_purchase_csvs
    for path in export_purchase_csvs(OUT):
        print(f'Generated {path} for DigiKey Canada upload.')
