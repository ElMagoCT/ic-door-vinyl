import os, re
from lib import ROOT
from pieces import piece
from text import text_path
NUM = re.compile(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)')
def shift(d, dx, dy): return NUM.sub(lambda m: f'{float(m.group(1)) + dx:.3f},{float(m.group(2)) + dy:.3f}', d)

class Doc:
    def __init__(s, name, w, h, title, desc=''):
        s.name, s.w, s.h, s.title, s.desc, s.items = name, w, h, title, desc, []
    def add(s, id, d): s.items.append((id, d)); return s
    def logo(s, v, w_mm, x, y, id=None):
        p = piece(v, w_mm); s.add(id or v, shift(p['d'], x, y)); return p
    def text(s, id, txt, x, y, cap, track=0, anchor='middle'):
        d, w = text_path(txt, x, y, cap, track, anchor); s.add(id, d); return w
    def svg(s, fill='#000'):
        paths = '\n'.join(f'  <path id="{i}" fill-rule="evenodd" d="{d}"/>' for i, d in s.items)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{s.w:.2f}mm" height="{s.h:.2f}mm" '
                f'viewBox="0 0 {s.w:.2f} {s.h:.2f}">\n<title>{s.title}</title>\n<desc>{s.desc}</desc>\n'
                f'<g id="vinyl" fill="{fill}">\n{paths}\n</g>\n</svg>\n')
    def save(s, sub='concepts'):
        os.makedirs(f'{ROOT}/{sub}', exist_ok=True)
        fn = f'{ROOT}/{sub}/{s.name}.svg'; open(fn, 'w').write(s.svg()); return fn

def rect_d(x, y, w, h, r=0):
    if r <= 0: return f'M{x:.3f},{y:.3f} L{x+w:.3f},{y:.3f} L{x+w:.3f},{y+h:.3f} L{x:.3f},{y+h:.3f}Z'
    k = 0.5523 * r
    return (f'M{x+r:.3f},{y:.3f} L{x+w-r:.3f},{y:.3f} C{x+w-r+k:.3f},{y:.3f} {x+w:.3f},{y+r-k:.3f} {x+w:.3f},{y+r:.3f} '
            f'L{x+w:.3f},{y+h-r:.3f} C{x+w:.3f},{y+h-r+k:.3f} {x+w-r+k:.3f},{y+h:.3f} {x+w-r:.3f},{y+h:.3f} '
            f'L{x+r:.3f},{y+h:.3f} C{x+r-k:.3f},{y+h:.3f} {x:.3f},{y+h-r+k:.3f} {x:.3f},{y+h-r:.3f} '
            f'L{x:.3f},{y+r:.3f} C{x:.3f},{y+r-k:.3f} {x+r-k:.3f},{y:.3f} {x+r:.3f},{y:.3f}Z')
def circ(cx, cy, r):   # 4 cubics (no arc commands, so shift() stays valid)
    k = 0.5523 * r
    return (f'M{cx+r:.3f},{cy:.3f} C{cx+r:.3f},{cy+k:.3f} {cx+k:.3f},{cy+r:.3f} {cx:.3f},{cy+r:.3f} '
            f'C{cx-k:.3f},{cy+r:.3f} {cx-r:.3f},{cy+k:.3f} {cx-r:.3f},{cy:.3f} '
            f'C{cx-r:.3f},{cy-k:.3f} {cx-k:.3f},{cy-r:.3f} {cx:.3f},{cy-r:.3f} '
            f'C{cx+k:.3f},{cy-r:.3f} {cx+r:.3f},{cy-k:.3f} {cx+r:.3f},{cy:.3f}Z')
def ring(cx, cy, r1, r2): return circ(cx, cy, r2) + circ(cx, cy, r1)
def poly_d(g):
    out = ''
    for pg in getattr(g, 'geoms', [g]):
        for rg in [pg.exterior, *pg.interiors]:
            c = list(rg.coords); out += 'M' + ' L'.join(f'{x:.3f},{y:.3f}' for x, y in c[:-1]) + 'Z'
    return out
LABEL = {'bb': 'ROBOTICS', 'cs': 'CUBESAT', 'rc': 'RC CLUB', 'rk': 'ROCKETRY'}
W11 = 279.4   # 11 in: every strip fits a 12 in roll with 1/2 in to spare
