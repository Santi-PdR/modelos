"""Geometry and body-space clearance for the contact under the collar."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json
import math
import re

import numpy as np

JAVA = Path(__file__).resolve().parents[1]/'src/main/java/com/capatest/client/CapeBacking.java'


@lru_cache(maxsize=1)
def profile():
    s = JAVA.read_text()
    names = [re.search(r'\b'+key+r' = "([^"]+)";',s)[1] for key in ('LEFT','RIGHT')]
    def val(key):
        return float(re.search(r'\b'+key+r' = ([\d.]+)',s)[1])
    data = re.search(r'\bPANELS\s*=\s*(\{.*?\});',s,re.S)[1]
    panels = json.loads(data.replace('{','[').replace('}',']').replace(' .',' 0.'))
    y,z = val('Y_PIVOT'),val('Z_PIVOT')
    inf = val('INFLATE')
    edges = []
    for w,h,k,dy,dz,th in panels:
        length = math.hypot(dy,dz)
        sin,cos = dy/length,dz/length
        edges.append([w, [[h+u*cos+v*sin-y,k-u*sin+v*cos-z]
                           for v in (-inf,length+inf) for u in (-th/2-inf,th/2+inf)]])
    return dict(names=names,pivot=[0.,y,z],inner=val('INNER'),inflate=inf,span=val('SPAN'),
                tuckY=val('TUCK_Y'),tuckZ=val('TUCK_Z'),headHalf=val('HEAD_HALF'),
                softRise=val('SOFT_RISE'),panels=panels,edges=edges)


def solve(head, depth, *, elytra=False):
    """Batched solver from the uninflated proxy of the outer head (9u per edge)."""
    f = profile()
    h = np.asarray(head)
    d = np.asarray(depth)
    if elytra:
        return np.broadcast_to([f['tuckY'],f['tuckY'],f['tuckZ']],(*d.shape,3))
    axes = (h[..., [1,3,4], :]-h[..., :1,:])/9.
    body = np.broadcast_to(np.eye(3),axes.shape)
    n = np.concatenate((body,axes,-body,-axes),axis=-2)
    middle = np.einsum('...ic,...c->...i',n,h.mean(-2))
    extent = f['headHalf']*np.abs(n@axes.swapaxes(-2,-1)).sum(-1)
    ax, ay, az = np.moveaxis(n,-1,0)
    room = middle-extent-ay*f['pivot'][1]-az*f['pivot'][2]
    depth_stretched = 1+np.minimum(3.2,np.maximum(0,d))/f['span']
    def rise(side,z):
        out=[]
        for w,cs in f['edges']:
            xs = ax*side
            socket = np.maximum(xs*(f['inner']-f['inflate']),xs*(f['inner']+w+f['inflate']))
            v,u = np.asarray(cs).T
            cap = (room[...,None]-socket[...,None]-az[...,None]*(z[...,None,None]*u)) / np.maximum(f['softRise'],ay[...,None]*v)
            out.append(cap.min(-1).max(-1))
        return np.clip(np.minimum.reduce(out),f['tuckY'],1.)
    sy,sx = rise(1, depth_stretched),rise(-1,depth_stretched)
    t=np.clip((np.maximum(sy,sx)-.14)/.38,0.,1.)
    z=f['tuckZ']+(depth_stretched-f['tuckZ'])*t*t*(3-2*t)
    return np.stack((np.minimum(sy,rise(1,z)),np.minimum(sx,rise(-1,z)),z),axis=-1)
