#!/usr/bin/env python3
"""GEO equipado: cuello escalonado, costura, placas y jirones con relieve.

Conserva huesos/UUID, geometría oculta e identificador de GeckoLib. El
relieve procede de cubos orientados; la cámara de la referencia sólo fija
la costura y el contorno, no es una textura plana.
"""
from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
import math
from pathlib import Path

import cape_shape as CS
from cape_reference import ORIGIN, lift
from cloth_spec import assert_opaque

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "tools" / "originals" / "capa_deteriorer_evilsaiyan.geo.json"
OUT = ROOT / "src/main/resources/assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json"

INFLATE = (0.01, 0.03, 0.05)

COLLAR_FRONT = 7
COLLAR_FLAPS = 7
COLLAR_BACK = 5
CUEILLO = 3  # v1.32.0: 3 bloques chiquitos junto a la nuca (cuellito)
PADS = 2
CHAIN_LINKS = 8
CRACKS = 10
TAIL_JOINT = 4  # los últimos tres cubos comparten el último pivote visible

# Holgura estática en el +Z del .geo (texels de modelo, 16 por bloque).
# No se añade un canal de posición: se desplazan juntos los mechones y
# las grietas que llevan cosidas. El torso acaba en Z=2.
CLOTH_SETBACK = CS.CLOTH_SETBACK


# Pantalla de referencia (x, y) + profundidad del pliegue; alturas en u.
COWL_BANDS = (
    ('v17_cowl_back_',
     ((446.0, 180.0, 4.9), (475.0, 175.0, 5.76), (511.0, 159.0, 6.91), (536.0, 173.0, 7.21),
      (570.0, 178.0, 6.83), (594.0, 169.0, 5.59)),
     (1.816, 2.456, 2.916, 2.426, 2.898), 0.87, 0.28, 3.0),
    ('v17_cowl_front_',
     ((436.0, 188.0, 4.53), (465.0, 190.0, 5.2), (490.0, 187.0, 6.05), (512.0, 195.0, 6.43),
      (538.0, 202.0, 6.55), (561.0, 197.0, 6.63), (581.0, 188.0, 6.25), (594.0, 178.0, 5.58)),
     (1.794, 2.15, 2.35, 2.55, 2.55, 2.3, 2.2), 0.93, 0.27, -4.5),
    ('v17_cowl_tooth_',
     ((454.0, 199.0, 4.4), (472.0, 203.0, 4.82), (492.0, 208.0, 5.38), (513.0, 219.0, 5.83),
      (535.0, 225.0, 5.68), (556.0, 220.0, 5.77), (579.0, 205.0, 5.46), (597.0, 198.0, 4.98)),
     (1.21, 1.81, 1.81, 1.71, 1.64, 1.54, 1.19), 0.88, 0.28, 0.0),
)
SEAM_PATH = ((464.2, 184.0, 5.603), (481.55, 184.0, 6.295), (504.0, 201.75, 6.838),
             (519.0, 213.0, 6.757), (535.45, 221.8, 6.918), (558.2, 218.8, 6.947),
             (575.0, 203.75, 6.67), (587.0, 192.4, 6.547), (596.85, 184.7, 5.68))
SEAM_HEIGHTS = (0.55, 0.623, 0.85, 0.693, 0.512, 0.524, 0.448, 0.418)

# Correcciones de borde en u de modelo: (traslado X/Y, ancho, alto).
# Afinan las puntas y el canto inferior de las placas a la misma escala
# que el trazado; no añaden huesos ni convierten la tela en una lámina.
RIBBON_TRIM = {
    (0, 4): (-0.13, 0.16, 0.00, -0.12),
    (1, 5): (0.00, -0.06, 0.05, 0.17),
    (1, 6): (-0.21, -0.03, 0.08, -0.23),
    (3, 4): (-0.08, 0.32, 0.09, -0.18),
    (3, 5): (0.00, 0.16, 0.00, -0.23),
    (3, 6): (-0.13, -0.16, 0.00, 0.29),
    (5, 4): (-0.21, 0.32, -0.22, 0.00),
    (5, 5): (0.00, 0.22, 0.08, 0.18),
    (5, 6): (0.13, -0.05, -0.18, 0.12),
    (7, 3): (-0.13, 0.03, 0.41, -0.11),
    (7, 4): (0.22, 0.14, -0.45, 0.30),
    (7, 5): (-0.17, -0.13, 0.54, 0.24),
    (7, 6): (-0.12, 0.00, 0.22, 0.00),
    (8, 4): (0.08, 0.10, -0.19, -0.41),
    (8, 5): (0.00, 0.26, 0.28, 0.03),
    (9, 3): (0.10, 0.13, 0.00, -0.07),
    (9, 4): (0.00, -0.11, 0.08, 0.14),
    (9, 5): (0.00, 0.16, 0.36, 0.14),
    (9, 6): (0.00, -0.18, 0.05, -0.26),
    (10, 5): (0.00, -0.11, -0.01, 0.18),
}
# Raíces cubiertas por el cuello en reposo, con alivio de la nuca al alzar
# el paño en vuelo. (Bajar Y y ajustar relieve Z sin perder el eje X.)
ROOT_CLEARANCE = {4: (.41, .09), 8: (.29, .22), 10: (.24, .08)}
PAD_TRIM = {
    (0, 0): (-0.27, 0.25, -0.62, -0.36),
    (0, 1): (-0.12, 0.00, -0.24, 0.00),
    (0, 2): (0.00, 0.51, 0.00, -0.22),
    (1, 0): (0.21, 0.51, 0.00, -0.58),
    (1, 1): (0.37, -0.04, -0.74, 0.00),  # rebaje interior junto al giro de la cabeza
    (1, 2): (-0.50, 0.00, -0.54, 0.18),
}


def trim_edge(cube, adjustment):
    if adjustment is None:
        return
    x, y, width, height = adjustment
    cube['origin'][0] = round(cube['origin'][0] + x - width / 2, 4)
    cube['origin'][1] = round(cube['origin'][1] + y - height / 2, 4)
    cube['size'][0] = round(cube['size'][0] + width, 4)
    cube['size'][1] = round(cube['size'][1] + height, 4)


FIT_BONE = "cape_wearer_fit"
DRAPE_BONE = "cape_drape_fit"
MOUNT_PREFIX = "v20_mount_"
SEAT_BONE = MOUNT_PREFIX + "seat"
GUSSET_BONE = MOUNT_PREFIX + "gusset"
SADDLE_BONE = MOUNT_PREFIX + "saddle"
SHOULDERS_BONE = MOUNT_PREFIX + "shoulders"
UNDER_YOKE_BONE = MOUNT_PREFIX + "under_yoke"
COLLAR_RETURN = "v17_cowl_return"
FIT_PIVOT = (0., 4.6, 5.6)  # historical pivot; the wearer fit now slides in Z
DRAPE_PIVOT = (0., 22.82, 4.89)  # seam at the start of the cloth
MOUNT_PIVOT = (0., 16., 2.04)   # distance from the torso rear = .04u


@lru_cache(maxsize=1)
def relief():
    return json.loads((ROOT / 'tools/cape_relief.json').read_text())


def apply_relief(geo):
    """Local sculpting corrections in true GEO units, never alpha cutouts."""
    by_name = {b['name']: b for b in geo['bones']}
    shape = relief()
    for key, box in shape['boxes'].items():
        name, ci = key.split(':')
        by_name[name]['cubes'][int(ci)].update(deepcopy(box))
    for name, parts in shape['fragments'].items():
        cubes = by_name[name]['cubes']
        originals = tuple(cubes)
        for part in parts:
            assert 0 <= part['source'] < len(originals), (name, part)
            fragment = deepcopy(originals[part['source']])
            # A relief piece has its own local axes. Retuning the source
            # cuboid must not rotate an unrotated piece around a new pivot.
            fragment.pop('pivot', None)
            fragment.pop('rotation', None)
            fragment.update({k: deepcopy(v) for k,v in part.items() if k != 'source'})
            cubes.append(fragment)


def source_cube(name: str, cube_index: int) -> int:
    """Original section supplying the material and joint of a split part."""
    parts = relief()['fragments'].get(name)
    if parts is not None:
        base = 4 if name.startswith('v18_pad_') else (3 if name.endswith(f'_seg{TAIL_JOINT}') else 1)
        if cube_index >= base:
            return parts[cube_index-base]['source']
    return cube_index


def legacy_element(bone_name: str, cube_index: int) -> tuple[str, int]:
    """Nombre original del elemento en Blockbench tras coser la punta."""
    if source_cube(bone_name, cube_index) != cube_index:
        return bone_name + "_relieve", cube_index
    if bone_name.startswith("v17_ribbon_") and bone_name.endswith(f"_seg{TAIL_JOINT}"):
        return bone_name.rsplit("_seg", 1)[0] + f"_seg{TAIL_JOINT + cube_index}", 0
    return bone_name, cube_index


def ribbon_thick(k: int) -> float:
    """Mechón PLANO pero con cuerpo: 0.68-0.84 unidades de fondo."""
    return 0.76 + 0.08 * math.sin(k * 1.7 + 0.3)


def band(u0: float, w: float, v0: float, h: float) -> dict:
    s = {"uv": [round(u0, 4), round(v0, 4)],
         "uv_size": [round(max(0.5, w), 4), round(max(0.5, h), 4)]}
    assert_opaque(s)
    return s


# Cantos: un parche oscuro y opaco (carbón / sombra), sin filetes.
DARK = band(120.0, 2.0, 100.0, 2.0)
# v1.27.0: la hombrera y la cadena tienen parches PROPIOS. Antes ambas
# muestreaban un gris carbón plano: la hombrera se leía como una masa
# negra y la cadena como una fila de puntos.
PAD_UV = band(97.0, 13.0, 1.0, 13.0)        # cara superior de la placa
PAD_SIDE_UV = band(97.0, 13.0, 65.0, 13.0)  # lateral de la placa
CREST_UV = band(113.0, 13.0, 65.0, 13.0)    # cresta exterior
CHAIN_UV = band(113.0, 13.0, 1.0, 13.0)     # anillo del eslabón
CHAIN_TOP_UV = band(97.0, 13.0, 81.0, 13.0)  # canto superior del eslabón
COLLAR_UV = band(97.0, 28.0, 17.0, 21.0)
NEON_UV = band(98.0, 28.0, 41.0, 21.0)
CUEILLO_UV = band(97.5, 28.0, 65.0, 13.0)  # parche del cuellito (ruff)


def cube16(origin, size, front: dict, side: dict | None = None,
           inflate: float = 0.0) -> dict:
    s = side or DARK
    return {
        "origin": [round(v, 4) for v in origin],
        "size": [round(v, 4) for v in size],
        "uv": {"north": dict(front), "south": dict(front),
               "east": dict(s), "west": dict(s),
               "up": dict(s), "down": dict(s)},
        "inflate": round(inflate, 4),
    }


def cube_faces(origin, size, faces: dict, inflate: float = 0.0) -> dict:
    """v1.27.0: cubo con UV POR CARA.

    La hombrera necesita que su cara superior sea la placa de acero
    iluminada y sus laterales el acero oscuro con filete: con el
    `cube16()` antiguo (dos parches) era imposible.
    """
    missing = {"north", "south", "east", "west", "up", "down"} - set(faces)
    assert not missing, f"faltan caras: {missing}"
    out = {
        "origin": [round(v, 4) for v in origin],
        "size": [round(v, 4) for v in size],
        "uv": {k: dict(v) for k, v in faces.items()},
        "inflate": round(inflate, 4),
    }
    return out


def bone(name: str, parent: str | None, pivot, rotation, cubes) -> dict:
    out = {"name": name,
           "pivot": [round(v, 4) for v in pivot],
           "rotation": [round(v, 4) for v in rotation],
           "cubes": cubes}
    if parent:
        out["parent"] = parent
    return out


def section_for_t(t: float) -> str:
    if t < 0.34:
        return "cape_top"
    if t < 0.67:
        return "cape_mid"
    return "cape_bottom"


def arc_strip(prefix, route, height, depth, front, *, overlap=.20, pitch=0., backing=0.):
    """Dados solapados con tangente XY y en profundidad; sin muescas cúbicas."""
    xyz = [lift(*p) for p in route]
    out = []
    for i, (a, b) in enumerate(zip(xyz, xyz[1:])):
        x,y,z = [(a[k]+b[k])/2 for k in range(3)]
        dx,dy,dz = -b[0]+a[0], b[1]-a[1], b[2]-a[2]
        h = height[i] if isinstance(height, tuple) else height
        w = math.sqrt(dx*dx+dy*dy+dz*dz) + overlap
        ang = [pitch, math.degrees(math.atan2(dz, math.hypot(dx,dy))), math.degrees(math.atan2(dy,dx))]
        c = cube16((x-w/2,y-h/2,z-depth/2-backing),(w,h,depth+backing),front,DARK,INFLATE[0])
        out.append(bone(f'{prefix}{i}', 'chestplate', [x,y,z], ang, [c]))
    return out



def mount_rib(start, end, width, depth):
    """A solid bias-cut panel between two points in GEO coordinates."""
    x, y, z = (b-a for a,b in zip(start,end,strict=True))
    lean = -math.degrees(math.atan2(z, math.hypot(x,y)))
    roll = math.degrees(math.atan2(x,y))
    sx, sy, sz = start
    panel = cube16((sx-width/2, sy-.17, sz-depth/2),
                   (width, math.hypot(x,y,z)+.34, depth), COLLAR_UV, DARK, INFLATE[0])
    panel.update(pivot=list(start), rotation=[round(lean, 6), 0., round(roll, 6)])
    return panel


def mount_bones():
    """Torso seat → broad sewn yoke → fitted collar and pad under-cuffs.

    The deep seat stays in the actual back, not just against its outer face.
    The low gusset stretches up to the collar. Two independent shoulder
    returns reach over the rear corners of the sleeves, and tuck into the
    pads when the wearer needs head or wing room (see CapeFit.shoulderReach).
    A thin lower fold closes the cloth between the returns and the torso.
    It nests in the bottom of the gusset during an arm swing.
    """
    def skin(origin, size):
        return cube16(origin, size, COLLAR_UV, DARK, INFLATE[0])

    seat = [skin((-3.63,14.42,1.60), (7.26,1.90,1.01)),
            skin((-3.56,14.33,2.21), (7.12,1.91,.56)),
            skin((-3.43,14.30,2.55), (6.86,1.87,.32))]
    gusset = [skin((-3.62,14.15,2.09), (7.24,.43,2.65)),
              mount_rib((0,14.38,4.23), (0,17.79,5.06), 7.12,.68),
              mount_rib((0,17.70,4.97), (0,21.34,5.55), 6.95,.51)]
    saddle = [skin((-1.80,20.45,5.245), (3.60,1.75,.58)),
              mount_rib((-1.75,21.16,5.23), (-4.98,22.28,4.51), 1.14,.64),
              mount_rib((1.76,21.06,5.19), (5.12,21.66,4.63), 1.19,.71),
              skin((-5.31,21.45,3.05), (1.10,.56,1.97)),
              skin((4.22,20.87,2.88), (1.10,.84,1.95)),
              skin((-1.12,20.62,3.98), (2.24,1.13,1.41))]
    returns = []
    for side, end_y in ((-1,23.29),(1,23.15)):
        x,y,z = side*5.73,24.68,2.08
        dx,dy,dz = side*5.63-x,end_y-y,5.54-z
        tab = skin((x-1.06,y-.20,z-.12), (2.12,.40,math.hypot(dx,dy,dz)+.24))
        tab.update(pivot=[x,y,z], rotation=[round(math.degrees(math.atan2(dy,math.hypot(dx,dz))),6),
                                           round(math.degrees(math.atan2(dx,dz)),6),0.])
        returns.append(tab)
    y,z,dy,dz = 18.58,1.88,.57,3.83
    under_yoke = skin((-5.74,y-.16,z), (11.48,.32,math.hypot(dy,dz)))
    under_yoke.update(pivot=[0,y,z], rotation=[round(math.degrees(math.atan2(dy,dz)),6),0.,0.])
    from cape_backing import profile
    shape = profile()
    backing = []
    for name, side in zip(shape['names'], (1,-1), strict=True):
        cubes = []
        for width,y,z,dy,dz,th in shape['panels']:
            x = -shape['inner']-width if side == 1 else shape['inner']
            c = skin((x,y-th/2,z),(width,th,math.hypot(dy,dz)))
            c.update(pivot=[0,y,z], rotation=[round(math.degrees(math.atan2(dy,dz)),6),0.,0.])
            cubes.append(c)
        backing.append(bone(name,'chestplate',shape['pivot'],(0,0,0),cubes))
    return [bone(SEAT_BONE, 'chestplate', MOUNT_PIVOT, (0,0,0), seat),
            bone(GUSSET_BONE, 'chestplate', MOUNT_PIVOT, (0,0,0), gusset),
            bone(SADDLE_BONE, FIT_BONE, (0,21.4,5.52), (0,0,0), saddle),
            bone(SHOULDERS_BONE, FIT_BONE, (0,23.20,5.35), (0,0,0), returns),
            bone(UNDER_YOKE_BONE, 'chestplate', (0,14.23,2.10), (0,0,0), [under_yoke]), *backing]

def collar_return():
    """Two tapered ends of the cowl, sharing the collar's live mount.

    Each tab runs toward the front from an overlapping fold in the cowl.
    Keep the centre open and the shoulder plates exactly as authored.
    Coordinates are in GEO space, from the front tip back into the cowl.
    """
    folds = (
        ((-5.18,24.62,3.56), (-5.08,24.50,4.58), .82,.78,-4),
        ((-5.08,24.50,4.58), (-4.14,24.86,6.44), .83,.86,-6),
        ((5.58,24.51,4.14), (5.88,24.53,4.95), 1.16,.79,12),
    )
    cubes = []
    for (x,y,z),(end_x,end_y,end_z),width,height,roll in folds:
        dx,dy,dz = end_x-x,end_y-y,end_z-z
        c = cube16((x-width/2,y-height/2,z-.12), (width,height,math.hypot(dx,dy,dz)+.24),
                   COLLAR_UV, DARK, INFLATE[0])
        c.update(pivot=[x,y,z], rotation=[round(math.degrees(math.atan2(dy,math.hypot(dx,dz))),4),
                                          round(math.degrees(math.atan2(dx,dz)),4),roll])
        cubes.append(c)
    return bone(COLLAR_RETURN, FIT_BONE, (0.,24.,4.8), (0.,0.,0.), cubes)


def build_base() -> dict:
    data = json.loads(ORIGINAL.read_text())
    geo = data["minecraft:geometry"][0]
    original_bones = list(geo["bones"])
    bones = list(original_bones)

    # ------------------------------------------------------------------
    # v1.30.0: SE ANULA LOS CUBOS DE LAS LOSAS cape_top/mid/bottom.
    #
    # Las tiras v17_* (la capa nueva) son HIJAS de estas tres losas.
    # Antes Java las ocultava con setHidden(true), pero en tercera
    # persona (F5) GeckoLib NO renderiza a los hijos de un hueso
    # oculto: la capa entera desaparecía al mirarla desde atrás.
    #
    # Ahora se quitan los cubos de la losa (queda visible, sin cubos)
    # y Java NO las oculta. Las tiras, al ser hijas de un hueso
    # visible, renderizan desde cualquier ángulo. La "masa negra" de
    # la losa original tampoco se ve: no tiene cubos.
    for _slab in ("cape_top", "cape_mid", "cape_bottom"):
        for _b in bones:
            if _b["name"] == _slab:
                _b["cubes"] = []
                if _slab == "cape_top":
                    # Bisagra en la costura externa, no dentro del torso.
                    # El borde alto gira fuera del volumen de la cabeza.
                    _b["pivot"] = list(DRAPE_PIVOT)
                elif _slab == "cape_mid":
                    _b["pivot"] = [0.0, CS.Y_TOP - CS.HEIGHT * 0.34, 4.61]
                else:
                    _b["pivot"] = [0.0, CS.Y_TOP - CS.HEIGHT * 0.67, 4.97]

    # ------------------------------------------------------------------
    # 1. 27 anclas INVISIBLES: dentro del cuello grueso. Java las necesita
    #    para panels[]. v1.53.0: se ponen VISIBLE=FALSE en Blockbench:
    #    antes quedaban apiladas en la parte superior del paño (los
    #    cubos `bottom`/`mid` flotando sueltos donde no deberían verse).
    #    Los huesos SE PRESERVAN (Java los sigue necesitando para
    #    panels[]); solo se oculta la geometría del cubo en Blockbench.
    # ------------------------------------------------------------------
    for si, section in enumerate(("cape_top", "cape_mid", "cape_bottom")):
        for col in range(9):
            ax = (col - 4) * 0.95
            _anchor = cube16((ax - 0.08, 23.52, 2.32), (0.16, 0.16, 0.16),
                             band(2.0 + col * 2.0, 2.0, 100.0, 2.0),
                             DARK, INFLATE[0])
            _anchor["visibility"] = False
            bones.append(bone(
                f"v15_cloth_{section}_{col}", section,
                [ax, 23.60, 2.40], [0.0, 0.0, 0.0], [_anchor]))

    # Cuello granate: dos bandas volumétricas que circundan la nuca.
    # Centro profundo de perfil y caída arqueada hacia la costura inferior.
    # A la misma altura proyectada, el pliegue que roza la nuca queda
    # detrás del hueco de giro de la cabeza. Es relieve estático.
    for profile, clearance in zip(COWL_BANDS, (.98, .56, .31), strict=True):
        prefix, route, heights, depth, over, tilt = profile
        raised = tuple((u,v,z+clearance) for u,v,z in route)
        bones.extend(arc_strip(prefix, raised, heights, depth, COLLAR_UV,
                               overlap=over, pitch=tilt))
    for i, point in enumerate(((485,189,5.79),(518,213,6.25),(551,212,6.51))):
        x,y,z = lift(*point)
        bones.append(bone(f'v19_cuellito_{i}', 'chestplate', [x,y,z], [0,0,0],
                          [cube16((x-.82,y-.62,z-.39),(1.64,1.24,.78),COLLAR_UV,DARK,INFLATE[0])]))

    # Hombreras de carbón/granate. El reborde NO tiene brillo metálico
    # blanco: el negro bajo la ranura es parte visible de la referencia.
    for i in range(PADS):
        side = 1. if i else -1.
        # La placa próxima conserva el canto ancho del original; el
        # hombro opuesto es más compacto, sin simetría forzada.
        x,y,z,w,h,d = ((7.24,22.43,4.16,5.10,2.84,2.12) if side>0
                        else (-5.84,22.35,4.46,3.01,2.12,2.09))
        # Asiento por debajo del labio: llega al dorso del brazo sin
        # atravesarlo. La cara que se ve en la referencia no se mueve.
        seat = .30 if side>0 else .24
        plates = [
            cube16((x-w/2,y-h*.69,z-d/2-seat),(w,h,d+seat), PAD_SIDE_UV,PAD_UV, INFLATE[0]),
            cube16((x-w*.52,y+h*.27,z-d*.57),(w*1.04-(.50 if side<0 else 0.),.56,d*1.14), CREST_UV, PAD_UV, INFLATE[1]),
            cube16((x-w*.40,y-h*.80,z+d*.36),(w*.80,h*.94,.41), PAD_SIDE_UV,DARK, INFLATE[1]),
            cube16((x+w*.32*side-.25,y-h*.49,z+d*.46),(.50,h*.82,.34), CREST_UV, PAD_SIDE_UV, INFLATE[0]),
        ]
        for j, face in enumerate(plates):
            trim_edge(face, PAD_TRIM.get((i, j)))
        bones.append(bone(f'v18_pad_{i}', 'chestplate',[x,y,z], [1.2, side*5., side*-6.], plates))
    # Los mismos ocho huesos de cadena forman una unión oscura continua:
    # deja de ser una joya plateada, se lee como el borde curvo de la foto.
    outer_seam = tuple((u, v, z + 1.02) for u, v, z in SEAM_PATH)
    bones.extend(arc_strip('v18_chain_', outer_seam, SEAM_HEIGHTS,
                           .39, CHAIN_UV, overlap=.24, backing=.53))

    # ------------------------------------------------------------------
    # 4. 12 MECHONES ANCHOS, PLANOS, CURVADOS Y SUPERPUESTOS, EN 2 CAPAS.
    #    7 huesos por mechón (6 tramos + punta afilada).
    # ------------------------------------------------------------------
    for k in range(CS.RIBBONS):
        dep = ribbon_thick(k)
        ribbon = []
        for n in range(CS.SEGS + 1):
            if n == CS.SEGS:
                # Punta corta e irregular, alineada al último tramo.
                t = CS.tip_t(k)
                last = CS.segment_geometry(k, n - 1)
                x, y, z = CS.ribbon_point(k, t)
                z += CLOTH_SETBACK
                w, h = 0.38 + 0.12 * (k % 3), 0.68 + 0.17 * (k % 3)
                pivot = [x, y - h / 2, z + dep / 2]
                angle = [last["bend"], last["twist"], last["theta"] + 3.0 * math.sin(k * 2.3)]
                c = cube16((x - w / 2, y - h, z), (w, h, dep * .8), COLLAR_UV,
                           DARK, INFLATE[(k + 2) % 3])
            else:
                g = CS.segment_geometry(k, n)
                t0, t1 = CS.segment_bounds(k, n)
                t = (t0 + t1) / 2
                x, y, z = g["cx"], g["cy"], g["z"] + 0.012 * n + CLOTH_SETBACK
                w = g["w"] + (0.12 if 2 <= n <= 4 else 0.0)
                h = g["h"]
                if k == 0 and n == TAIL_JOINT:
                    # El jirón corto comparte tramo con la punta, y
                    # necesita un labio de solape cuando sale volando.
                    h += .53
                if n == 0 and k in ROOT_CLEARANCE:
                    trim, back = ROOT_CLEARANCE[k]
                    dx, dy, _ = lift(*ORIGIN, back)
                    x += dx
                    y += dy - trim
                    z += back
                pivot = [x, y, z + dep / 2]
                angle = [g["bend"], g["twist"], g["theta"]]
                c = cube16((x - w / 2, y - h / 2, z), (w, h, dep),
                           COLLAR_UV, DARK, INFLATE[(k + n) % 3])
            trim_edge(c, RIBBON_TRIM.get((k,n)))
            # Una cola continua, no tres dados que se sueltan en el aire:
            # la inclinación de cada sección vive en el cubo. Se preservan
            # nombres y tracks de los dos huesos terminales como anclas.
            if n >= TAIL_JOINT:
                c.update(pivot=[round(v, 4) for v in pivot], rotation=[round(v, 4) for v in angle])
                angle = [0.0, 0.0, 0.0]
            articul = pivot
            if n == TAIL_JOINT:
                jx,jy,jz = CS.ribbon_point(k, t0)
                articul = [jx,jy,jz+CLOTH_SETBACK+dep/2]
            new_bone = bone(f"v17_ribbon_{k}_seg{n}", section_for_t(t), articul, angle,
                            [c] if n <= TAIL_JOINT else [])
            if n > TAIL_JOINT:
                ribbon[TAIL_JOINT]["cubes"].append(c)
            ribbon.append(new_bone)
        bones.extend(ribbon)

    # El nacimiento de los cortes se resolverá en superficie al asignar
    # UV; los huesos los seguimos declarando, conservando UUID y orden.
    for i in range(CRACKS):
        bones.append(bone(f'v17_vein_{i}', 'cape_top', [0, 21, 5], [0.,0.,0.],
                          [cube16((0,21,5),(.20,.51,.04),NEON_UV,NEON_UV,INFLATE[0])]))

    # ---- descripción y garantías -------------------------------------
    geo["bones"] = bones
    desc = geo["description"]
    desc["visible_bounds_width"] = 6.0
    desc["visible_bounds_height"] = 5.6
    desc["visible_bounds_offset"] = [0, 0.5, 0]

    assert geo["bones"][:72] == original_bones, "los 72 huesos originales cambiaron"
    names = {b["name"] for b in bones}
    assert len(names) == len(bones), "nombres de hueso duplicados"
    new = [b for b in bones[72:]]
    assert not any(b["name"].startswith(("v17_mote_", "v17_ash_",
                                        "v16_mote_", "v16_ash_",
                                        "v17_shingle_", "v17_yoke_"))
                   for b in new), "vuelven las tiras / motas sueltas"
    for prefix, expected in (
            ("v15_cloth_", 27),
            ("v17_cowl_front_", COLLAR_FRONT),
            ("v17_cowl_tooth_", COLLAR_FLAPS),
            ("v17_cowl_back_", COLLAR_BACK),
            ("v18_pad_", PADS), ("v18_chain_", CHAIN_LINKS),
            ("v19_cuellito_", CUEILLO),
            ("v17_ribbon_", CS.RIBBONS * (CS.SEGS + 1)),
            ("v17_vein_", CRACKS)):
        got = sum(1 for n in names if n.startswith(prefix))
        assert got == expected, (prefix, got, expected)
    for b in bones:
        assert b.get("parent") is None or b["parent"] in names, b["name"]
    for b in new:
        for c in b["cubes"]:
            for f in c["uv"].values():
                assert_opaque(f)
            assert 0.0 < c["inflate"] <= 0.05, c["inflate"]
    thick = [c["size"][2] for b in new for c in b["cubes"]
             if b["name"].startswith("v17_ribbon_")]
    assert thick and all(0.40 <= v <= 0.85 for v in thick), (min(thick), max(thick))

    apply_relief(geo)
    # Keep the rigid trim together. Head clearance shifts it relative to
    # the fitted back plate, but does not swing the whole model off a low
    # hinge. The drape compensates at its seam to stay closer at the hem.
    for b in bones:
        if b['name'] == 'cape_top':
            b['parent'] = DRAPE_BONE
        elif b['name'].startswith(('v17_cowl_', 'v19_cuellito_', 'v18_pad_', 'v18_chain_')):
            assert b['parent'] == 'chestplate'
            b['parent'] = FIT_BONE
    bones.insert(72, bone(FIT_BONE, 'chestplate', FIT_PIVOT, (0,0,0), []))
    # One body-space fit frame for all cape pieces. In the editable rig it
    # is neutral; the game shortens the entire mount without opening joints.
    from cape_fit import seat_profile
    q = seat_profile()
    mounts = mount_bones()
    for b in [*mounts, next(b for b in bones if b['name'] == FIT_BONE)]:
        if b['parent'] == 'chestplate':
            b['parent'] = q['frame']
    bones.extend([bone(q['frame'], 'chestplate', (0,24,q['plane']), (0,0,0), []),
                  bone(DRAPE_BONE, FIT_BONE, DRAPE_PIVOT, (0,0,0), []), *mounts, collar_return()])
    return data


def build() -> dict:
    from cape_material import map_material

    data = build_base()
    map_material(data['minecraft:geometry'][0], fitted=True)
    return data


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    geo = data["minecraft:geometry"][0]
    cubes = sum(len(b.get("cubes", [])) for b in geo["bones"])
    print(f"wrote {OUT.relative_to(ROOT)}: {len(geo['bones'])} bones, {cubes} cubes")
    print(f"  {CS.RIBBONS} MECHONES ANCHOS x {CS.SEGS + 1} tramos en 2 capas"
          f" | cuello alto {COLLAR_FRONT}+{COLLAR_BACK} | hombreras {PADS}"
          f" | costura {CHAIN_LINKS} | emisión sobre el paño"
          f" | SIN tiras finas ni motas 3D")


if __name__ == "__main__":
    main()
