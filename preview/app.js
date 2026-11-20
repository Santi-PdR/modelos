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

let GEO, CLIPS, FIT, STRIDE, SWAY, WINGS, REF, ORIGINAL, ATLAS, GLOW, HALO, NOCTURNE, SPARKS, AURA, ATLAS_W = 128, ATLAS_H = 128;
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

function backset(profile, stance, look, turn) {
  const table=profile.backset;
  const axis=(v,n)=>{
    v=Math.min(n-1, Math.max(0,v));
    const i=Math.min(Math.floor(v),n-2);
    return [i,v-i];
  };
  const lerp=(a,b,t)=>a+(b-a)*t;
  const [st,ft]=axis(stance*(table.length-1),table.length);
  const wrapped=((turn+180)%360+360)%360-180;
  const [sy,fy]=axis(Math.abs(wrapped)/profile.yawStep,table[0].length);
  const [sp,fp]=axis((look+90)/profile.pitchStep,table[0][0].length);
  const row=k=>lerp(lerp(table[k][sy][sp],table[k][sy][sp+1],fp),
    lerp(table[k][sy+1][sp],table[k][sy+1][sp+1],fp),fy);
  return lerp(row(st),row(st+1),ft);
}
function shoulderScales(stance, look, turn, elytra=false) {
  const yaw=Math.abs(((turn+180)%360+360)%360-180);
  const down=smooth(34,62,-look)*(1-.62*smooth(44,73,yaw))*(1-.52*smooth(0,1,stance));
  const ahead=.45*(1-smooth(0,3,yaw))*(1-smooth(0,42,Math.abs(look)))*(1-.66*smooth(0,.70,stance));
  const length=elytra ? .245 : .245+.755*Math.max(down,ahead);
  return [1,.27+.73*length,length];
}
function yokeScales(stance, look, arm, elytra=false) {
  const posture=elytra ? 0 : (1-smooth(0,.60,stance))*(1-smooth(42,83,look));
  const sleeve=1-smooth(2.9,6.1,arm), spread=posture*sleeve;
  return [.51+.49*spread,.065+.935*posture*smooth(0,.44,sleeve),.62+.38*spread];
}
// Same head box and separating planes as CapeBacking, in body space.
function backingShape(f, bodyAngle, stance, look, turn, depth, elytra) {
  if (elytra) return [f.tuckY,f.tuckY,f.wingZ];
  const tilt = stance*bodyAngle*Math.PI/180, p = look*Math.PI/180, a = turn*Math.PI/180;
  const [cl,sl,co,si,cy,sy] = [Math.cos(tilt),Math.sin(tilt),Math.cos(p),Math.sin(p),Math.cos(a),Math.sin(a)];
  const x = [cy,sl*sy,-cl*sy], y = [sy*si,cl*co-sl*cy*si,sl*co+cl*cy*si],
        z = [sy*co,-cl*si-sl*cy*co,-sl*si+cl*cy*co];
  const center = [4*y[0],24-stance*cl+4*y[1],-stance*sl+4*y[2]];
  const dot = (u,v) => u[0]*v[0]+u[1]*v[1]+u[2]*v[2];
  const planes = [];
  for (const n of [[1,0,0],[0,1,0],[0,0,1],x,y,z]) {
    const extent = f.headHalf*(Math.abs(dot(n,x))+Math.abs(dot(n,y))+Math.abs(dot(n,z)));
    for (const sign of [1,-1]) {
      const [ax,ay,az] = n.map(v => sign*v);
      planes.push([ax,ay,az,sign*dot(n,center)-extent-ay*f.pivot[1]-az*f.pivot[2]]);
    }
  }
  function rise(side, depthScale) {
    let height = 1;
    for (const [width,edges] of f.edges) {
      let best = 0;
      for (const [ax,ay,az,clear] of planes) {
        const room = clear - Math.max(side*ax*(f.inner-f.inflate),side*ax*(f.inner+width+f.inflate));
        let safe = 1;
        for (const [h,d] of edges) safe = Math.min(safe,(room-az*depthScale*d)/Math.max(f.softRise,ay*h));
        best = Math.max(best,safe);
      }
      height = Math.min(height,best);
    }
    return Math.max(f.tuckY,height);
  }
  const stretch = 1+Math.min(f.maxBackset,Math.max(0,depth))/f.span;
  let l = rise(1,stretch), r = rise(-1,stretch);
  const scale = f.tuckZ+(stretch-f.tuckZ)*smooth(f.foldMin,f.foldMin+f.foldSpan,Math.max(l,r));
  if (scale < stretch-1e-8) { l=Math.min(l,rise(1,scale)); r=Math.min(r,rise(-1,scale)); }
  return [l,r,scale];
}
function seating(q, stance, look, turn, arm, elytra) {
  if (elytra || ![stance,look,turn,arm].every(Number.isFinite)) return 0;
  const yaw = Math.abs(((turn+180)%360+360)%360-180);
  return smooth(q.downStart,q.downFull,-look) * (1-smooth(q.turnStart,q.turnEnd,yaw))
      * (1-smooth(q.leanStart,q.leanEnd,stance)) * (1-smooth(q.armStart,q.armEnd,arm));
}

function plateInfluence(profile, stance, look, turn, arm, elytra) {
  if (!profile || elytra || ![stance, look, turn, arm].every(Number.isFinite)) return 0;
  const [a,b,c,d,e,f,g,h] = profile.limits;
  const yaw = Math.abs(((turn+180)%360+360)%360-180);
  return smooth(a,b,-look) * (1-smooth(c,d,yaw)) * (1-smooth(e,f,stance)) * (1-smooth(g,h,arm));
}

function plateFrame(bone, target, k) {
  const [x,y,z,sx,sy,sz,lift,advance,rx,ry] = target;
  return {name:'fit_'+bone.name, parent:bone.parent, pivot:[-x,y,z], offset:[0,k*lift,k*advance],
    rotation:[-k*rx,-k*ry,0], scale:[1+k*(sx-1),1+k*(sy-1),1+k*(sz-1)], cubes:[]};
}

function plateRim(bone, profile, target, k) {
  const [a,b,c,d] = profile.lips;
  const rise=smooth(a,b,k), reach=smooth(c,d,k);
  const [x,y,z,across,lift,advance,sx,sy,sz,pitch] = target;
  return {name:'rim_'+bone.name,parent:bone.name,pivot:[-x,y,z],
    offset:[-reach*across,rise*lift,reach*advance],rotation:[-rise*pitch,0,0],
    scale:[1+reach*(sx-1),1+rise*(sy-1),1+reach*(sz-1)],cubes:[bone.cubes[profile.rimCube]]};
}

function torsoShape(data, stance, look, yaw, depth, seat, plate, arm, effort, dry=1, elytra=false) {
  if (!data || elytra || dry<=0 || ![stance,look,yaw,depth,arm,effort,dry,seat,plate].every(Number.isFinite))
    return [0,null,null,null,null,null];
  const signedTurn=((yaw+180)%360+360)%360-180;
  const down=-look, turn=Math.abs(signedTurn);
  const leanRoom=1-smooth(.05,.36,stance), steepRoom=1-.82*smooth(62,88,down)*smooth(24,36,turn);
  const sleeveRoom=1-smooth(2.85,6,effort), release=smooth(44,57,turn);
  const space=(1-smooth(.02,.40,depth))*leanRoom*(1-release)*steepRoom;
  const reach=space*sleeveRoom;
  const tuck=dry*(1-.48*smooth(.62,.995,seat))*(1-smooth(.09,.32,stance))
    *(1-smooth(.10,.82,depth))*(1-smooth(10,25,effort));
  const trim=reach*smooth(24,43,down);
  const rest=dry*(1-smooth(.72,1,plate))*(1-smooth(.10,.50,stance))
    *(1-smooth(14,33,look))*(1-smooth(70,86,turn));
  const sweep=smooth(5,25,effort), advance=reach*smooth(12,42,down), upright=1-smooth(0,23,down);
  const fit=(i,k,sx,sy,sz,dy,dz)=>k>0 ? [...data.pivots[i],0,k*dy,k*dz,...[sx,sy,sz].map(v=>1+k*(v-1))] : null;
  const collar=(r,shift=0,scale=1)=>tuck>0 ? [...data.pivots[0],0,-.58*tuck,shift-1.62*r*tuck*scale,
    1+tuck*(.965-1),1+tuck*(.41-1),(1-.12*r*tuck)*scale] : null;
  const crown=trim*(1+1.24*smooth(.76,.995,seat)+.46*smooth(78,87,down)*smooth(.79,.995,seat));
  const stroke=.68*smooth(23,43,down), outer=stroke*dry*space*(1-smooth(2.85,6,arm));
  const [start,soft,opening,end,d0,d1,lipY,lipZ,lift,advanceLip,rise,side]=data.turn;
  const lost=Math.max(0,release-smooth(44,57,start));
  const hold=lost*lost/(lost+soft)*(1-smooth(opening,end,turn))*smooth(30,45,down)*(1-smooth(64,78,down))
    *(1-smooth(d0,d1,depth))*leanRoom*steepRoom*sleeveRoom;
  const scale=(1-data.seatDepth*Math.max(seat,outer+stroke*dry*hold))/(1-data.seatDepth*Math.max(seat,outer));
  const shift=(1-scale)*(data.seatPlane-depth-data.pivots[0][2]);
  const settled=dry*smooth(.78,.99,plate);
  const compact=rest*(1-smooth(.54,.76,seat))*(1-smooth(.10,.26,stance));
  const wide=rest || settled ? fit(2,1,1-.60*rest,1-.59*rest,1-.14*advance*rest,
    rest*(.065+.37*sweep+.48*advance-.47*upright)+.07*settled,
    rest*(-.24*advance+.52*sweep+.22*upright)-.38*settled) : null;
  const fold=collar(crown+hold*smooth(24,43,down),shift,scale);
  let lip=fold;
  if (fold && hold>0) {
    const [x,y,z,dx,dy,dz,sx,sy,sz]=fold, thickness=1-.12*crown*tuck, raise=lift*hold;
    const drift=-Math.sign(signedTurn)*side*hold*smooth(48,57,down);
    lip=[x,y,z,dx+drift,dy+raise*(y+dy-lipY)+rise*hold,dz-(thickness-sz)*(lipZ-z)-advanceLip*hold,
      sx,sy*(1+raise),thickness];
  }
  return [outer,fold,lip,collar(trim*.16),fit(1,compact,.94,.92,1-.17*advance,.18*advance,-.24*advance),wide];
}

function wornPlate(f, index, elytra, slim) {
  const plate=(elytra ? f.wingPlates : f.plates)[index].slice();
  const inset=plate.pop();
  if (slim) plate[3]+=inset;
  return plate;
}

function fixedWearerPose(geo, profile, stance, elytra, slim) {
  const f=profile.mount;
  const fixed=geo.bones.some(b=>b.name===profile.bone) && geo.bones.some(b=>b.name===profile.gussetBone);
  const seated=fixed && !elytra;
  const a=profile.backing;
  const backing=elytra ? [a.tuckY,a.tuckY,a.wingZ] : f.backing;
  const bones=[];
  for (let piece of geo.bones) {
    const name=piece.name, half=a.names.indexOf(name);
    if (name==='chestplate') piece={...piece,rotation:[stance*profile.bodyAngle,0,0],offset:[0,-3.2*stance,0]};
    if (half>=0) piece={...piece,scale:[1,backing[half],backing[2]]};
    if (name==='v20_mount_shoulders' && (elytra || seated)) {
      piece={...piece,scale:elytra ? shoulderScales(0,0,0,true) : [1,f.SHOULDER_HEIGHT,f.SHOULDER_REACH]};
    }
    if (elytra && name==='v20_mount_under_yoke') piece={...piece,scale:yokeScales(0,0,0,true)};
    if (fixed && name==='v20_mount_saddle') piece={...piece,offset:[0,0,f.SADDLE_DEPTH],scale:[f.SADDLE_WIDTH,1,1]};
    if (seated) {
      if (name==='v17_cowl_return') piece={...piece,offset:[0,-f.RETURN_DROP,0]};
      else if (!name.startsWith('v17_cowl_tooth_') &&
          ['v17_cowl_','v19_cuellito_','v18_chain_'].some(p=>name.startsWith(p))) {
        const frame={name:'fixed_'+name,parent:piece.parent,pivot:[0,f.TRIM_Y,f.TRIM_Z],
          offset:[0,-f.TRIM_DROP,0],scale:[f.TRIM_WIDTH,f.TRIM_HEIGHT,1],cubes:[]};
        bones.push(frame);
        piece={...piece,parent:frame.name};
      }
    }
    const plate=profile.plates.names.indexOf(name);
    if (fixed && plate>=0 && piece.parent===profile.bone) {
      const [x,y,z,dx,dy,dz,pitch,yaw,roll,sx,sy,sz]=wornPlate(f,plate,elytra,slim);
      const frame={name:'shoulder_'+name,parent:'chestplate',pivot:[x,y,z],offset:[dx,dy,dz],
        rotation:[pitch,yaw,roll],scale:[sx,sy,sz],cubes:[]};
      bones.push(frame);
      piece={...piece,parent:frame.name};
    }
    bones.push(piece);
  }
  return {...geo,bones};
}

function wearerPose(geo, profile, stance, look, turn, elytra=false, arm=0, effort=arm, slim=false) {
  if (profile.mount) return fixedWearerPose(geo,profile,stance,elytra,slim);
  const depth=backset(profile,stance,look,turn);
  const anchor = profile.backing;
  const seat = profile.seat;
  const hasSeat = seat && geo.bones.some(b => b.name===seat.frame);
  const pressed = hasSeat ? seating(seat,stance,look,turn,arm,elytra) : 0;
  const backing = anchor && backingShape(anchor,profile.bodyAngle,stance,look,turn,depth,elytra);
  const plate = plateInfluence(profile.plates,stance,look,turn,effort,elytra);
  const [extra,collar,lip,facing,...pads] = torsoShape(hasSeat && profile.torso,stance,look,turn,depth,pressed,plate,arm,effort,1,elytra);
  const outer = Math.max(pressed,extra);
  const bones = geo.bones.map(b => {
    if (b.name===seat?.frame) return {...b,scale:[1,1,1-seat.depth*pressed]};
    const half = anchor?.names.indexOf(b.name) ?? -1;
    if (half>=0) return {...b,scale:[1,backing[half],backing[2]]};
    if (b.name===profile.bone) return {...b,offset:[0,0,depth]};
    if (b.name===profile.drapeBone) return {...b,rotation:[-depth*profile.drapePerUnit+(seat?.hem ?? 0)*outer,0,0]};
    if (b.name===profile.gussetBone) return {...b,scale:[1,1,1+depth/profile.gussetDepth]};
    if (b.name==='v20_mount_shoulders') {
      const scale = shoulderScales(stance,look,turn,elytra);
      scale[0] = 1-(seat?.width ?? 0)*pressed;
      return {...b,scale};
    }
    if (b.name==='v20_mount_under_yoke') return {...b,scale:yokeScales(stance,look,arm,elytra)};
    if (b.name==='chestplate') return {...b,rotation:[stance*profile.bodyAngle,0,0],offset:[0,-3.2*stance,0]};
    return b;
  });
  if (plate > 0) for (const [i,name] of profile.plates.names.entries()) {
    const index=bones.findIndex(b => b.name===name);
    if (index < 0) continue;
    const frame=plateFrame(bones[index],profile.plates.targets[i],plate);
    const piece={...bones[index],parent:frame.name};
    bones[index]=piece;
    bones.push(frame);
    if (piece.cubes?.length>profile.plates.rimCube) {
      bones.push(plateRim(piece,profile.plates,profile.plates.rims[i],plate));
      piece.cubes=piece.cubes.filter((_,j)=>j!==profile.plates.rimCube);
    }
  }
  for (let i=0,length=bones.length;i<length;i++) {
    const piece=bones[i], name=piece.name;
    const plateIndex=profile.plates?.names.indexOf(name) ?? -1;
    const transform=plateIndex>=0 ? pads[plateIndex] : name.startsWith('v17_cowl_back_') ? lip
      : name.startsWith('v17_cowl_tooth_') ? facing
      : name!=='v17_cowl_return' && ['v17_cowl_','v19_cuellito_','v18_chain_'].some(prefix=>name.startsWith(prefix)) ? collar : null;
    if (transform) {
      const [x,y,z,dx,dy,dz,sx,sy,sz]=transform;
      const frame={name:'torso_'+name,parent:piece.parent,pivot:[-x,y,z],offset:[-dx,dy,dz],scale:[sx,sy,sz],cubes:[]};
      bones[i]={...piece,parent:frame.name};
      bones.push(frame);
    }
    if (outer>pressed && (transform || plateIndex>=0 || name===profile.drapeBone ||
        (name!=='v17_cowl_return' && ['v17_cowl_','v19_cuellito_','v18_chain_'].some(prefix=>name.startsWith(prefix))))) {
      const child=(plate>0 && plateIndex>=0 ? bones.find(b=>b.name==='fit_'+name) : null) ||
        (transform ? bones.at(-1) : bones[i]);
      const frame={name:'seat_'+child.name,parent:child.parent,pivot:[0,0,seat.plane-depth],
        scale:[1,1,(1-seat.depth*outer)/(1-seat.depth*pressed)],cubes:[]};
      // Do not mutate a bone shared with the browser's input geometry.
      bones[bones.indexOf(child)]={...child,parent:frame.name};
      bones.push(frame);
    }
  }
  return {...geo,bones};
}

function strideLifts(s, top, mid, arm, leg, lean, depth, wingLift=0) {
  const knee = Math.max(0, Math.min(s.MID_TARGET_LIMIT, s.LEG_GAIN*leg-s.LEG_INSET-lean-s.LEG_FIT*depth));
  const want = Math.max(0, Math.min(s.TOP_LIMIT, Math.max(s.ARM_GAIN*arm-s.ARM_INSET-lean-s.ARM_FIT*depth, s.LEG_SHARE*knee)));
  const lift = gap => {
    if (gap<=0) return 0;
    const p=Math.min(1,gap/s.SOFT_EDGE);
    return gap*p*(2-p);
  };
  const a=Math.max(wingLift, want>0 ? lift(want-top) : 0);
  return [a, knee>0 ? lift(knee-top-a-mid) : 0];
}
function wingGoal(w, pitch, roll, lean, depth) {
  const clamp=(n,limit)=>Math.max(0,Math.min(n,limit));
  const cut=(w.CLEAR_SPAN-Math.abs(roll))/(w.CLEAR_SPAN-w.FOLDED);
  const target=w.PITCH_BIAS+w.PITCH_GAIN*clamp(pitch,45)-w.BODY_GAIN*clamp(lean,30)-w.DEPTH_GAIN*Math.max(0,depth);
  return smooth(0,1,cut)*clamp(target,w.GOAL_LIMIT);
}
function wingLift(w, top, wanted) {
  if (wanted<=0) return 0;
  const gap=Math.max(wanted-top,0);
  const t=Math.min(1,gap/w.SOFT_EDGE);
  return Math.min(w.LIFT_LIMIT,w.CARRY*gap*t*(2-t));
}
function clearancePose(geo, gait, stance, depth, wings) {
  const top=geo.bones.find(b=>b.name==='cape_top'), mid=geo.bones.find(b=>b.name==='cape_mid');
  // Same projection of the synthetic limb rotations as the live ModelParts.
  const back = deg => Math.asin(Math.max(0,Math.sin(deg*Math.PI/180)))*180/Math.PI;
  const arm=gait ? Math.max(...gait.arms.map(v=>back(v+stance*.4*180/Math.PI))) : 0;
  const leg=gait ? Math.max(...gait.legs.map(back)) : 0;
  const topAngle=top.rotation[0];
  const lift=wings>0 ? wingLift(WINGS,topAngle,wings) : 0;
  const [x,y]=strideLifts(STRIDE,topAngle,mid.rotation[0],arm,leg,FIT.bodyAngle*stance,depth,lift);
  return {...geo,bones:geo.bones.map(b => {
    const d=b===top ? x : b===mid ? y : 0;
    return d ? {...b,rotation:[b.rotation[0]+d,...b.rotation.slice(1)]} : b;
  })};
}
function strideGait(phase, amplitude) {
  const a=amplitude*Math.cos(2*Math.PI*phase)*180/Math.PI;
  return {arms:[a,-a],legs:[-1.4*a,1.4*a]};
}

function swayAngles(p, time, segment) {
  const half=p.DEMO_SECONDS/2, t=time%p.DEMO_SECONDS;
  const sign=t<half ? 1 : -1;
  const step=k=>sign*(1-(1+Math.tanh(k*half/2))*Math.exp(-k*(t%half)));
  const q=Math.pow(segment/p.LAST_SEGMENT,p.SEGMENT_POWER);
  const near=step(p.SIDE_NEAR_RATE), hem=step(p.SIDE_HEM_RATE);
  const pull=near+q*(hem-near);
  return [p.SIDE_YAW,p.SIDE_ROLL].map((gain,i)=>{
    const cap=i===0 ? p.MAX_YAW : p.MAX_ROLL;
    return q*Math.max(-cap,Math.min(cap,pull*gain));
  });
}
function swayPose(geo,p,time) {
  const angles=Array.from({length:p.LAST_SEGMENT+1},(_,segment)=>swayAngles(p,time,segment));
  return {...geo, bones:geo.bones.map(b=>{
    const segment=+(/^v17_ribbon_\d+_seg(\d+)$/.exec(b.name)?.[1]);
    if (!(segment>0 && segment<=p.LAST_SEGMENT)) return b;
    const [y,z]=angles[segment];
    const r=b.rotation;
    // Apply the same signed, local rotations as the baked rig in Forge.
    return {...b,rotation:[r[0],r[1]-y,r[2]+z]};
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

function playerFaces(stance=0, look=0, turn=0, gait=null) {
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
  const about=(pivot,rotation,offset)=>mul(T(pivot.map((v,i)=>v+offset[i])),mul(rotation,T(pivot.map(v=>-v))));
  const head=about([0,24,0],mul(R('y',turn),R('x',look)),[0,-4.2*stance,0]);
  const body=about([0,24,0],R('x',-(FIT?.bodyAngle || 0)*stance),[0,-3.2*stance,0]);
  const arms=[-5,5].map((x,i)=>about([x,22,0],R('x',-(gait?.arms[i]||0)-.4*(180/Math.PI)*stance),[0,-3.2*stance,0]));
  const legs=[-1.9,1.9].map((x,i)=>about([x,12,0],R('x',-(gait?.legs[i]||0)),[0,-.2*stance,4*stance]));
  const out = [];
  for (const [i,[x,y,z,w,h,d,color]] of parts.entries()) {
    const pose=i===0 ? head : i===1 ? body : i<4 ? arms[i-2] : legs[i-4];
    const legInset=gait && i>=4 ? (i===4 ? .1 : -.1) : 0;
    const V = CORNERS.map(k => apply(pose,[x + legInset + k[0]*w, y + k[1]*h, z + k[2]*d]));
    for (const fn in FACE_ORDER) {
      const idx = FACE_ORDER[fn];
      out.push({ pts: idx.map(i => V[i]), uvs: [[0,0],[0,0],[0,0],[0,0]], color });
    }
  }
  return out;
}

function wingHulls(profile, [pitch,yaw,roll,down]) {
  const [x,y,z]=profile.pivot;
  return [1,-1].map(sign=>{
    const rot=mul(R('z',-sign*roll),mul(R('y',sign*yaw),R('x',pitch)));
    return CORNERS.map(k=>{
      const local=profile.origin.map((v,i)=>v+k[i]*profile.size[i]);
      local[0]*=sign;
      const [a,b,c]=apply(rot,local);
      return [-sign*x-a,24-y-down-b,z+c];
    });
  });
}
function wingFaces(profile, pose) {
  return wingHulls(profile, pose).flatMap(V=>Object.entries(FACE_ORDER).map(([side,idx])=>({
    pts:idx.map(i=>V[i]), uvs:[[0,0],[0,0],[0,0],[0,0]],
    color:side==='north' || side==='south' ? [109,107,130] : [76,71,91],
  })));
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
function spillAt(map, coord, stride, dx, dy) {
  return (map[coord]*(1-dx)+map[coord+4]*dx)*(1-dy)
       + (map[coord+stride]*(1-dx)+map[coord+stride+4]*dx)*dy;
}
function smooth(lo, hi, x) {
  const t=Math.max(0, Math.min(1, (x-lo)/(hi-lo)));
  return t*t*(3-2*t);
}
function haloDusk(p, light) {
  return 1-smooth(p.DARK_LEVEL,p.LIGHT_LEVEL,light);
}
function haloGains(p, dusk, seconds, seed=0) {
  const phase=seconds/p.PERIOD+seed*p.SEED_SHIFT;
  const wave=t=>.5+.5*Math.cos(2*Math.PI*t);
  const edge=p.EDGE_BASE+p.EDGE_PULSE*wave(phase-p.EDGE_DELAY);
  const inner=p.INNER_BASE+p.INNER_PULSE*wave(phase);
  return [p.DAY_GAIN+dusk*(edge-p.DAY_GAIN), p.DAY_GAIN+dusk*(inner-p.DAY_GAIN), p.EDGE_LO, p.EDGE_HI];
}
function render(faces, yaw, pitch, zoom, size, bounds, tint, ambient=1, frame=null, overlay=null, bloom=false, gains=null, comparison=null) {
  const view = mul(R('x', pitch), R('y', yaw));
  lastView = view;
  const prepared = [];
  let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9;
  const include=([x,y])=>{
    x0=Math.min(x0,x); x1=Math.max(x1,x);
    y0=Math.min(y0,y); y1=Math.max(y1,y);
  };
  // Keep the neutral framing during each cycle, but include the displaced
  // cape and posed wearer if they extend past it. The reference stays locked.
  if (!frame && bounds) for (const p of bounds) include(apply(view,p));
  // Fit to the union, not just the currently selected A/B pose. Even if a
  // tip sticks out of the neutral bounds, toggling the effect can't reframe.
  if (!frame && comparison) for (const {pts} of comparison) for (const p of pts) include(apply(view,p));
  const LIGHT = [-0.35, 0.65, 0.68];
  const ln = Math.hypot(...LIGHT);
  for (let i=0;i<3;i++) LIGHT[i] /= ln;
  for (const f of faces) {
    const pv = f.pts.map(p => apply(view, p));
    if (!frame) for (const p of pv) include(p);
    const e1=[pv[1][0]-pv[0][0],pv[1][1]-pv[0][1],pv[1][2]-pv[0][2]];
    const e2=[pv[2][0]-pv[0][0],pv[2][1]-pv[0][1],pv[2][2]-pv[0][2]];
    const n=[e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2], e1[0]*e2[1]-e1[1]*e2[0]];
    const l=Math.hypot(...n);
    // Misma luz aproximada que el render de comparación registrado.
    const shade=l>1e-6 ? .40+.60*Math.abs((n[0]*LIGHT[0]+n[1]*LIGHT[1]+n[2]*LIGHT[2])/l) : .45;
    prepared.push({pv, uvs:f.uvs, shade, color:f.color || null});
  }
  const [cx,cy,scale] = frame || [(x0+x1)/2, (y0+y1)/2,
    Math.min((size-46)/(x1-x0||1), (size-46)/(y1-y0||1)) * zoom];
  lastScale = scale; lastCx = cx; lastCy = cy;

  const img = ctx.createImageData(size, size);
  const pix = img.data;
  const BG=[18,14,26];
  for (let i=0;i<size*size;i++) { pix[i*4]=BG[0]; pix[i*4+1]=BG[1]; pix[i*4+2]=BG[2]; pix[i*4+3]=255; }
  const depth = new Float32Array(size*size).fill(-1e9);
  const A = ATLAS, AW=ATLAS_W, AH=ATLAS_H;
  const H = bloom && tint ? HALO : null;
  const spillGain = H ? .45+.55*tint[0] : 0;

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
          const lit = q.shade * ambient;
          const emission = !solid && tint && GLOW[ti+3]>=26 ? GLOW[ti+3]/255 : 0;
          const diffuse = lit * (1-emission);
          let r=cr*diffuse + emission*GLOW[ti]  *(tint?.[0] || 0);
          let g=cg*diffuse + emission*GLOW[ti+1]*(tint?.[1] || 0);
          let bCol=cb*diffuse + emission*GLOW[ti+2]*(tint?.[2] || 0);
          if (H && !solid) {
            // The shader adds light without covering the diffuse. Linear
            // halo sampling is independent from the pixel-sharp core.
            const u=Math.max(0,Math.min(AW-1,uu-.5)), v=Math.max(0,Math.min(AH-1,vv-.5));
            const i=Math.min(AW-2,Math.floor(u)), j=Math.min(AH-2,Math.floor(v)), row=AW*4, h=j*row+i*4;
            if (H[h]||H[h+4]||H[h+row]||H[h+row+4]||H[h+2]||H[h+6]||H[h+row+2]||H[h+row+6]) {
              const red=spillAt(H,h,row,u-i,v-j);
              const envelope=gains ? gains[0]+(gains[1]-gains[0])*smooth(gains[2],gains[3],red/255) : 1;
              const gain=(1-emission)*spillGain*envelope;
              r += gain*tint[0]*red;
              g += gain*tint[1]*spillAt(H,h+1,row,u-i,v-j);
              bCol += gain*tint[2]*spillAt(H,h+2,row,u-i,v-j);
            }
          }
          pix[di]   = pix[di]*(1-al) + r*al;
          pix[di+1] = pix[di+1]*(1-al) + g*al;
          pix[di+2] = pix[di+2]*(1-al) + bCol*al;
          depth[idx]=zz;
        }
      }
    }
  }
  if (overlay) overlay(pix,depth);
  ctx.putImageData(img,0,0);
}

/* FX ilustrativos: los impulsos del servidor y la iluminación de
   Minecraft no corren en el navegador. Se usan los assets del mod. */
const TINT = {
  'animation.idle': [.72, .17, 0],
  'animation.moving': [.79, .21, 0],
  'animation.sprint': [.87, .13, .1],
  'animation.air': [.87, .12, .18],
  'animation.fall': [.74, .25, .04],
  'animation.sneak': [.55, .12, 0],
  'animation.swim': [.66, .27, .35],
  'animation.deterioro': [.63, .37, .28]
};
function simulatedTint(t, length) {
  const [base, amp, cool]=TINT[motionState];
  const wave=.5+.5*Math.cos(2*Math.PI*t/length);
  const w=motionState==='animation.deterioro' ? (0.62*wave**3+0.38*(1-wave)**3)/.62 : wave;
  const gain=base+amp*w;
  return [gain*(1-.27*cool), gain*(.67+.25*cool), gain*(.86+.33*cool)];
}
function sparkOrigin(state,pulse,index,grounded,noise) {
  const sneak=state==='animation.sneak';
  const collar=grounded && ((state==='animation.idle'||state==='animation.deterioro') ? index===1 :
    state==='animation.moving' ? pulse%3===0 : sneak && (pulse&3)===0);
  const beat=sneak ? pulse>>>1 : pulse;
  const side=(beat+(index===0?0:1))&1;
  const band=collar ? 0 : grounded && (index===1 || (beat&3)===3) ? 1 : ((beat+index)&2)===0 ? 2 : 3;
  const point=AURA.origins[band][side].map((value,i)=>value+AURA.spread[band][i]*(2*noise[i]-1));
  return {point,collar};
}

function overEmber(pix,depth,size,sprite,x,y,z,width,opacity,tint) {
  const x0=x-width/2,y0=y-width/2,s=16/width;
  for (let yy=Math.max(0,Math.ceil(y0)); yy<Math.min(size,y0+width); yy++) {
    const row=Math.min(15,Math.floor((yy-y0)*s));
    for (let xx=Math.max(0,Math.ceil(x0)); xx<Math.min(size,x0+width); xx++) {
      const dst=yy*size+xx;
      if (z<=depth[dst]) continue; // native particles also test depth against the body/cloth
      const ti=(row*16+Math.min(15,Math.floor((xx-x0)*s)))*4;
      const a=opacity*sprite[ti+3]/255;
      if (a<.1) continue; // vanilla particle shader's alpha test
      for (let j=0;j<3;j++) pix[dst*4+j]=pix[dst*4+j]*(1-a)+sprite[ti+j]*tint[j]*a;
    }
  }
}

// Same look curve as CapeEmber.java; the positions below are illustrative.
function emberLook(progress, streak, phase) {
  const p=Math.max(0,Math.min(1,progress));
  const ease=(lo,hi)=>{
    const t=Math.max(0,Math.min(1,(p-lo)/(hi-lo)));
    return t*t*(3-2*t);
  };
  const glint=.5+.5*Math.sin(phase+p*7.5);
  const fade=ease(0,.16)*(1-ease(.36,1));
  const cool=ease(.22,.93);
  return {frame:p<.25 ? 0 : p<.63 ? 1 : 2,
          alpha:(.79+.06*glint+.07*streak)*fade, scale:1-.43*p+.05*glint,
          tint:[1-.39*cool,.98-.18*cool,.93+.07*cool]};
}

function drawRuntimeParticles(seconds, size, stance, pix, depth) {
  const [count, outward, trail, rise]=AURA.modes[motionState];
  const sneak=motionState==='animation.sneak';
  const grounded=!['animation.air','animation.fall','animation.swim'].includes(motionState);
  const stride=(sneak ? 2 : 1)*AURA.pulseTicks/20, embers=[];
  const shotNow=Math.floor(seconds/stride);
  const random=(n,i,k)=>.5+.5*Math.sin(n*61.7+i*2.92+k*61.36);
  const first=Math.max(0,Math.ceil((seconds-47/20)/stride));
  for (let shot=first; shot<=shotNow; shot++) {
    const age=seconds-shot*stride;
    for (let i=0;i<count;i++) {
      const noise=[0,1,2].map(k=>random(shot,i,k));
      const {point,collar}=sparkOrigin(motionState,sneak ? shot*2 : shot,i,grounded,noise);
      const [x0,y0,z0]=point;
      const dx=Math.sign(x0)*outward*(.75+.35*noise[0]);
      const dz=collar ? .005 : trail*(.75+.35*noise[2]);
      const streak=Math.min(1,Math.hypot(dx,dz)/.035);
      const life=39-Math.round(13*streak)+Math.floor(random(shot,i,3)*9);
      const tick=age*20;
      if (tick<=0 || tick>=life) continue;
      const look=emberLook(Math.floor(tick)/life,streak,noise[1]*3.14);
      if (look.alpha<.1) continue;
      const fly=(1-Math.pow(.94,tick))/(1-.94);
      const clamp=Math.min(1,.04/Math.max(1e-9,Math.hypot(dx,dz)));
      const pos=apply(lastView,[16*(x0+fly*dx*clamp),16*(y0*(stance ? 1.5/1.8 : 1)+fly*rise),16*(z0+fly*dz*clamp)]);
      const x=size/2+(pos[0]-lastCx)*lastScale,y=size/2-(pos[1]-lastCy)*lastScale;
      const quad=(.1+.1*noise[0])*(.28+.10*streak+.15*noise[2]);
      const width=32*quad*look.scale*lastScale;
      embers.push({x,y,z:pos[2],width,...look});
    }
  }
  for (const e of embers.sort((a,b)=>a.z-b.z))
    overEmber(pix,depth,size,SPARKS[e.frame],e.x,e.y,e.z,e.width,e.alpha,e.tint);
}

let yaw=25, pitch=10, zoom=1.0, playing=true, t=0, elapsed=0;
let lastFrame=null, dirty=true, hidden=null, frameBounds=null, gaitBounds=null;
let showPlayer=true, showFx=false, referenceView=false;
const stanceControl=document.getElementById('fitStance'), lookControl=document.getElementById('fitLook');
const turnControl=document.getElementById('fitTurn'), fitValue=document.getElementById('fitValue');
const stridePlayer=document.getElementById('stridePlayer'), strideFit=document.getElementById('strideFit');
const strideAmount=document.getElementById('strideAmount');
const swayDemo=document.getElementById('swayDemo'), swayFit=document.getElementById('swayFit');
const swayValue=document.getElementById('swayValue'), swayMoment=document.getElementById('swayMoment');
const stateControl=document.getElementById('state');
const wingMode=document.getElementById('wingMode'), wingFit=document.getElementById('wingFit');
const fitReset=document.getElementById('fitReset'), fxControl=document.getElementById('l_particles');
const glowControl=document.getElementById('l_glow'), haloControl=document.getElementById('l_halo');
const seek=document.getElementById('seek'), play=document.getElementById('play');
const ambientControl=document.getElementById('ambient');
const lightPresets=[['lightCave',.18],['lightTorch',.88],['lightDay',1]]
    .map(([id,value])=>[document.getElementById(id),value]);
const zoomControl=document.getElementById('zoom');
const compareControl=document.getElementById('referenceCompare');
const wipe=document.getElementById('wipe');
function referenceScale(size) {
  return size / Math.max(...REF.cropSize);
}
function referenceFrame(size) {
  return [...REF.center, REF.pixelsPerUnit*referenceScale(size)];
}
function drawOriginal(size) {
  const amount=+wipe.value/100;
  if (amount===0) return;
  const [w,h]=REF.cropSize.map(d=>d*referenceScale(size));
  const x=(size-w)/2, y=(size-h)/2;
  ctx.save();
  ctx.beginPath(); ctx.rect(x,y,amount*w,h); ctx.clip();
  ctx.imageSmoothingEnabled=false;
  ctx.drawImage(ORIGINAL,x,y,w,h);
  ctx.restore();
  if (amount<1) {
    ctx.fillStyle='#f4d0e4';
    ctx.fillRect(Math.floor(x+amount*w),y,1,h);
  }
}
function refreshStrideControls() {
  stridePlayer.disabled=referenceView;
  strideFit.disabled=strideAmount.disabled=referenceView || !stridePlayer.checked;
}
function refreshHaloControl() {
  haloControl.disabled=referenceView || !glowControl.checked;
}
function refreshSwayControls() {
  swayDemo.disabled=referenceView;
  swayFit.disabled=referenceView || !swayDemo.checked;
}
function refreshWingControls() {
  wingMode.disabled=referenceView;
  wingFit.disabled=referenceView || wingMode.value==='none';
}
function setReference(value) {
  referenceView=value;
  document.getElementById('v34').setAttribute('aria-pressed',String(value));
  compareControl.hidden=!value;
  for (const control of [stanceControl, lookControl, turnControl, fitReset, fxControl, glowControl, ambientControl, zoomControl])
    control.disabled=value;
  for (const [button] of lightPresets) button.disabled=value;
  refreshStrideControls(); refreshHaloControl(); refreshSwayControls(); refreshWingControls();
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
  // Keep both A/B passes at one scale, even when the legs swing out.
  for (const phase of [0,.5]) for (const {pts} of playerFaces(0,0,0,strideGait(phase,1)))
    for (const p of pts) for (let a=0;a<3;a++) { lo[a]=Math.min(lo[a],p[a]); hi[a]=Math.max(hi[a],p[a]); }
  gaitBounds=CORNERS.map(k=>k.map((v,i)=>v?hi[i]:lo[i]));
}
function draw(now) {
  requestAnimationFrame(draw);
  const clip=CLIPS[motionState];
  const demo=!referenceView && swayDemo.checked;
  const duration=demo ? SWAY.DEMO_SECONDS : clip.length;
  if (playing && lastFrame!==null) {
    const step=Math.min(.05,(now-lastFrame)/1000);
    t=(t+step)%duration; elapsed+=step; dirty=true;
  }
  lastFrame=now;
  if (!dirty) return;
  const stance=referenceView ? 0 : Number(stanceControl.checked);
  const look=referenceView ? 0 : +lookControl.value;
  const turn=referenceView ? 0 : +turnControl.value;
  // A synthetic stride has its own clock. Pausing freezes both it and the clip.
  const amplitude=+strideAmount.value;
  const gait=!referenceView && stridePlayer.checked ? strideGait(elapsed*(.8+.95*amplitude),amplitude) : null;
  const clipTime=demo ? elapsed%clip.length : t;
  const base=referenceView ? GEO : poseAt(GEO,clip,clipTime);
  const wingPose=referenceView ? null : WINGS[wingMode.value === 'folded' && stance ? 'crouched' : wingMode.value];
  const clearanceGait=strideFit.checked ? gait : null;
  const backArm=Math.max(...(gait?.arms || [0,0]).map(
    a=>Math.asin(Math.sin(a*Math.PI/180+stance*.4))*180/Math.PI));
  const armEffort=Math.max(backArm,...(gait?.arms || [0,0]).map(a=>Math.abs(a+stance*FIT.bodyAngle)));
  const depth=FIT.mount ? 0 : backset(FIT,stance,look,turn);
  const guide=wingPose ? wingGoal(WINGS,wingPose[0],wingPose[2],FIT.bodyAngle*stance,depth) : 0;
  const fit=(pose, goal)=>{
    if (clearanceGait || goal>0) pose=clearancePose(pose,clearanceGait,stance,depth,goal);
    return collect(referenceView ? pose : wearerPose(pose,FIT,stance,look,turn,!!wingPose,backArm,armEffort),hidden);
  };
  const drift=demo ? swayPose(base,SWAY,t) : null;
  const current=drift && swayFit.checked ? drift : base;
  const currentGuide=wingFit.checked ? guide : 0;
  const faces=fit(current,currentGuide);
  const comparison=[];
  for (const pose of drift ? [base,drift] : [base]) for (const goal of guide>0 ? [0,guide] : [0]) {
    if (pose!==current || goal!==currentGuide) comparison.push(...fit(pose,goal));
  }
  if (showPlayer) faces.push(...playerFaces(stance,look,turn,gait));
  if (wingPose) faces.push(...wingFaces(WINGS,wingPose));
  fitValue.textContent=referenceView ? 'Pose base · ajuste desactivado' :
    FIT.mount ? `Montaje fijo · Mirada ${look}° · giro ${turn}°` :
    `Mirada ${look}° · giro ${turn}° · holgura ${depth.toFixed(2)} u`;
  const fx=showFx&&!referenceView;
  const ambient=referenceView ? 1 : +ambientControl.value;
  const bloom=haloControl.checked&&!referenceView;
  // The slider stands in for local block/sky light. It snaps to the target
  // so a paused frame can be compared at identical pose and pulse phase.
  const gains=bloom ? haloGains(NOCTURNE,haloDusk(NOCTURNE,15*(ambient-.18)/.82),elapsed) : null;
  render(faces,yaw,pitch,zoom,SIZE,gait ? gaitBounds : frameBounds,
         glowControl.checked&&!referenceView ? simulatedTint(clipTime,clip.length) : null,
         ambient, referenceView ? referenceFrame(SIZE) : null,
         fx ? (pixels,z)=>drawRuntimeParticles(elapsed,SIZE,stance,pixels,z) : null,
         bloom, gains, comparison);
  if (referenceView) drawOriginal(SIZE);
  document.getElementById('faces').textContent=faces.length;
  document.getElementById('clock').textContent=referenceView?'Pose base':`${t.toFixed(2).replace('.',',')} s`;
  seek.value=Math.round(t/duration*1000);
  const direction=demo ? (t%duration>=duration/2 ? 'Vuelta' : 'Ida') : '';
  if (swayValue.textContent!==direction) swayValue.textContent=direction;
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
  const [geo,clips,fit,stride,sway,wings,atlas,glow,halo,aura,nocturne,reference,original,sparks]=await Promise.all([
    loadJson('armor.geo.json'), loadJson('armor.animation.json'), loadJson('fit.json'), loadJson('stride.json'),
    loadJson('sway.json'), loadJson('wings.json'), image('armor.png'),
    image('armor_glowmask.png'), image('armor_halo.png'), loadJson('aura.json'), loadJson('nocturne.json'),
    loadJson('reference-frame.json'), image('reference-crop.png'),
    Promise.all([0,1,2].map(i=>image(`capa_spark_${i}.png`)))]);
  if (original.width!==reference.cropSize[0] || original.height!==reference.cropSize[1])
    throw new Error('La imagen no coincide con el encuadre de referencia');
  REF=reference; ORIGINAL=original;
  GEO=geo['minecraft:geometry'][0]; CLIPS=prepareClips(clips); FIT=fit; STRIDE=stride; SWAY=sway; WINGS=wings;
  hidden=runtimeHidden(GEO);
  if ([glow,halo].some(im=>im.width!==atlas.width || im.height!==atlas.height))
    throw new Error('Los mapas de luz no coinciden con el atlas opaco');
  ATLAS=pixels(atlas); GLOW=pixels(glow); HALO=pixels(halo); AURA=aura; NOCTURNE=nocturne;
  refreshHaloControl(); refreshWingControls();
  SPARKS=sparks.map(pixels); ATLAS_W=atlas.width; ATLAS_H=atlas.height;
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
  if (referenceView) setReference(false);
  yaw+=.46*(e.clientX-drag[0]); pitch=Math.max(-76,Math.min(76,pitch+.46*(e.clientY-drag[1])));
  drag=[e.clientX,e.clientY]; dirty=true;
});
for (const type of ['pointerup','pointercancel','lostpointercapture']) canvas.addEventListener(type,()=>drag=null);
for (const [id,y,p] of [['vBack',0,9],['vFront',180,8],['vSide',-87,8],['vTop',0,78]]) {
  document.getElementById(id).onclick=()=>{setReference(false); yaw=y; pitch=p;};
}
document.getElementById('v34').onclick=()=>{
  if (referenceView) { setReference(false); return; }
  if (!REF) return;
  yaw=REF.yaw; pitch=REF.pitch; zoom=1; t=elapsed=0;
  zoomControl.value=zoom;
  setPlaying(false); setReference(true);
};
play.onclick=()=>setPlaying(!playing);
seek.oninput=e=>{
  if (!CLIPS) return;
  setPlaying(false); setReference(false);
  t=(swayDemo.checked ? SWAY.DEMO_SECONDS : CLIPS[motionState].length)*(+e.target.value)/1000;
  elapsed=t; dirty=true;
};
function setMotion(state) {
  stateControl.value=motionState=state;
  stanceControl.checked=state==='animation.sneak';
  t=elapsed=0;
  setReference(false);
}
swayDemo.onchange=()=>{
  if (swayDemo.checked) setMotion('animation.moving');
  else t=elapsed=0;
  refreshSwayControls(); dirty=true;
};
swayMoment.onclick=()=>{
  if (!SWAY) return;
  swayDemo.checked=swayFit.checked=true;
  setMotion('animation.moving');
  setPlaying(false);
  t=elapsed=SWAY.DEMO_SECONDS/2+.10;
  yaw=0; pitch=9;
};
swayFit.onchange=wingFit.onchange=()=>{ dirty=true; };
wingMode.onchange=()=>{ refreshWingControls(); dirty=true; };
stateControl.onchange=e=>{
  swayDemo.checked=false;
  setMotion(e.target.value);
};
for (const control of [stanceControl,lookControl,turnControl]) {
  control.oninput=()=>{ if (!referenceView) dirty=true; };
}
stridePlayer.onchange=()=>{ refreshStrideControls(); dirty=true; };
strideFit.onchange=strideAmount.oninput=()=>{ dirty=true; };
fitReset.onclick=()=>{
  stanceControl.checked=false; lookControl.value=turnControl.value=0; dirty=true;
};
zoomControl.oninput=e=>{ zoom=+e.target.value; dirty=true; };
document.getElementById('l_player').onchange=e=>{ showPlayer=e.target.checked; dirty=true; };
fxControl.onchange=e=>{ showFx=e.target.checked; dirty=true; };
glowControl.onchange=()=>{ refreshHaloControl(); dirty=true; };
haloControl.onchange=wipe.oninput=()=>{ dirty=true; };
ambientControl.oninput=()=>{
  for (const [button,value] of lightPresets)
    button.setAttribute('aria-pressed',String(+ambientControl.value===value));
  dirty=true;
};
for (const [button,value] of lightPresets) button.onclick=()=>{
  ambientControl.value=value;
  ambientControl.oninput();
};

boot().catch(error=>{ document.getElementById('loading').textContent=error.message; });
