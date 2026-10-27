"""Shared helpers: headless-Chrome SVG rasteriser and paths."""
import os, re, subprocess, uuid, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # ic-door-vinyl/
WORK = os.environ.get('VINYL_WORK', os.path.join(ROOT, '.work'))         # cache + temp renders
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
PXMM = 20   # working resolution: 20 px per mm = 0.05 mm pixels
os.makedirs(WORK, exist_ok=True)

def render(svg_text, wpx, hpx, bg='white', mode='L'):
    d = os.path.join(WORK, 'tmp'); os.makedirs(d, exist_ok=True)
    k = uuid.uuid4().hex[:8]
    sp, hp, pp = (os.path.join(d, k + e) for e in ('.svg', '.html', '.png'))
    open(sp, 'w').write(svg_text)
    open(hp, 'w').write(f'<html><body style="margin:0;background:{bg}"><img src="{k}.svg" '
                        f'style="width:{wpx}px;height:{hpx}px;display:block"></body></html>')
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                    '--allow-file-access-from-files', f'--window-size={wpx},{hpx}',
                    f'--screenshot={pp}', 'file://' + hp], capture_output=True, timeout=300)
    a = np.array(Image.open(pp).convert(mode))
    for p in (sp, hp, pp): os.remove(p)
    assert a.shape[:2] == (hpx, wpx), (a.shape, wpx, hpx)
    return a

def path_svg(d, x, y, w, h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}" preserveAspectRatio="none">'
            f'<path fill-rule="evenodd" d="{d}"/></svg>')

def path_mask(d, w, h, pxmm=PXMM, x=0, y=0):
    return render(path_svg(d, x, y, w, h), int(round(w * pxmm)), int(round(h * pxmm))) < 128
