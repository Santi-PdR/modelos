/* Visor de la capa — renderer software en canvas puro.
   Port de tools/preview_cloth.py: mismas matrices, mismas caras, mismo atlas.
   NO es una captura in-game: es la geometría real del geo de Blockbench. */

/* BEGIN LOCAL LOADER */
async function loadJson(name) {
  const response = await fetch(`assets/${name}`);
  if (!response.ok) throw new Error(`No se pudo leer ${name}: ${response.status}`);
  return response.json();
}
function assetUrl(name) { return `assets/${name}`; }
/* END LOCAL LOADER */

let GEO, CLIPS, ATLAS, GLOW, SPARK, ATLAS_W = 128, ATLAS_H = 128;
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
  const parent = {}, h = new Set(['helmet','chestplate','rightArm','leftArm',
    'rightLeg','leftLeg','rightBoot','leftBoot']);
  for (const b of geo.bones) { parent[b.name] = b.parent; if (SECTION_BONES.has(b.name) || HIDDEN_DETAILS.has(b.name)) h.add(b.name); }
  for (const b of geo.bones) { if (b.name.startsWith('v15_cloth_')) h.add(b.name); }
  for (const b of geo.bones) {
    let cur = parent[b.name];
    while (cur) { if (HIDDEN_DETAILS.has(cur)) { h.add(b.name); break; } cur = parent[cur]; }
  }
  return h;
}

/* ---------- Pistas del animation.json del mod ---------- */
const REST = { rotation:[0,0,0], position:[0,0,0], scale:[1,1,1] };
let motionState = 'animation.idle';

function prepare(track) {
  return Object.entries(track).map(([t,p]) => [+t, p.vector || p, p.easing || 'linear'])
      .sort((a,b) => a[0] - b[0]);
}
function prepareClips(data) {
  return Object.fromEntries(Object.entries(data.animations).map(([name,clip]) => [name, {
    length: clip.animation_length,
    bones: Object.fromEntries(Object.entries(clip.bones).map(([n,channels]) => [n,
      Object.fromEntries(Object.entries(channels).filter(([ch]) => ch in REST).map(([ch,t]) =>
        [ch, Array.isArray(t) ? [[0,t,'linear']] : prepare(t)]))])),
  }]));
}
function sample(keys, t, fallback) {
  if (!keys || keys.length === 0) return fallback;
  if (t <= keys[0][0]) return keys[0][1];
  let left=0, right=keys.length;
  while (right-left>1) {
    const m=(left+right)>>1;
    if (keys[m][0] <= t) left=m; else right=m;
  }
  if (right === keys.length) return keys[left][1];
  const [t0,a] = keys[left], [t1,b,ease] = keys[right];
  let f=(t-t0)/(t1-t0);
  if (ease === 'easeInOutSine') f=(1-Math.cos(Math.PI*f))/2;
  else if (ease === 'easeOutSine') f=Math.sin(Math.PI*f/2);
  else if (ease === 'easeInSine') f=1-Math.cos(Math.PI*f/2);
  else if (ease !== 'linear') throw new Error(`Interpolación desconocida: ${ease}`);
  return a.map((v,i) => v+(b[i]-v)*f);
}
function poseAt(geo, clip, t) {
  return {...geo, bones:geo.bones.map(b => {
    const p = clip.bones[b.name] || {};
    const rot = sample(p.rotation,t,REST.rotation);
    return {...b, rotation:(b.rotation || REST.rotation).map((v,i) => v+rot[i]),
      offset:sample(p.position,t,REST.position), scale:sample(p.scale,t,REST.scale)};
  })};
}

function matrices(geo) {
  const by = {}, out = {};
  for (const b of geo.bones) by[b.name] = b;
  function calc(n) {
    if (out[n]) return out[n];
    const b = by[n], p = b.pivot || [0,0,0], B = [-p[0], p[1], p[2]];
    const off = b.offset || [0,0,0];
    const scale=b.scale || REST.scale, S=ident();
    S[0]=scale[0]; S[5]=scale[1]; S[10]=scale[2];
    const local = mul(T([B[0]-off[0], B[1]+off[1], B[2]+off[2]]),
      mul(mul(rotmat(b.rotation || REST.rotation), S), T([-B[0],-B[1],-B[2]])));
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

function playerFaces() {
  // Maniquí Steve/Alex a escala (1 bloque = 16 unidades). NO está en el
  // .geo.json ni en el .bbmodel: sólo se usa para juzgar el ajuste.
  const parts = [
    [-4, 24, -4, 8, 8, 8, [227, 226, 232]],
    [-4, 12, -2, 8, 12, 4, [40, 38, 47]],
    [-8, 12, -2, 4, 12, 4, [59, 54, 64]],
    [ 4, 12, -2, 4, 12, 4, [59, 54, 64]],
    [-4,  0, -2, 4, 12, 4, [45, 40, 48]],
    [ 0,  0, -2, 4, 12, 4, [45, 40, 48]],
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

function collect(geo, hidden) {
  const mats = matrices(geo), faces = [];
  for (const b of geo.bones) {
    if (hidden.has(b.name)) continue;
    const M = mats[b.name];
    for (const c of (b.cubes || [])) {
      const o=c.origin, sz=c.size;
      const d=c.inflate || 0;
      const O = [-(o[0]+sz[0])-d, o[1]-d, o[2]-d];
      const V = CORNERS.map(k => k.map((v,i) => O[i]+v*(sz[i]+2*d)));
      const p=c.pivot || REST.position, pivot=[-p[0],p[1],p[2]];
      const matrix=c.rotation ? mul(M,mul(T(pivot),mul(rotmat(c.rotation),T(pivot.map(v=>-v))))) : M;
      const VT = V.map(v => apply(matrix, v));
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
function render(faces, yaw, pitch, zoom, size, bounds, tint) {
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
    // Misma luz aproximada que el render de comparación registrado.
    const shade=l>1e-6 ? .40+.60*Math.abs((n[0]*LIGHT[0]+n[1]*LIGHT[1]+n[2]*LIGHT[2])/l) : .45;
    prepared.push({pv, uvs:f.uvs, shade, color:f.color || null});
  }
  if (bounds) {
    const points=bounds.map(p=>apply(view,p));
    x0=Math.min(...points.map(p=>p[0])); x1=Math.max(...points.map(p=>p[0]));
    y0=Math.min(...points.map(p=>p[1])); y1=Math.max(...points.map(p=>p[1]));
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
          let ui=Math.floor(uu), vi=Math.floor(vv);
          if (ui<0) ui=0; else if (ui>=AW) ui=AW-1;
          if (vi<0) vi=0; else if (vi>=AH) vi=AH-1;
          const ti=(vi*AW+ui)*4, di=idx*4;
          const solid=q.color;
          const al=solid ? 1 : A[ti+3]/255;
          if (al<=0.03) continue;
          const cr=solid ? solid[0] : A[ti];
          const cg=solid ? solid[1] : A[ti+1];
          const cb=solid ? solid[2] : A[ti+2];
          const lit = q.shade;
          const em = !solid && tint ? GLOW[ti+3]/255 : 0;
          pix[di]   = pix[di]*(1-al) + cr*(lit+em*Math.max(0,(tint?.[0] || 0)-lit))*al;
          pix[di+1] = pix[di+1]*(1-al) + cg*(lit+em*Math.max(0,(tint?.[1] || 0)-lit))*al;
          pix[di+2] = pix[di+2]*(1-al) + cb*(lit+em*Math.max(0,(tint?.[2] || 0)-lit))*al;
          depth[idx]=zz;
        }
      }
    }
  }
  ctx.putImageData(img,0,0);
}

/* FX ilustrativos: los impulsos del servidor y la iluminación de
   Minecraft no corren en el navegador. Se usan los assets del mod. */
const FX = {
  'animation.idle': [2, .004, .003, .34, .010, .72, .17, 0],
  'animation.moving': [1, .009, .011, .40, .010, .79, .21, 0],
  'animation.sprint': [2, .012, .029, .50, .010, .87, .13, .1],
  'animation.air': [2, .021, .027, .55, .011, .87, .12, .18],
  'animation.fall': [2, .010, .023, .46, .017, .74, .25, .04],
  'animation.sneak': [1, .003, .002, .35, .009, .55, .12, 0],
  'animation.swim': [1, .009, .007, .37, .010, .66, .27, .35],
  'animation.deterioro': [3, .023, .017, .39, .015, .63, .37, .28]
};
function simulatedTint(t, length) {
  const [, , , , , base, amp, cool]=FX[motionState];
  const wave=.5+.5*Math.cos(2*Math.PI*t/length);
  const w=motionState==='animation.deterioro' ? (0.62*wave**3+0.38*(1-wave)**3)/.62 : wave;
  const gain=base+amp*w;
  return [gain*(1-.27*cool), gain*(.67+.25*cool), gain*(.86+.33*cool)];
}
function drawRuntimeParticles(seconds, size) {
  const [count, outward, trail, depth, rise]=FX[motionState];
  const sneaking=motionState==='animation.sneak';
  const stride=sneaking ? .8 : .4;
  const shotNow=Math.floor(seconds/stride);
  for (let shot=shotNow-6; shot<=shotNow; shot++) {
    if (shot<0) continue;
    const age=seconds-shot*stride;
    const life=1.98-Math.min(trail/.035,1)*.54;
    if (age<0 || age>=life) continue;
    for (let i=0;i<count;i++) {
      const upper=((motionState==='animation.idle'||motionState==='animation.deterioro')&& i===1)
              || (motionState==='animation.moving' && shot%3===0) || (sneaking && shot%2===0);
      const side=(shot+(i===0?0:1))%2===0?-1:1, low=i!==1;
      const jitter=.5+.5*Math.sin(shot*61.7+i*2.92);
      const x0=side*(upper ? .50+.095*jitter : (low?.24:.41)+.145*jitter);
      const y0=upper ? 1.36+.16*jitter : (low?.13:.54)+.21*jitter;
      const z0=upper ? .34+.08*jitter : depth+.10*(jitter-.5);
      const t=upper ? .005 : trail;
      const p=apply(lastView,[16*(x0+age*14*outward*side),16*(y0+age*13*rise),16*(z0+age*14*t)]);
      const x=size/2+(p[0]-lastCx)*lastScale, y=size/2-(p[1]-lastCy)*lastScale;
      const w=(.60+.19*jitter+.08*(trail>.02))*lastScale;
      ctx.globalAlpha=Math.min(1,age*6)*Math.min(1,(life-age)*2.4)*.79;
      ctx.drawImage(SPARK,x-w/2,y-w/2,w,w);
    }
  }
  ctx.globalAlpha=1;
}

let yaw=25, pitch=10, zoom=1.0, playing=true, t=0, elapsed=0;
let lastFrame=null, dirty=true, hidden=null, frameBounds=null;
let showPlayer=true, showFx=false, referenceView=false;
const seek=document.getElementById('seek'), play=document.getElementById('play');
function setReference(value) {
  referenceView=value;
  document.getElementById('v34').setAttribute('aria-pressed',String(value));
  dirty=true;
}
function setPlaying(value) {
  playing=value;
  if (value) setReference(false);
  play.textContent=playing?'Pausar':'Reproducir';
}

function updateBounds() {
  if (!GEO) return;
  const lo=[Infinity,Infinity,Infinity], hi=[-Infinity,-Infinity,-Infinity];
  const player=playerFaces();
  for (const clip of Object.values(CLIPS)) for (let i=0;i<7;i++) {
    const f=collect(poseAt(GEO,clip,clip.length*i/7),hidden);
    f.push(...player);
    for (const {pts} of f) for (const p of pts) for (let a=0;a<3;a++) {
      lo[a]=Math.min(lo[a],p[a]); hi[a]=Math.max(hi[a],p[a]);
    }
  }
  frameBounds=CORNERS.map(k=>k.map((v,i)=>v?hi[i]:lo[i]));
}
function draw(now) {
  requestAnimationFrame(draw);
  const clip=CLIPS[motionState];
  if (playing && lastFrame!==null) {
    const step=Math.min(.05,(now-lastFrame)/1000);
    t=(t+step)%clip.length; elapsed+=step; dirty=true;
  }
  lastFrame=now;
  if (!dirty) return;
  const faces=collect(referenceView?GEO:poseAt(GEO,clip,t),hidden);
  if (showPlayer) faces.push(...playerFaces());
  render(faces,yaw,pitch,zoom,SIZE,frameBounds,showFx?simulatedTint(t,clip.length):null);
  if (showFx) drawRuntimeParticles(elapsed,SIZE);
  document.getElementById('faces').textContent=faces.length;
  document.getElementById('clock').textContent=referenceView?'Pose base':`${t.toFixed(2).replace('.',',')} s`;
  seek.value=Math.round(t/clip.length*1000);
  dirty=false;
}
function image(name) {
  return new Promise((resolve,reject)=>{
    const im=new Image(); im.onload=()=>resolve(im); im.onerror=()=>reject(new Error(`No se leyó ${name}`));
    im.src=assetUrl(name);
  });
}
function pixels(im) {
  const off=document.createElement('canvas'); off.width=im.width; off.height=im.height;
  const ctx=off.getContext('2d'); ctx.drawImage(im,0,0);
  return ctx.getImageData(0,0,im.width,im.height).data;
}
async function boot() {
  const [geo,clips,atlas,glow,spark]=await Promise.all([
    loadJson('armor.geo.json'), loadJson('armor.animation.json'), image('armor.png'),
    image('armor_glowmask.png'), image('capa_spark_1.png')]);
  GEO=geo['minecraft:geometry'][0]; CLIPS=prepareClips(clips); hidden=runtimeHidden(GEO);
  ATLAS=pixels(atlas); GLOW=pixels(glow); SPARK=spark; ATLAS_W=atlas.width; ATLAS_H=atlas.height;
  updateBounds();
  document.getElementById('bones').textContent=GEO.bones.length;
  document.getElementById('loading').hidden=true;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) setPlaying(false);
  requestAnimationFrame(draw);
}

let drag=null;
canvas.addEventListener('pointerdown',e=>{ drag=[e.clientX,e.clientY]; canvas.setPointerCapture(e.pointerId); });
canvas.addEventListener('pointermove',e=>{
  if (!drag) return;
  yaw+=.46*(e.clientX-drag[0]); pitch=Math.max(-76,Math.min(76,pitch+.46*(e.clientY-drag[1])));
  drag=[e.clientX,e.clientY]; dirty=true;
});
for (const type of ['pointerup','pointercancel','lostpointercapture']) canvas.addEventListener(type,()=>drag=null);
for (const [id,y,p] of [['vBack',0,9],['vFront',180,8],['vSide',-87,8],['vTop',8,58]]) {
  document.getElementById(id).onclick=()=>{yaw=y; pitch=p; dirty=true;};
}
document.getElementById('v34').onclick=()=>{
  yaw=25; pitch=10; t=elapsed=0;
  setPlaying(false); setReference(true);
};
play.onclick=()=>setPlaying(!playing);
seek.oninput=e=>{
  if (!CLIPS) return;
  setPlaying(false); setReference(false); t=CLIPS[motionState].length*(+e.target.value)/1000; elapsed=t; dirty=true;
};
document.getElementById('state').onchange=e=>{ motionState=e.target.value; t=elapsed=0; setReference(false); };
document.getElementById('zoom').oninput=e=>{ zoom=+e.target.value; dirty=true; };
document.getElementById('l_player').onchange=e=>{ showPlayer=e.target.checked; dirty=true; };
document.getElementById('l_particles').onchange=e=>{ showFx=e.target.checked; dirty=true; };

boot().catch(error=>{ document.getElementById('loading').textContent=error.message; });
