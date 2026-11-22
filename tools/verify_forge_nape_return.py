#!/usr/bin/env python3
"""Compare the two directions and final part of the draw in paired Forge captures."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from verify_forge_combined import SLOTS, timeline
from verify_forge_gaits import table, text
from verify_forge_nape import BAND, CHAIN, FRONT, Capture, cut, paired
from verify_forge_postures import read_boxes
from verify_forge_walk import read

TRACKS = (('maniobra', 1), ('giro-inverso', -1))
WINDOW = range(77, 84)
GROUPS = (CHAIN,BAND,FRONT)


def frames(root, out, track, slot, direction, *, neutral=False):
    stem = f'{track}-{slot}'
    trace = read(root/f'{stem}.tsv')
    timeline(trace, slot)
    mesh = read_boxes(root/f'{stem}-cubos.tsv')
    roof = {}
    for line in (root/f'{stem}-cabeza.tsv').read_text().splitlines():
        t, face, *uv = line.split('\t')
        assert face == 'top' and len(uv) == 8, line
        roof[int(t)] = uv
    shots = trace[trace['image'] != '-']
    assert {int(r['time']) for r in shots} == set(roof), stem
    photos = {}
    for p in shots:
        tick = int(p['time'])
        rest = neutral and tick in range(87,90)
        if tick not in range(63,66) and tick not in WINDOW and not rest:
            continue
        assert p['fit'] == p['ground'] == p['crouching'] == 1, (stem,p)
        assert abs(p['yaw']) < 2 if rest else direction*p['yaw'] > 0, (stem,p)
        assert p['image'] == f'{stem}-{tick:03d}.png'
        with Image.open(root/str(p['image'])) as im:
            w,h = im.size
            x,y = w//2 - round(.26*h), round(.105*h)
            dst = out/f'{stem}-{tick:03d}.png'
            im.crop((x,y,w//2+round(.26*h),round(.56*h))).save(dst)
        cap = Capture(out, dict(zip('tick imagen ancho alto x0 y0 ax ay bx by cx cy dx dy'.split(),
                                     (tick,dst.name,w,h,x,y,*roof[tick]),strict=True)))
        photos[tick] = p, cap, mesh[tick]
    return photos


def measure(a,b,side):
    old,hair = a.sample(side)
    now,clear = b.sample(side)
    return tuple(int(x) for x in (old.sum(),now.sum(),(old & clear).sum(),(hair & now).sum()))


def gallery(out, slot, report):
    # Same row: same part of the route. The negative and positive turns use
    # opposite live cameras, never a flipped positive-turn screenshot.
    w,h=230,196
    im = Image.new('RGB',(24+4*(w+7),94+sum(h+34 for _ in report[0])), '#17121d')
    pen = ImageDraw.Draw(im)
    text(pen,(12,10),f'Alex · retorno de la mirada · {slot}',25,bold=True)
    text(pen,(12,48),'Forge · giros medidos a ambos lados',16,'#edc4db')
    for i, pairs in enumerate(report):
        for j,(k,a,b) in enumerate(pairs):
            x,y=12+i*2*(w+7), 95+j*(h+34)
            text(pen,(x,y-22), f'{"+" if i==0 else "−"}55° · t{k} · .30 / .31',16,bold=True)
            for n, cap in enumerate((a,b)):
                with Image.open(cap.path) as p:
                    pic=p.resize((w,h),Image.Resampling.LANCZOS)
                    im.paste(pic,(x+n*(w+7),y))
    im.save(out,quality=94,optimize=True)


def compare(old, new, out, scratch):
    out.mkdir(parents=True,exist_ok=True)
    dirs = [scratch/v for v in ('v30','v31')]
    for d in dirs: d.mkdir(parents=True,exist_ok=True)
    rows = []
    for slot in SLOTS:
        overlay = []
        for track, direction in TRACKS:
            a,b = [frames(r,d,track,slot,direction) for r,d in zip((old,new),dirs,strict=True)]
            ticks = sorted(a.keys() & b.keys())
            assert len(set(ticks)&set(WINDOW)) >= 5 and min(ticks) <= 65 and max(ticks) >= 82, (track,slot,'faltan pares de Forge',ticks)
            chosen = []
            for tick in ticks:
                p,c0,m0=a[tick]
                q,c1,m1=b[tick]
                paired(p,q)
                s0,s1=(1 if c.eye[0]>1 else -1 if c.eye[0]<0 else 0 for c in (c0,c1))
                if tick in WINDOW:
                    assert s0 == s1 == direction, (track,slot,tick,c0.eye,c1.eye)
                side = measure(c0,c1,s0) if s0 == s1 and s0 else ('-',)*4
                rows.append((slot,direction,tick,round(p['time'],6),round(q['time'],6),round(p['yaw'],5),round(q['yaw'],5),
                             *measure(c0,c1,0),*side,round(cut(m0,GROUPS),6),round(cut(m1,GROUPS),6)))
                chosen.append((tick,c0,c1))
            overlay.append(chosen)
        # Keep this sheet compact; both full traces remain in the TSV.
        common = {t for t,*_ in overlay[0]} & {t for t,*_ in overlay[1]}
        late = [t for t in sorted(common) if t in WINDOW]
        picks = {min(common),late[0],late[-1]}
        if len(late) > 2: picks.add(late[len(late)//2])
        gallery(out/f'retorno-{slot}.jpg',slot,[[x for x in seq if x[0] in picks] for seq in overlay])
    table(out/'retorno.tsv','ranura sentido tick tiempo_30 tiempo_31 yaw_30 yaw_31 granate_nuca_30 granate_nuca_31 '
          'pelo_recuperado_nuca granate_nuevo_nuca granate_lado_30 granate_lado_31 pelo_recuperado_lado granate_nuevo_lado '
          'seccion_30_u2 seccion_31_u2',rows)
    for row in rows:
        print(*row,sep='\t',flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('old','new','out','scratch'): p.add_argument(key,type=Path)
    a=p.parse_args()
    compare(a.old,a.new,a.out,a.scratch)
