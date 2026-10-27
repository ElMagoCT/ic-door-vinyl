import potrace
from lib import PXMM
def trace(V, pxmm=PXMM, ox=0.0, oy=0.0):
    """bool mask -> SVG path data in mm (absolute M/L/C, 'x,y' pairs)"""
    pl = potrace.Bitmap(~V).trace(turdsize=2, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                                  alphamax=1.0, opticurve=True, opttolerance=0.2)   # potracer: False = ink
    f = lambda p: f'{p.x / pxmm + ox:.3f},{p.y / pxmm + oy:.3f}'
    out = []
    for c in pl:
        s = ['M' + f(c.start_point)]
        for seg in c.segments:
            s.append('L' + f(seg.c) + ' L' + f(seg.end_point) if seg.is_corner
                     else 'C' + f(seg.c1) + ' ' + f(seg.c2) + ' ' + f(seg.end_point))
        out.append(''.join(s) + 'Z')
    return ''.join(out)
