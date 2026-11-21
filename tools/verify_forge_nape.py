#!/usr/bin/env python3
"""Register real Forge color/mesh at the nape, independently of the top-face test.

The exported four roof corners determine the perspective camera in head space.
Sample the same interior of Alex's rear face in separate draws; do not compare
unregistered image pixels or treat the sum of box sections as visible area.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from cape_fit import nape_piece, nape_shifts, profile
from extract_forge_nape import extract
from verify_forge_combined import SLOTS
from verify_forge_crown import EDGES, head_roof, sewn, shorten
from verify_forge_gaits import table, text
from verify_forge_postures import read_boxes
from verify_forge_walk import read
from verify_v1660 import contacts

CHAIN = 'v18_chain_'
BAND = 'v17_cowl_back_'
FRONT = 'v17_cowl_front_'
STILLS = (63, 77)
# Exclude the outer-layer/silhouette edge and the intentional overlap at the
# roots below the arch. These are fractions of the solid 8 u vanilla face.
X0, X1, Y0, Y1 = .10, .90, .12, .57


def camera(top, size):
    """Recover a centered pinhole camera from a square with known corner order."""
    corners = np.array(((0., 0.), (1., 0.), (1., 1.), (0., 1.)))
    coords = (np.asarray(top)-.5) * (size[0]/size[1], 1.)
    rows, rhs = [], []
    for (x, z), (u, v) in zip(corners, coords, strict=True):
        rows.extend(((x,z,1,0,0,0,-u*x,-u*z), (0,0,0,x,z,1,-v*x,-v*z)))
        rhs.extend((u, v))
    h = np.r_[np.linalg.solve(rows, rhs), 1.].reshape((3, 3))
    a, b = h[:, :2].T
    # Rotation columns must have equal norm and be orthogonal. The image
    # axes have a common focal length in pixels (units of viewport height).
    z = np.array((a[2]*b[2], a[2]**2-b[2]**2))
    f = np.sqrt(-z @ [a[:2] @ b[:2], a[:2] @ a[:2]-b[:2] @ b[:2]] / (z @ z))
    assert .25 < f < 1.8, (top, f)
    x, z, offset = (h / np.array([[f], [f], [1.]])).T
    scale = (np.linalg.norm(x)+np.linalg.norm(z))/2
    x, z, offset = x/scale, z/scale, offset/scale
    u, _, v = np.linalg.svd(np.column_stack((x,np.cross(z,x),z)))
    rot = u @ v
    np.testing.assert_allclose(project(np.c_[corners[:,0],np.zeros(4),corners[:,1]], (f,rot,offset), size),
                               np.asarray(top)*size, rtol=0, atol=.10)
    assert np.linalg.det(rot) > 0, rot
    return f, rot, offset


def project(points, intrinsics, size):
    f, rot, offset = intrinsics
    p = points @ rot.T + offset
    assert (p[:,2] > 0).all()
    return p[:,:2] * (f*size[1]) / p[:,2:] + np.asarray(size)*.5


def face_grid(x0, x1, y0, y1, side=False):
    x, y = np.meshgrid(np.linspace(x0,x1,96), np.linspace(y0,y1,54))
    end = np.ones(x.size)
    return np.column_stack((end,y.ravel(),x.ravel()) if side else (x.ravel(),y.ravel(),end))


class Capture:
    def __init__(self, root, row):
        self.tick = int(row['tick'])
        self.path = root/row['imagen']
        self.size = tuple(int(row[k]) for k in ('ancho','alto'))
        self.origin = [int(row[k]) for k in ('x0','y0')]
        self.camera = camera(np.array([float(row[k]) for k in ('ax','ay','bx','by','cx','cy','dx','dy')]).reshape(4,2), self.size)
        self.eye = -self.camera[1].T @ self.camera[2]
        with Image.open(self.path) as im:
            self.rgb = np.array(im.convert('RGB'), dtype=np.int16)

    def sample(self, side=False):
        axis = 0 if side else 2
        assert self.eye[axis] > 1, (self.path, 'cara no visible', self.eye)
        p = face_grid(X0,X1,Y0,Y1,side)
        ij = np.floor(project(p,self.camera,self.size)-self.origin).astype(int)
        w,h = self.rgb.shape[1],self.rgb.shape[0]
        assert (ij >= 0).all() and (ij < [w,h]).all(), self.path
        r,g,b = self.rgb[ij[:,1],ij[:,0]].T
        cloth = (r-g >= 13) & (b-g >= 6) & (g < 125)
        hair = (r-g >= 17) & (g-b >= 12) & (r >= 55)
        return cloth, hair


def load(root):
    photos = {}
    with (root/'capturas.tsv').open() as file:
        for r in csv.DictReader(file,delimiter='\t'):
            cap = Capture(root,r)
            t, = [t for t in STILLS if t <= cap.tick <= t+2]
            key = (r['ranura'],t)
            assert key not in photos, (root,key)
            photos[key] = cap
    assert set(photos) == {(s,t) for s in SLOTS for t in STILLS}, root
    return photos


def trace_at(path, tick):
    data = read(path)
    pose = data[(data['fit'] == 1) & (data['time'].astype(int) == tick)]
    assert len(pose) == 1 and pose[0]['crouching'] == 1, (path,tick)
    return pose[0]


def paired(a, b):
    assert abs(a['yaw']-b['yaw']) <= 4.5 and abs(a['pitch']-b['pitch']) <= 3., (a,b)


def local_head(groups):
    h, = groups['head']
    basis = h[[1,3,4]]-h[0]
    np.testing.assert_allclose(np.linalg.norm(basis,axis=1),[8]*3,atol=.004,rtol=0)
    return {n:(np.asarray(g)-h[0]) @ np.linalg.inv(basis) for n,g in groups.items()}


def rear_cut(box):
    # Intersect each edge with the actual rear head plane Z=1 and clip the
    # section to the measured strip. Still a geometric sum, not screen area.
    d = box[:,2]-1
    p = np.asarray([(d[i]*box[j,:2]-d[j]*box[i,:2])/(d[i]-d[j])
                    for i,j in EDGES if (d[i] < 0) != (d[j] < 0)])
    if len(p) < 3:
        return 0.
    u,v = (p-p.mean(0)).T
    p = p[np.argsort(np.arctan2(v,u))]
    for axis,(lo,hi) in enumerate(((X0,X1),(Y0,Y1))):
        p = shorten(shorten(p,axis,lo,1),axis,hi,-1)
    u,v = p.T
    return 32*abs(u @ np.roll(v,-1)-v @ np.roll(u,-1))


def cut(groups, prefix):
    return sum(rear_cut(b) for n,g in local_head(groups).items() if n.startswith(prefix) for b in g)


def chain_seam(groups):
    chain = np.concatenate([groups[f'{CHAIN}{i}'] for i in range(8)])
    assert len(chain) == 8
    anchors = np.concatenate([g for n,g in groups.items() if n.startswith(('v17_cowl_','v19_cuellito_','v20_mount_saddle'))
                              or n.startswith('v17_ribbon_') and n.endswith('_seg0')])
    depth = -contacts(chain[None], anchors[None])[0]
    halves = chain[:,:,0].mean(1) > 0
    return min(depth[:,halves].max(), depth[:,~halves].max())


def load_mesh(root):
    return {s:read_boxes(root/f'{s}-cubos.tsv') for s in SLOTS}


def ablation(baseline, out):
    paths = [baseline/'control'/n for n in ('maniobra','sin-cadena','sin-borde')]
    sets = [load(d) for d in paths]
    meshes = [load_mesh(d) for d in paths]
    before = load(baseline)
    rows, gallery = [], []
    for s in SLOTS:
        for t in STILLS:
            orig = before[s,t]
            full, chain, band = (d[s,t] for d in sets)
            poses = [trace_at(d/f'{s}.tsv',v.tick) for d,v in zip(paths,(full,chain,band),strict=True)]
            for p in poses[1:]:
                paired(poses[0],p)
            groups, no_chain, no_band = (m[s][v.tick] for m,v in zip(meshes,(full,chain,band),strict=True))
            for prefix, omitted in ((CHAIN,no_chain),(BAND,no_band)):
                assert set(omitted) == {n for n in groups if not n.startswith(prefix)}, (s,t,prefix,set(groups)^set(omitted))
            old = orig.sample()[0]
            painted, _ = full.sample()
            a, hair_a = chain.sample()
            b, hair_b = band.sample()
            restored_chain = (painted & hair_a).sum()
            restored_band = (painted & hair_b).sum()
            assert painted.sum() > 150 and .75 <= painted.sum()/old.sum() <= 1.25, (s,t,'no se reprodujo la mancha .30')
            if t == 77:
                assert restored_chain > .17*painted.sum() and restored_chain > restored_band, (s,t,restored_chain,restored_band)
            rows.append((s,t,full.tick,chain.tick,band.tick,len(painted),old.sum(),painted.sum(),a.sum(),b.sum(),restored_chain,restored_band,
                         f'{cut(groups,CHAIN):.6f}',f'{cut(groups,BAND):.6f}',f'{cut(groups,FRONT):.6f}'))
            gallery.append((s,t,(orig,full,chain,band)))
    table(out/'ablacion.tsv','ranura momento tick_completo tick_sin_cadena tick_sin_borde muestras granate_original granate_completo '
          'granate_sin_cadena granate_sin_borde pelo_recuperado_sin_cadena pelo_recuperado_sin_borde '
          'corte_cadena_u2 corte_borde_u2 corte_frente_u2',rows)
    board(out/'ablacion.jpg',gallery,('Original .30','Repetición .30','Sin cadena · control','Sin borde trasero · control'),
          'Nuca de Alex · aislamiento en Forge')
    for row in rows:
        print(*row, sep='\t',flush=True)


def undo_trim(groups, pose):
    shifts = nape_shifts(-pose['pitch'],pose['yaw'],profile()['bodyAngle']) if pose['crouching'] else [(0.,)*3]*2
    return {n:np.asarray(c)-shifts[k] if (k := nape_piece(n)) is not None else c for n,c in groups.items()}


def verify_mesh(root, baseline):
    old = load_mesh(baseline)
    measures, info = {}, []
    for slot, mesh in load_mesh_full(root).items():
        trace = read(root/f'maniobra-{slot}.tsv')
        pose = {int(r['time']):r for r in trace[trace['fit'] == 1]}
        assert sorted(mesh) == sorted(pose), slot
        baseline_chain = old[slot][63]
        active = [t for t in mesh if 58 <= t <= 79]
        assert len(active) >= 18 and sum(74 <= t <= 79 for t in active) >= 4, (slot,active)
        for t, groups in mesh.items():
            ref = undo_trim(groups,pose[t])
            # Undo only the declared stroke; the remaining chain geometry
            # must be the .30 rigid shape and placement at every sample.
            for n in baseline_chain:
                if n.startswith(CHAIN):
                    np.testing.assert_allclose(ref[n],baseline_chain[n],atol=.005,rtol=0,err_msg=f'{slot}/{t}/{n}')
            support = chain_seam(groups)
            assert support > .15 and sewn(groups) > .14, (slot,t,'borde despegado',support)
            if not 58 <= t <= 83:
                continue
            a = head_roof(ref)[0]
            b = head_roof(groups)[0]
            assert b <= a+.015, (slot,t,'levantó la corona',a,b)
            original = cut(ref,(CHAIN,BAND,FRONT))
            current = cut(groups,(CHAIN,BAND,FRONT))
            if t in active:
                assert original > .5 and current < .60*original, (slot,t,'sección de nuca',original,current)
            elif t >= 81:
                assert current <= original+.32, (slot,t,'la franja vuelve al deshacer el giro',original,current)
            measures[slot,t] = (original,current,support)
            info.append((slot,t,*(f'{x:.6f}' for x in (original,current,a,b,support))))
    table(root/'maniobra-nuca-malla.tsv','ranura tick corte_sin_ajuste_u2 corte_u2 altura_corona_sin_ajuste_u '
          'altura_corona_u contacto_tira_u',info)
    return measures


def load_mesh_full(root):
    return {s:read_boxes(root/f'maniobra-{s}-cubos.tsv') for s in SLOTS}


def candidate(root, baseline, out):
    extract(root,out/'detalle',stills_only=True)
    measures = verify_mesh(root,baseline)
    old, new = load(baseline), load(out/'detalle')
    rows, gallery = [], []
    for slot in SLOTS:
        for t in STILLS:
            a,b = old[slot,t],new[slot,t]
            paired(trace_at(baseline.parent/f'maniobra-{slot}.tsv',a.tick), trace_at(root/f'maniobra-{slot}.tsv',b.tick))
            cloth0,hair0 = a.sample()
            cloth1,hair1 = b.sample()
            recovered = (cloth0 & hair1).sum()
            new_cloth = (hair0 & cloth1).sum()
            orig,cur,seam = measures[slot,b.tick]
            s0 = s1 = 0
            if t == 77:
                side0, skin0 = a.sample(side=True)
                side1, _ = b.sample(side=True)
                s0,s1 = side0.sum(),side1.sum()
                assert s1 <= s0+55 and (skin0 & side1).sum() <= .04*len(side0), (slot,t,'el cruce pasó al lateral',s0,s1)
            print(f'{slot}: t={b.tick} granate nuca {cloth0.sum()} → {cloth1.sum()} / {len(cloth0)}; '
                  f'pelo recuperado {recovered}, granate nuevo {new_cloth}; corte {orig:.3f} → {cur:.3f}u², '
                  f'unión tira {seam:.3f}u, lateral {s0} → {s1}.',flush=True)
            assert cloth0.sum() > 600 and cloth1.sum() <= cloth0.sum()*(.76 if t == 63 else .35), (slot,t,'queda la franja')
            assert recovered >= cloth0.sum()*(.27 if t == 63 else .60) and new_cloth < .035*len(cloth0), (slot,t,'no recuperó pelo')
            rows.append((slot,t,a.tick,b.tick,len(cloth0),cloth0.sum(),cloth1.sum(),recovered,new_cloth,s0,s1,
                         *(f'{x:.6f}' for x in (orig,cur,seam))))
            gallery.append((slot,t,(a,b)))
    table(root/'maniobra-nuca.tsv','ranura momento tick_base tick muestras granate_base granate pelo_recuperado granate_nuevo '
          'granate_lateral_base granate_lateral corte_sin_ajuste_u2 corte_u2 contacto_tira_u',rows)
    board(root/'maniobra-nuca.jpg',gallery,('v1.67.30','v1.67.31 · ajuste de nuca'), 'Nuca de Alex · mismo giro en Forge')


def board(out, gallery, columns, title):
    w,h = 250,185
    sheet = Image.new('RGB',(20+len(columns)*(w+8),95+len(gallery)*(h+29)), '#17121d')
    pen = ImageDraw.Draw(sheet)
    text(pen,(10,10),title,26,bold=True)
    for j,key in enumerate(columns):
        text(pen,(10+j*(w+8),48),key,15,'#edc4db')
    for i,(slot,tick,photos) in enumerate(gallery):
        y = 88+i*(h+29)
        text(pen,(10,y-19),f'{slot.upper()} · {"PASO" if tick == 63 else "FRENO"}',14,bold=True)
        for j,k in enumerate(photos):
            with Image.open(k.path) as im:
                display = im.resize((w,round(w/im.width*im.height)),Image.Resampling.LANCZOS)
                a = max(0,(display.height-h)//2)
                sheet.paste(display.crop((0,a,w,a+h)),(10+j*(w+8),y))
    sheet.save(out,quality=95,optimize=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--shots', type=Path, help='Forge capture to compare; without it, report the .30 ablations')
    args = parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    if args.shots:
        candidate(args.shots,args.baseline,args.out)
    else:
        ablation(args.baseline,args.out)
