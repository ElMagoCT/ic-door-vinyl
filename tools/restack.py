#!/usr/bin/env python3
"""Reorder the club groups in a 'Stacked (custom)' SVG exported by review.html, keeping every group's
geometry and the gaps between slots, so the artboard size and the <desc> glass offsets stay valid.

  python3 tools/restack.py IN.svg OUT.svg bb rc rk cs      # top-to-bottom order by logo key

A group is a logo path (bb*/cs*/rc*/rk*) plus the label path right after it. room-label-* stays put."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut import parse, bbox

PAIR = re.compile(r'(-?\d+\.?\d*),(-?\d+\.?\d*)')

def shift_d(d, dy):
    return PAIR.sub(lambda m: f'{m.group(1)},{float(m.group(2)) + dy:.3f}', d)

def main(src, dst, order):
    s = open(src, encoding='utf-8').read()
    paths = [(m.group(0), re.search(r'id="([^"]+)"', m.group(0)).group(1), re.search(r' d="([^"]+)"', m.group(0)).group(1))
             for m in re.finditer(r'<path\b[^>]*/>', s)]
    groups = []
    for idx, (_, pid, d) in enumerate(paths):
        key = pid.split('-')[0]
        if key[:2] in ('bb', 'cs', 'rc', 'rk') and key != 'room': groups.append([key[:2], [idx]])
        elif key == 'label' and groups: groups[-1][1].append(idx)
    for g in groups:
        bbs = [bbox(parse(paths[i][2])) for i in g[1]]
        g.append((min(b[1] for b in bbs), max(b[3] for b in bbs)))
    groups.sort(key=lambda g: g[2][0])
    tops = [g[2][0] for g in groups]; bottoms = [g[2][1] for g in groups]
    gaps = [tops[i + 1] - bottoms[i] for i in range(len(groups) - 1)]
    bykey = {g[0]: g for g in groups}
    if sorted(order) != sorted(bykey): raise SystemExit(f'order must list exactly {sorted(bykey)}')
    print('current order:', ' '.join(f'{g[0]}({g[2][0]:.1f}..{g[2][1]:.1f})' for g in groups), '| gaps', [f'{x:.2f}' for x in gaps])
    y = tops[0]; out = s
    for i, key in enumerate(order):
        g = bykey[key]; dy = y - g[2][0]
        print(f'{key}: {g[2][0]:.2f} -> {y:.2f}  (shift {dy:+.2f} mm)')
        for idx in g[1]:
            text, pid, d = paths[idx]
            out = out.replace(text, text.replace(f' d="{d}"', f' d="{shift_d(d, dy)}"'), 1)
        y += (g[2][1] - g[2][0]) + (gaps[i] if i < len(gaps) else 0)
    print(f'bottom of the last group: {y:.2f} (was {bottoms[-1]:.2f})')
    out = re.sub(r'<title>[^<]*</title>', f'<title>Stacked (custom, order {" ".join(order)})</title>', out, 1)
    open(dst, 'w', encoding='utf-8').write(out)
    print('wrote', dst)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
