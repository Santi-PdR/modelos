/* Visor de la capa — renderer software en canvas puro.
   Port de tools/preview_cloth.py: mismas matrices, mismas caras, mismo atlas.
   NO es una captura in-game: es la geometría real del geo de Blockbench. */

const GEO_URL = 'assets/armor.geo.json';
const ATLAS_URL = 'assets/armor.png';

let GEO = null, ATLAS = null, ATLAS_W = 128, ATLAS_H = 128;
const canvas = document.getElementById('view');
const ctx = canvas.getContext('2d', { alpha: false });
let SIZE = 480;

/* ---------- álgebra 4x4 (row-major) ---------- */
function ident() { return [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]; }
function mul(a, b) {
  const o = new Array(16);
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) {
    let s = 0;
    for (let k = 0; k < 4; k++) s += a[i*4+k] * b[k*4+j];
    o[i*4+j] = s;
  }
  return o;
}
function T(v) { const m = ident(); m[3]=v[0]; m[7]=v[1]; m[11]=v[2]; return m; }
function R(axis, deg) {
  const a = deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a), m = ident();
  if (axis === 'x') { m[5]=c; m[6]=-s; m[9]=s; m[10]=c; }
  else if (axis === 'y') { m[0]=c; m[2]=s; m[8]=-s; m[10]=c; }
  else { m[0]=c; m[1]=-s; m[4]=s; m[5]=c; }
  return m;
}
function rotmat(r) { return mul(mul(R('z', r[2] || 0), R('y', -(r[1] || 0))), R('x', -(r[0] || 0))); }
function apply(M, v) {
  return [M[0]*v[0]+M[1]*v[1]+M[2]*v[2]+M[3],
          M[4]*v[0]+M[5]*v[1]+M[6]*v[2]+M[7],
          M[8]*v[0]+M[9]*v[1]+M[10]*v[2]+M[11]];
}

/* ---------- huesos ---------- */
const SECTION_BONES = new Set(['cape_top','cape_mid','cape_bottom']);
const HIDDEN_DETAILS = new Set([
 'arnes_frontal','collar_dentado','yugo','espina_0','espina_1','espina_2',
 'mano_hombro_R','dedo_hR_0','dedo_hR_1','dedo_hR_2','dedo_hR_3','dedo_hR_4',
 'mano_hombro_L','dedo_hL_0','dedo_hL_1','dedo_hL_2','dedo_hL_3','dedo_hL_4',
 'cristal_top_L','flujo_violeta_0','esquirla_0','esquirla_1','nucleo_sigilo',
 'mano_sigilo','dedo_sigilo_0','dedo_sigilo_1','dedo_sigilo_2','dedo_sigilo_3',
 'dedo_sigilo_4','cinturon_oxidado','lengueta','colgajo_R','colgajo_L',
 'cristal_mid_R','cristal_mid_L','flujo_violeta_1','flujo_violeta_2',
 'esquirla_2','esquirla_3','jiron_0','jiron_1','jiron_2','jiron_3','jiron_4',
 'faldon_R','faldon_R_tip','faldon_L','faldon_L_tip','cristal_bot_R',
 'flujo_violeta_3','flujo_violeta_4','esquirla_4','esquirla_5','esquirla_6',
 'esquirla_7','hombrera_der','tira_der_0','tira_der_1','hombrera_izq',
 'tira_izq_0','tira_izq_1']);

/* v1.27.0: las 27 ANCLAS `v15_cloth_*` son cubos de 0.16 que existen
   SÓLO para dar pose a la onda (los usa `panels[]` y el animation.json).
   El runtime Java (`hideClothAnchors`) y el render software
   (`effective_hidden`) ya NO las dibujan: el hueso se conserva, pero el
   render se apaga, para que el cuello no tenga motas negras. El visor tiene
   que hacer lo MISMO, si no sigue enseñando las motas que se arreglaron. */
function runtimeHidden(geo) {
  const parent = {}, h = new Set();
  for (const b of geo.bones) { parent[b.name] = b.parent; if (SECTION_BONES.has(b.name) || HIDDEN_DETAILS.has(b.name)) h.add(b.name); }
  for (const b of geo.bones) { if (b.name.startsWith('v15_cloth_')) h.add(b.name); }
  for (const b of geo.bones) {
    let cur = parent[b.name];
    while (cur) { if (HIDDEN_DETAILS.has(cur)) { h.add(b.name); break; } cur = parent[cur]; }
  }
  return h;
}

/* ---------- animación: espejo EXACTO de tools/cape_motion.py v1.21.0 -----
   Onda VIAJERA periódica (frecuencias 1/2/3), sin restar sin(phase): la
   fase baja por tramo (-0.62*seg + col*0.19) como RETARDO TEMPORAL, no como
   amplitud. Antes todos los huesos volvían a cero en f=0 y f=1: un latido
   con parón, no tela. Ahora hay ráfaga común, arrastre, envolvente por
   tramo, aleteo de alas y DESPLAZAMIENTO ACUMULADO (offset) que curva el
   jirón. Las motas NO están en la geometría: drawRuntimeParticles(). */
const MOTION_STYLES = {
  idle:      {length:4.0, phase:0.00, travel:0.62, flutter:0.045, step:0.00, flare:0.00, shiver:0.00, pull:0.030, breath:0.020, pulse:0.16, gust:0.35, sway:0.25, bias:0.0,  posbias:[0,0,0],        gain:[0.62,0.40,0.60]},
  caminar:   {length:1.2, phase:0.45, travel:0.62, flutter:0.075, step:1.00, flare:0.30, shiver:0.00, pull:0.060, breath:0.028, pulse:0.22, gust:0.80, sway:0.85, bias:0.0,  posbias:[0,0,0],        gain:[1.00,0.68,0.95]},
  correr:    {length:0.8, phase:0.95, travel:0.56, flutter:0.115, step:0.45, flare:1.00, shiver:0.00, pull:0.110, breath:0.045, pulse:0.30, gust:1.25, sway:1.15, bias:-1.5, posbias:[0,0.05,0.12],  gain:[1.65,0.95,1.35]},
  volar:     {length:1.5, phase:2.20, travel:0.60, flutter:0.135, step:0.10, flare:1.55, shiver:0.00, pull:0.150, breath:0.055, pulse:0.34, gust:1.45, sway:1.30, bias:-7.0, posbias:[0,0.42,0.55],  gain:[1.85,1.05,1.55]},
  caer:      {length:0.9, phase:1.15, travel:0.68, flutter:0.150, step:0.00, flare:0.00, shiver:0.30, pull:0.130, breath:0.040, pulse:0.28, gust:1.10, sway:0.90, bias:8.5,  posbias:[0,0.55,0.10],  gain:[1.55,0.90,1.35]},
  agachado:  {length:2.6, phase:0.80, travel:0.70, flutter:0.035, step:0.00, flare:-0.35,shiver:0.00, pull:0.018, breath:0.015, pulse:0.10, gust:0.20, sway:0.15, bias:2.5,  posbias:[0,-0.18,-0.35],gain:[0.48,0.32,0.45]},
  agua:      {length:3.2, phase:2.75, travel:0.72, flutter:0.050, step:0.15, flare:0.20, shiver:0.00, pull:0.045, breath:0.030, pulse:0.20, gust:0.55, sway:0.60, bias:-1.2, posbias:[0,0.12,0.18],  gain:[0.72,0.48,0.70]},
  deterioro: {length:3.0, phase:1.70, travel:0.75, flutter:0.150, step:0.00, flare:0.15, shiver:0.85, pull:0.025, breath:0.012, pulse:0.45, gust:0.55, sway:0.40, bias:0.0,  posbias:[0,0,0],        gain:[0.90,0.55,2.10]}
};

/* Estado elegido desde la UI. 'auto' = según la velocidad, como antes. */
let motionState = 'auto';

function motionParts(n) {
  let m = /^v17_ribbon_(\d+)_seg(\d+)$/.exec(n);
  if (m) return ['ribbon', +m[1], +m[2]];
  const tail = +(n.slice(n.lastIndexOf('_') + 1)) || 0;
  if (n.startsWith('v15_cloth_cape_'))
    return ['tela', tail, n.includes('cape_mid_') ? 3 : (n.includes('cape_bottom_') ? 6 : 0)];
  if (n.startsWith('v15_hem_')) return ['tela', tail, 6];
  if (n.startsWith('v17_cowl_') || n.startsWith('v18_pad_') ||
      n.startsWith('v18_chain_')) return ['cowl', tail, 0];
  if (n.startsWith('v17_vein_')) return ['vein', tail, 0];
  return ['other', tail, 0];
}

/* v1.26.0: EJE DE SIMETRÍA POR FAMILIA = (columnas - 1) / 2, medido
   sobre los pivotes X del geo real. El 7.5 global (16 tiras de la
   élitra) inclinaba toda la capa hacia un lado: el paño de 9 columnas
   iba de -1.0 a +0.07 y ondeaba el doble por la izquierda.
   Espejo exacto de tools/cape_motion.py::axis_of() y de
   CapaArmorModel.motionAxis(); la CI compara los tres ficheros. */
const MOTION_AXES = {ribbon: 5.5, cloth: 4.0, vein: 4.5, cowl: 3.0,
                      cowl_back: 2.0, chain: 3.5, pad: 0.5, default: 5.5};
function motionAxis(n, fam) {
  if (fam === 'ribbon') return MOTION_AXES.ribbon;
  if (fam === 'tela')   return MOTION_AXES.cloth;
  if (fam === 'vein')   return MOTION_AXES.vein;
  if (n.startsWith('v18_chain_')) return MOTION_AXES.chain;
  if (n.startsWith('v18_pad_'))   return MOTION_AXES.pad;
  if (n.startsWith('v17_cowl_back_')) return MOTION_AXES.cowl_back;
  return MOTION_AXES.cowl;
}

/* sin(2πk f + p) y su derivada; sólo usamos el valor en el visor. */
function harm(f, k, p) { const a = 2 * Math.PI * k * f + p; return Math.sin(a); }

function capeMotion(name, f, style) {
  const S = MOTION_STYLES[style];
  const [fam, col, seg] = motionParts(name);
  const segF = Math.min(1, seg / 6);
  // v1.26.0: eje por FAMILIA (columnas reales) + fase/amplitud propias
  // por columna. Antes el 7.5 global inclinaba la capa hacia un lado.
  const axis = motionAxis(name, fam);
  const lateral = (col - axis) / axis;
  const edge = 0.62 + 0.38 * Math.pow(Math.abs(lateral), 1.4);
  const phase = -S.travel * seg + col * 0.19
    + 0.23 * Math.sin(col * 2.13 + 1.7) + S.phase;
  const colAmp = 0.88 + 0.24 * (0.5 + 0.5 * Math.sin(col * 1.93 + 0.6));
  const h = S.flutter * ((fam === 'ribbon' || fam === 'tela') ? (1 + 0.30 * seg) : 1) * colAmp;
  const w = harm(f,1,phase) + 0.28*harm(f,2,phase*1.7) + h*harm(f,3,phase*2.3);
  const gust = 0.72*harm(f,1,0.55) + 0.28*harm(f,2,1.10);
  const drag = 0.5 - 0.5*harm(f,1,phase-0.8+Math.PI/2);
  const sp = harm(f,1,phase*0.5), ss = harm(f,8,col*1.3+seg*0.9);
  const spu = harm(f,1,phase+0.6);
  const G = S.gain;
  let rot = [0,0,0], pos = [0,0,0];
  if (fam === 'ribbon' || fam === 'tela') {
    const amp = (1.60 + 8.50*Math.pow(segF,1.35))*G[0]*edge;
    const flare = S.flare*6, step = S.step*4*lateral;
    const shiver = S.shiver*3.0*(0.30+0.70*segF);
    rot = [amp*0.42*w - flare*(0.62+0.38*drag) + S.gust*1.20*segF*gust,
           step*sp + S.sway*lateral*gust,
           amp*w + S.gust*2.20*segF*gust + shiver*ss];
    if (fam === 'ribbon') {
      const bend = Math.pow(segF,1.6);
      const swing = (0.35+0.85*G[0]+3.0*S.pull)*bend*edge;
      pos = [swing*w + S.gust*0.55*bend*gust,
             -0.28*bend*drag,
             flare*0.10*drag + 0.34*bend*spu];
    }
  } else if (fam === 'cowl') {
    const amp = 1.4*G[1];
    rot = [amp*0.45*w + 0.30*(drag-0.5), 0, amp*0.30*w + 0.25*gust];
  } else if (fam === 'vein') {
    const amp = 5.0*G[2];
    rot = [amp*0.12*w, 0, amp*w];
  } else {
    const amp = 2.4*G[0];
    rot = [amp*0.5*w, 0, amp*w];
  }
  // v1.22.0: silueta del ESTADO (constante ⇒ derivada cero ⇒ C1).
  const lean = S.bias * (0.25 + 0.75*segF);
  rot[0] += lean;
  if (fam === 'ribbon') {
    const bend = Math.pow(segF,1.6);
    pos[0] += S.posbias[0]*bend;
    pos[1] += S.posbias[1]*bend;
    pos[2] += S.posbias[2]*bend;
  }
  return [rot[0],rot[1],rot[2], pos[0],pos[1],pos[2]];
}

function animate(geo, t, speed) {
  const out = geo.bones.map(b => ({ ...b,
    rotation: (b.rotation || [0,0,0]).slice(), offset: [0,0,0] }));
  const style = (motionState !== 'auto') ? motionState :
        (speed < 0.15 ? 'idle' : (speed < 0.65 ? 'caminar' : 'correr'));
  const f = ((t / MOTION_STYLES[style].length) % 1 + 1) % 1;
  for (const b of out) {
    const n = b.name;
    if (n.startsWith('v17_') || n.startsWith('v18_') ||
        n.startsWith('v15_cloth_') || n.startsWith('v15_hem_')) {
      const r = capeMotion(n, f, style);
      b.rotation[0] += r[0]; b.rotation[1] += r[1]; b.rotation[2] += r[2];
      b.offset = [r[3], r[4], r[5]];
    } else if (n.startsWith('v15_rear_pad_')) {
      const i = n.endsWith('L') ? 0 : 1;
      b.rotation[0] += Math.sin(t * 2.6 + i * 1.7) * (1.0 + speed * 2.0);
      b.rotation[2] += Math.sin(t * 1.8 + i * 1.2) * 0.8;
    } else if (n.startsWith('v15_orbit_')) {
      const i = parseInt(n.slice(n.lastIndexOf('_') + 1), 10) || 0;
      b.rotation[2] += Math.sin(t * 0.85 + i * Math.PI / 2) * 2.0;
    } else if (n.startsWith('v15_pauldron_') || n.startsWith('v15_front_chain_')) {
      b.rotation[2] += Math.sin(t * 2.1 + n.length * 0.3) * 1.4;
    }
  }
  return { ...geo, bones: out };
}

function matrices(geo) {
  const by = {}, out = {};
  for (const b of geo.bones) by[b.name] = b;
  function calc(n) {
    if (out[n]) return out[n];
    const b = by[n], p = b.pivot || [0,0,0], B = [-p[0], p[1], p[2]];
    const off = b.offset || [0,0,0];
    const local = mul(T([-off[0], off[1], off[2]]),
      mul(mul(T(B), rotmat(b.rotation || [0,0,0])), T([-B[0],-B[1],-B[2]])));
    const P = b.parent ? calc(b.parent) : ident();
    out[n] = mul(P, local);
    return out[n];
  }
  for (const n in by) calc(n);
  return out;
}

const CORNERS = [[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]];
const FACE_ORDER = {
  west:[7,3,0,4], east:[2,6,5,1], north:[3,2,1,0],
  south:[6,7,4,5], up:[7,6,2,3], down:[0,1,5,4]
};
function faceUV(s) {
  const u=s.uv[0], v=s.uv[1], w=s.uv_size[0], h=s.uv_size[1];
  return [[u+w,v],[u,v],[u,v+h],[u+w,v+h]];
}

function layerFilter(name, layers) {
  if (!layers.cloth && (name.startsWith('v15_cloth_') || name.startsWith('v15_orbit_'))) return true;
  if (!layers.collar && (name.startsWith('v17_cowl_') || name.startsWith('v18_pad_') ||
      name.startsWith('v18_chain_') || name.startsWith('v15_rear_pad_'))) return true;
  if (!layers.shreds && (name.startsWith('v17_ribbon_') || name.startsWith('v15_hem_'))) return true;
  if (!layers.energy && name.startsWith('v17_vein_')) return true;
  // rev. B: `layers.particles` controla un OVERLAY 2D de runtime, no
  // filtra cubos. No existe ningún hueso de partícula en el geo.
  return false;
}

function playerFaces() {
  // Maniquí Steve/Alex a escala (1 bloque = 16 unidades). NO está en el
  // .geo.json: existe aquí y en el .bbmodel para juzgar el ajuste al cuello.
  const parts = [
    [-4, 24, -4, 8, 8, 8, [216, 214, 222]],
    [-4, 12, -2, 8, 12, 4, [58, 42, 76]],
    [-8, 12, -2, 4, 12, 4, [88, 62, 112]],
    [ 4, 12, -2, 4, 12, 4, [88, 62, 112]],
    [-4,  0, -2, 4, 12, 4, [42, 30, 56]],
    [ 0,  0, -2, 4, 12, 4, [42, 30, 56]],
  ];
  const out = [];
  for (const [x, y, z, w, h, d, color] of parts) {
    const V = CORNERS.map(k => [x + k[0]*w, y + k[1]*h, z + k[2]*d]);
    for (const fn in FACE_ORDER) {
      const idx = FACE_ORDER[fn];
      out.push({ pts: idx.map(i => V[i]), uvs: [[0,0],[0,0],[0,0],[0,0]], color });
    }
  }
  return out;
}

function collect(geo, hidden, layers) {
  const mats = matrices(geo), faces = [];
  for (const b of geo.bones) {
    if (hidden.has(b.name) || layerFilter(b.name, layers)) continue;
    const M = mats[b.name];
    for (const c of (b.cubes || [])) {
      const o=c.origin, sz=c.size;
      const O = [-(o[0]+sz[0]), o[1], o[2]];
      const V = CORNERS.map(k => [O[0]+k[0]*sz[0], O[1]+k[1]*sz[1], O[2]+k[2]*sz[2]]);
      const VT = V.map(v => apply(M, v));
      for (const fn in FACE_ORDER) {
        const spec = c.uv && c.uv[fn];
        if (!spec) continue;
        const idx = FACE_ORDER[fn];
        faces.push({ pts: idx.map(i => VT[i]), uvs: faceUV(spec) });
      }
    }
  }
  return faces;
}

/* ---------- rasterizador con z-buffer ---------- */
let lastScale = null, lastCx = 0, lastCy = 0, lastView = null;
function render(faces, yaw, pitch, zoom, size) {
  const view = mul(R('x', pitch), R('y', yaw));
  lastView = view;
  const prepared = [];
  let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9;
  const LIGHT = [-0.35, 0.65, 0.68];
  const ln = Math.hypot(...LIGHT);
  for (let i=0;i<3;i++) LIGHT[i] /= ln;
  for (const f of faces) {
    const pv = f.pts.map(p => apply(view, p));
    const e1=[pv[1][0]-pv[0][0],pv[1][1]-pv[0][1],pv[1][2]-pv[0][2]];
    const e2=[pv[2][0]-pv[0][0],pv[2][1]-pv[0][1],pv[2][2]-pv[0][2]];
    const n=[e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2], e1[0]*e2[1]-e1[1]*e2[0]];
    const l=Math.hypot(...n);
    // Iluminacion de presentacion: luz principal + relleno + rim en las
    // caras de perfil + gamma suave. Antes el minimo 0.40 aplastaba el
    // violeta y la capa parecia una silueta plana.
    let shade=0.52;
    if (l>1e-6) {
      const nd=Math.abs((n[0]*LIGHT[0]+n[1]*LIGHT[1]+n[2]*LIGHT[2])/l);
      const rim=1.0-Math.abs(n[2]/l);
      // v1225: especular suave en las caras de frente y mas rim en los
      // perfiles. Los pliegues se leen como tela con volumen, no como
      // laminas planas. Solo afecta al visor, nunca a la autoevaluacion.
      const spec=Math.pow(nd,6)*0.12;
      shade=Math.pow(Math.min(1,0.48+0.40*nd+0.12*rim+spec),0.90);
    }
    for (const p of pv) { x0=Math.min(x0,p[0]); x1=Math.max(x1,p[0]); y0=Math.min(y0,p[1]); y1=Math.max(y1,p[1]); }
    prepared.push({pv, uvs:f.uvs, shade, color:f.color || null});
  }
  const cx=(x0+x1)/2, cy=(y0+y1)/2;
  const base = Math.min((size-46)/(x1-x0||1), (size-46)/(y1-y0||1));
  const scale = base * zoom;
  lastScale = scale; lastCx = cx; lastCy = cy;

  const img = ctx.createImageData(size, size);
  const pix = img.data;
  const BG=[18,14,26];
  for (let i=0;i<size*size;i++) { pix[i*4]=BG[0]; pix[i*4+1]=BG[1]; pix[i*4+2]=BG[2]; pix[i*4+3]=255; }
  const depth = new Float32Array(size*size).fill(-1e9);
  const A = ATLAS, AW=ATLAS_W, AH=ATLAS_H;

  for (const q of prepared) {
    const scr = q.pv.map(p => [size/2+(p[0]-cx)*scale, size/2-(p[1]-cy)*scale]);
    const z = q.pv.map(p => p[2]);
    const U = q.uvs;
    for (const [i,j,k] of [[0,1,2],[0,2,3]]) {
      const p0=scr[i], p1=scr[j], p2=scr[k];
      const m00=p1[0]-p0[0], m01=p2[0]-p0[0], m10=p1[1]-p0[1], m11=p2[1]-p0[1];
      const det=m00*m11-m01*m10;
      if (Math.abs(det)<1e-6) continue;
      const i00=m11/det, i01=-m01/det, i10=-m10/det, i11=m00/det;
      const bx0=Math.max(0,Math.floor(Math.min(p0[0],p1[0],p2[0])));
      const bx1=Math.min(size,Math.ceil(Math.max(p0[0],p1[0],p2[0]))+1);
      const by0=Math.max(0,Math.floor(Math.min(p0[1],p1[1],p2[1])));
      const by1=Math.min(size,Math.ceil(Math.max(p0[1],p1[1],p2[1]))+1);
      if (bx1<=bx0||by1<=by0) continue;
      for (let yy=by0; yy<by1; yy++) {
        const dy=yy-p0[1];
        for (let xx=bx0; xx<bx1; xx++) {
          const dx=xx-p0[0];
          const a=i00*dx+i01*dy, b=i10*dx+i11*dy;
          if (a<-1e-6||b<-1e-6||a+b>1+1e-6) continue;
          const zz=z[i]+a*(z[j]-z[i])+b*(z[k]-z[i]);
          const idx=yy*size+xx;
          if (zz<=depth[idx]) continue;
          const uu=U[i][0]+a*(U[j][0]-U[i][0])+b*(U[k][0]-U[i][0]);
          const vv=U[i][1]+a*(U[j][1]-U[i][1])+b*(U[k][1]-U[i][1]);
          let ui=Math.round(uu), vi=Math.round(vv);
          if (ui<0) ui=0; else if (ui>=AW) ui=AW-1;
          if (vi<0) vi=0; else if (vi>=AH) vi=AH-1;
          const ti=(vi*AW+ui)*4, di=idx*4;
          const solid=q.color;
          const al=solid ? 1 : A[ti+3]/255;
          if (al<=0.03) continue;
          const cr=solid ? solid[0] : A[ti];
          const cg=solid ? solid[1] : A[ti+1];
          const cb=solid ? solid[2] : A[ti+2];
          const s=q.shade;
          pix[di]  = pix[di]*(1-al) + cr*s*al;
          pix[di+1]= pix[di+1]*(1-al) + cg*s*al;
          pix[di+2]= pix[di+2]*(1-al) + cb*s*al;
          depth[idx]=zz;
        }
      }
    }
  }
  ctx.putImageData(img,0,0);
}

/* ---------- partículas RUNTIME (no son geometría) ----------
   18 motas con la distribución medida en la referencia. Se emiten y
   desplazan aquí, en el visor, igual que `spawnAura()` las emite en el
   juego desde el servidor. No hay ni un cubo asociado. */
/* v1.23.0: las chispas nacen SÓLO en los bordes y las puntas inferiores
   del paño (y=2..13, |x|=4..9). NO hay halo detrás de la cabeza: era el
   efecto que el usuario veía acumulado en las capturas in-game. */
const SPARK_SEEDS = [
  [-8.3, 4.2, 3.1], [8.5, 3.6, 3.2], [-7.1, 6.0, 3.0], [7.4, 5.4, 3.3],
  [-6.0, 8.4, 2.9], [6.2, 7.8, 3.1], [-9.0, 9.6, 2.8], [8.9, 10.2, 3.0],
  [-4.6, 3.0, 3.2], [4.8, 3.4, 3.3], [-5.4, 11.4, 2.9], [5.6, 11.9, 3.0],
  [-3.6, 2.2, 3.1], [3.7, 2.6, 3.2], [-7.8, 12.6, 2.8], [7.9, 12.2, 3.0]
];

function drawRuntimeParticles(t, speed, size) {
  if (!lastView || !lastScale) return;
  // Espejo 2D de CapaSparkParticle: rectángulo VERTICAL estrecho,
  // semitransparente, centro casi blanco, sube suave y se desvanece.
  // 16 semillas como máximo, SIN geometría, SIN fetch, SIN lag.
  const intense = (motionState === 'correr' || motionState === 'volar' ||
                   motionState === 'caer' || motionState === 'deterioro' ||
                   (motionState === 'auto' && speed > 0.65));
  const shown = intense ? 9 : 6;

  for (let i = 0; i < shown; i++) {
    const [bx, by, bz] = SPARK_SEEDS[i];
    const life = ((t * (0.16 + speed * 0.10) + i * 0.271) % 1);
    const p = [bx + Math.sin(t * 0.8 + i * 1.9) * 0.16,
               by + life * 1.9,
               bz + Math.cos(t * 0.6 + i) * 0.10];
    const v = apply(lastView, p);
    const sx = size / 2 + (v[0] - lastCx) * lastScale;
    const sy = size / 2 - (v[1] - lastCy) * lastScale;
    if (sx < -20 || sy < -20 || sx > size + 20 || sy > size + 20) continue;

    const fade = Math.sin(Math.PI * life);
    const a = 0.62 * fade;
    const w = 3 + 1.5 * fade;          // estrecho
    const h = 9 + 5 * fade;            // VERTICAL
    // Borde magenta semitransparente.
    ctx.fillStyle = `rgba(236,46,178,${a * 0.42})`;
    ctx.fillRect(sx - w, sy - h / 2, w * 2, h);
    // Núcleo rosa.
    ctx.fillStyle = `rgba(255,96,210,${a * 0.72})`;
    ctx.fillRect(sx - w * 0.55, sy - h / 2, w * 1.1, h);
    // Centro brillante.
    ctx.fillStyle = `rgba(255,224,248,${a})`;
    ctx.fillRect(sx - w * 0.18, sy - h / 2, w * 0.36, h);
  }
}

/* ---------- estado / UI ---------- */
let yaw=0, pitch=8, zoom=1.0, playing=true, t=0, speed=0.35;
let lastFrame=0, dirty=true;
const layers = { cloth:true, collar:true, shreds:true, particles:true, energy:true };
let showPlayer = false;  // v1.21.0: la capa SOLA se ve mejor
let hidden = null;
/* v1.27.0: diagnóstico. Las 27 anclas v15_cloth_* están ocultas (igual que
   en el runtime Java y en el render software). Con esta casilla se vuelven
   a pintar para ver de dónde salían las motas negras. Es el equivalente del
   modo ANCLAS de \`capa.visibilidad\` y de \`--show-anchors\` del render. */
let showAnchors = false;

function draw(now) {
  requestAnimationFrame(draw);
  if (!GEO || !ATLAS) return;
  if (playing) { t += Math.min(0.05,(now-lastFrame)/1000) * (0.6+speed*1.4); dirty=true; }
  lastFrame=now;
  if (!dirty) return;
  const g = animate(GEO, t, speed);
  const faces = collect(g, hidden, layers);
  if (showPlayer) faces.push(...playerFaces());
  render(faces, yaw, pitch, zoom, SIZE);
  if (layers.particles) drawRuntimeParticles(t, speed, SIZE);
  document.getElementById('faces').textContent = faces.length;
  dirty=false;
}

async function boot() {
  const geo = await (await fetch(GEO_URL)).json();
  GEO = geo['minecraft:geometry'][0];
  hidden = runtimeHidden(GEO);
  const im = new Image();
  im.src = ATLAS_URL;
  await new Promise(r => im.onload = r);
  const off = document.createElement('canvas'); off.width=im.width; off.height=im.height;
  const octx = off.getContext('2d'); octx.drawImage(im,0,0);
  const d = octx.getImageData(0,0,im.width,im.height);
  ATLAS = new Uint8ClampedArray(d.data); ATLAS_W=im.width; ATLAS_H=im.height;
  document.getElementById('loading').style.display='none';
  document.getElementById('bones').textContent = GEO.bones.length;
  requestAnimationFrame(draw);
  drawIcons();
}

/* ---------- iconos animados ---------- */
const ICON_MAP = {
  fiel: null, blight: null
};
let PAL = {
 '.':[0,0,0,0], K:[12,5,18,255], H:[42,11,28,255], D:[66,24,70,255],
 M:[88,30,84,255], L:[112,52,108,255], G:[232,104,172,255],
 W:[255,222,238,255], C:[214,34,138,255], E:[96,22,72,255], P:[140,20,96,255]
};
async function loadIconRows() {
  // Se leen del pipeline para que el visor muestre EXACTAMENTE lo que hay en el código.
  const txt = await (await fetch('assets/icon_src.txt')).text();
  const m = txt.match(/ICON_ALTERNATIVE = \(([\s\S]*?)\n\)/);
  const n = txt.match(/ICON_PIXEL_MAP = \(([\s\S]*?)\n\)/);
  const grab = s => (s.match(/"([.A-Z]{16})"/g) || []).map(x => x.slice(1,-1));
  ICON_MAP.fiel = grab(m[1]);
  ICON_MAP.blight = grab(n[1]);
  const pm = txt.match(/ICON_PALETTE = \{([\s\S]*?)\n\}/);
  if (pm) {
    const out = {'.':[0,0,0,0]};
    for (const hit of pm[1].matchAll(/"([A-Z.])":\s*\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)/g)) {
      out[hit[1]] = [+hit[2], +hit[3], +hit[4], +hit[5]];
    }
    PAL = out;
  }
}
let iconChoice='blight', iconFrame=0;
function iconTick() {
  requestAnimationFrame(iconTick);
  if (!ICON_MAP.blight || !ICON_MAP.fiel) return;
  iconFrame += 1;
  if (iconFrame % 4 !== 0) return;
  const phase = Math.sin(performance.now()/520);
  for (const id of ['iconA','iconB']) {
    const cv=document.getElementById(id); if(!cv) continue;
    const which = id==='iconA' ? iconChoice : (iconChoice==='blight'?'fiel':'blight');
    const rows=ICON_MAP[which]; if(!rows || rows.length!==16) continue;
    const c=cv.getContext('2d'), S=14;
    c.clearRect(0,0,cv.width,cv.height);
    c.fillStyle='#120e1a'; c.fillRect(0,0,cv.width,cv.height);
    for (let y=0;y<16;y++) for (let x=0;x<16;x++) {
      let ch=rows[y][x];
      // animación: la estrella y el broche pulsan; el festón ondea 1 px
      if (ch==='C' && phase>0.35) ch='W';
      if (ch==='G' && phase>0.80) ch='W';
      let dy=0;
      if (y===15 && ch!=='.') dy = phase>0.4 ? -1 : 0;
      const col=PAL[ch]; if(!col || col[3]===0) continue;
      c.fillStyle=`rgba(${col[0]},${col[1]},${col[2]},${col[3]/255})`;
      c.fillRect(x*S,(y+dy)*S,S,S);
    }
  }
}
async function drawIcons() { await loadIconRows(); requestAnimationFrame(iconTick); }

/* ---------- interacción ---------- */
let dragging=false, lx=0, ly=0;
canvas.addEventListener('pointerdown', e => { dragging=true; lx=e.clientX; ly=e.clientY; canvas.setPointerCapture(e.pointerId); });
canvas.addEventListener('pointerup', () => dragging=false);
canvas.addEventListener('pointermove', e => {
  if (!dragging) return;
  yaw += (e.clientX-lx)*0.55; pitch = Math.max(-70,Math.min(70,pitch+(e.clientY-ly)*0.4));
  lx=e.clientX; ly=e.clientY; dirty=true;
});
canvas.addEventListener('wheel', e => {
  e.preventDefault(); zoom=Math.max(0.55,Math.min(2.4,zoom*(e.deltaY>0?0.92:1.08))); dirty=true;
}, {passive:false});

function setView(y,p) { yaw=y; pitch=p; dirty=true; }
document.getElementById('vFront').onclick = ()=>setView(180,8);
document.getElementById('vBack').onclick  = ()=>setView(0,8);
document.getElementById('vSide').onclick  = ()=>setView(-62,14);
document.getElementById('v34').onclick    = ()=>setView(25,14);
document.getElementById('vTop').onclick   = ()=>setView(0,52);
document.getElementById('play').onclick = e => {
  playing=!playing; e.target.textContent = playing?'⏸ Pausar animación':'▶ Reproducir animación'; dirty=true;
};
document.getElementById('speed').oninput = e => { speed=parseFloat(e.target.value); document.getElementById('speedVal').textContent=speed.toFixed(2); };
document.getElementById('res').onchange = e => {
  SIZE=parseInt(e.target.value,10); canvas.width=SIZE; canvas.height=SIZE; dirty=true;
};
for (const k of Object.keys(layers)) {
  const el=document.getElementById('l_'+k);
  if (el) el.onchange = () => { layers[k]=el.checked; dirty=true; };
}
const aEl=document.getElementById('l_anchors');
if (aEl) aEl.onchange = () => {
  showAnchors = aEl.checked;
  if (!GEO) return;                       // el geo aún no ha cargado
  hidden = runtimeHidden(GEO);
  if (showAnchors) for (const b of GEO.bones) {
    if (b.name.startsWith('v15_cloth_')) hidden.delete(b.name);
  }
  dirty = true;
};
const pEl=document.getElementById('l_player');
const stEl=document.getElementById('state');
if (stEl) stEl.onchange = () => { motionState=stEl.value; dirty=true; };

if (pEl) pEl.onchange = () => { showPlayer=pEl.checked; dirty=true; };
document.getElementById('choice').onchange = e => { iconChoice=e.target.value; };

boot().catch(e => { document.getElementById('loading').textContent='Error: '+e.message; });
