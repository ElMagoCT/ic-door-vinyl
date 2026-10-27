"""previews.py [files]: white-vinyl-on-glass PNG previews into ../previews/"""
import sys, os, re, glob
from PIL import Image
from lib import ROOT, render
GLASS = 'linear-gradient(160deg,#3d4d58 0%,#1f2a31 55%,#2a3740 100%)'
os.makedirs(f'{ROOT}/previews', exist_ok=True)
for fn in sys.argv[1:] or sorted(glob.glob(f'{ROOT}/logos/*.svg') + glob.glob(f'{ROOT}/concepts/*.svg')):
    svg = open(fn).read().replace('fill="#000"', 'fill="#f2f5f6"')
    W, H = (float(x) for x in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
    sc = min(1500 / H, 1500 / W)
    a = render(svg, int(W * sc), int(H * sc), bg=GLASS, mode='RGB')
    out = f'{ROOT}/previews/' + os.path.basename(fn).replace('.svg', '.png')
    Image.fromarray(a).save(out); print(out, flush=True)
