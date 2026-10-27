"""The cut rules (mm), applied to vinyl strokes AND to the clear gaps between them:
  R1  nothing thinner than MIN = 0.5
  R2  anything thinner than THICK = 1.0 must run shorter than RUN = 10
Width is measured morphologically: a pixel is 'thinner than d' when no disk of
diameter d that fits inside the shape covers it (the residue of an opening).
A sharp corner always tapers to zero, so residues no longer than CORNER_TIP
count as corners; anything longer is a sliver and fails."""
import numpy as np, cv2
from skimage.morphology import skeletonize
from scipy import ndimage as ndi
from lib import PXMM
MIN, THICK, RUN, CORNER_TIP = 0.5, 1.0, 10.0, 0.6
DESIGN_TOL = 1.1   # what we generate must clear 0.55 / 1.1 mm; the final verify checks the true 0.5 / 1.0
_dt = lambda M: cv2.distanceTransform(M.astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)

def opening(V, d_px):
    r = d_px / 2
    return _dt(~(_dt(V) > r)) <= r
def dilate(V, r_px): return _dt(~V) <= r_px
def thin_parts(V, d_mm, pxmm=PXMM): return V & ~opening(V, d_mm * pxmm)
def _runs(T, pxmm):
    lab, n = ndi.label(T, structure=np.ones((3, 3)))
    if not n: return lab, np.zeros(0)
    return lab, ndi.sum(skeletonize(T), lab, np.arange(1, n + 1)) * 1.12 / pxmm

def check(V, pxmm=PXMM, tol=1.0):
    """violations as lists of (x_mm, y_mm[, run_mm]). Tests at exactly 0.5 / 1.0 mm (tol=1): no slack,
    so a feature that measures 0.49 mm at 0.05 mm pixels fails."""
    pad = int(3 * pxmm); V = np.pad(V, pad); out = {}
    for name, M in (('vinyl', V), ('gap', ~V)):
        lab, n = ndi.label(thin_parts(M, MIN * tol, pxmm), structure=np.ones((3, 3)))
        out[name + '_under_0.5'] = [(round(s[1].start / pxmm - 3, 1), round(s[0].start / pxmm - 3, 1))
                                    for s in ndi.find_objects(lab)
                                    if max(s[0].stop - s[0].start, s[1].stop - s[1].start) > CORNER_TIP * pxmm]
        lab, L = _runs(thin_parts(M, THICK * tol, pxmm), pxmm)
        sl = ndi.find_objects(lab)
        out[name + '_under_1_longrun'] = [(round(sl[i][1].start / pxmm - 3, 1), round(sl[i][0].start / pxmm - 3, 1),
                                           round(L[i], 1)) for i in range(len(L)) if L[i] >= RUN]
    return out

def enforce(V, pxmm=PXMM, iters=3, log=None, minw=0.6, thick=1.1):
    """push V to satisfy the rules with margin: thicken long thin strokes, widen long thin gaps,
    then fill gaps < minw and drop strokes < minw"""
    pad = int(3 * pxmm); V = np.pad(V, pad); V0 = V.copy()
    for _ in range(iters):
        for pos in (True, False):
            lab, L = _runs(thin_parts(V if pos else ~V, thick, pxmm), pxmm)
            ids = np.nonzero(L >= RUN * 0.85)[0] + 1
            if not len(ids): continue
            grow = dilate(np.isin(lab, ids), (thick - MIN) / 2 * pxmm + 1)
            V = (V | grow) if pos else (V & ~grow)
        V = ~opening(~V, minw * pxmm)
        V = opening(V, minw * pxmm)
    if log is not None: log.append(f'enforce changed {(V != V0).sum() / pxmm**2:.1f} mm^2')
    return V[pad:-pad, pad:-pad]
