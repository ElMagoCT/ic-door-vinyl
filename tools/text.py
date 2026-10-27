"""Outlined text from DIN Condensed Bold (cut vinyl needs paths, not fonts)."""
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
FONT = '/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf'
_f = TTFont(FONT); GS = _f.getGlyphSet(); CM = _f.getBestCmap()
_bp = BoundsPen(GS); GS[CM[ord('H')]].draw(_bp); CAP = _bp.bounds[3]

class _PairPen(SVGPathPen):           # emit 'x,y' pairs so paths can be shifted with one regex
    def _fmt(self, pts): return ' '.join(f'{x:.3f},{y:.3f}' for x, y in pts)
    def _moveTo(self, p): self._commands.append('M' + self._fmt([p]))
    def _lineTo(self, p): self._commands.append('L' + self._fmt([p]))
    def _qCurveToOne(self, a, b): self._commands.append('Q' + self._fmt([a, b]))
    def _curveToOne(self, a, b, c): self._commands.append('C' + self._fmt([a, b, c]))
    def _closePath(self): self._commands.append('Z')

import json, os, re
from lib import WORK
_G = None
_NUM = re.compile(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)')
def text_path(s, x, y, cap_mm, track=0.0, anchor='middle'):
    """cut-safe text from the processed glyphs (glyphs.py); (x, y) = baseline anchor; returns (d, width)"""
    global _G
    if _G is None: _G = json.load(open(os.path.join(WORK, 'glyphs.json')))
    assert cap_mm >= _G['C0'] - 1e-9, f'text below the {_G["C0"]} mm minimum cap height'
    g = _G['glyphs']; s = ''.join(c for c in s if c in g)
    W = sum(g[c]['adv'] * cap_mm for c in s) + track * (len(s) - 1)
    cx = {'middle': x - W / 2, 'start': x, 'end': x - W}[anchor]; out = ''
    for c in s:
        out += _NUM.sub(lambda m: f'{float(m.group(1)) * cap_mm + cx:.3f},{float(m.group(2)) * cap_mm + y:.3f}', g[c]['d'])
        cx += g[c]['adv'] * cap_mm + track
    return out, W

def raw_text_path(s, x, y, cap_mm, track=0.0, anchor='middle'):
    """straight from the font (used only to build the processed glyphs)"""
    sc = cap_mm / CAP
    adv = [GS[CM[ord(c)]].width * sc for c in s]
    W = sum(adv) + track * (len(s) - 1)
    cx = {'middle': x - W / 2, 'start': x, 'end': x - W}[anchor]
    pen = _PairPen(GS)
    for c, a in zip(s, adv):
        GS[CM[ord(c)]].draw(TransformPen(pen, (sc, 0, 0, -sc, cx, y))); cx += a + track
    return ''.join(pen._commands), W

def glyph_table(chars):
    """per-glyph outlines normalised to cap height 1 (y down, baseline 0) for the browser editor"""
    out = {}
    for c in chars:
        pen = _PairPen(GS); s = 1 / CAP
        GS[CM[ord(c)]].draw(TransformPen(pen, (s, 0, 0, -s, 0, 0)))
        out[c] = {'d': ''.join(pen._commands), 'adv': GS[CM[ord(c)]].width / CAP}
    return out
