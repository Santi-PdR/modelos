// Test del app.js que se incluye en el HTML, sin emular el rasterizador.
// Recibe GEO, clips y tiempos por stdin; devuelve transformaciones por hueso.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const indata = JSON.parse(fs.readFileSync(0, 'utf8'));
const target = () => ({getContext:()=>({}), addEventListener(){}});
const context = vm.createContext({ document:{getElementById:target}, indata });
const src = fs.readFileSync(path.join(__dirname, '../preview/app.js'), 'utf8').split('\nboot().catch')[0];
const matrices = vm.runInContext(`${src}
  (() => {
    if (indata.wingSamples) {
      const { wings, stride, wingSamples, wingPoses }=indata;
      return {
        angles:wingSamples.map(([pitch,roll,lean,depth,arm,leg,top,mid])=>{
          const goal=wingGoal(wings,pitch,roll,lean,depth);
          return [goal,...strideLifts(stride,top,mid,arm,leg,lean,depth,wingLift(wings,top,goal))];
        }),
        hulls:wingPoses.map(angles=>wingHulls(wings,angles))
      };
    }
    if (indata.swayTimes) {
      const rig={bones:[{name:'v20_mount_seat',rotation:[3,1,1]},
                        ...Array.from({length:6},(_,i)=>({name:'v17_ribbon_0_seg'+i,rotation:[4,2,3]}))]};
      return indata.swayTimes.map(t=>{
        const posed=swayPose(rig,indata.sway,t).bones;
        if ([0,1,6].some(i=>posed[i]!==rig.bones[i])) throw Error('arrastre fuera de los tramos libres');
        return posed.slice(2,6).flatMap(b=>{
          if (b.rotation[0]!==4) throw Error('el arrastre sobreescribió el eje X');
          return [2-b.rotation[1],b.rotation[2]-3];
        });
      });
    }
    if (indata.strideSamples) {
      return indata.strideSamples.map(([top,mid,arm,leg,stance,depth]) =>
        strideLifts(indata.stride,top,mid,arm,leg,stance*indata.fit.bodyAngle,depth));
    }
    if (indata.mountPlateSamples) {
      return indata.mountPlateSamples.map(([w,slim,i])=>wornPlate(indata.fit.mount,i,!!w,!!slim));
    }
    if (indata.mountLiningSamples) {
      const {geo,fit,parts}=indata;
      const source=parts.map(n=>geo.bones.find(b=>b.name===n).cubes);
      return indata.mountLiningSamples.map(wings=>{
        const posed=fixedWearerPose(geo,fit,0,!!wings,true);
        return parts.flatMap((n,i)=>source[i].map(c=>+posed.bones.find(b=>b.name===n).cubes.includes(c)));
      });
    }
    if (indata.hoodSamples) {
      const {geo,fit,parts}=indata;
      return indata.hoodSamples.map(([stance,wings,...inputs]) => {
        const pose=hoodPose(fit.hood,...inputs);
        const m=matrices(wearerPose(geo,fit,stance,0,0,!!wings,0,0,true,pose));
        return [...pose,...parts.flatMap(n=>m[n])];
      });
    }
    if (indata.lookClearanceSamples) {
      return indata.lookClearanceSamples.map(args=>hoodAim(indata.fit.hood,...args));
    }
    if (indata.rearTuckSamples) {
      return indata.rearTuckSamples.map(args=>rearTuck(indata.fit.hood,...args));
    }
    if (indata.napeSamples) {
      return indata.napeSamples.map(args=>napeShifts(indata.fit.hood,...args));
    }
    if (indata.sprintEdgeSamples) {
      return indata.sprintEdgeSamples.map(([r,s])=>sprintEdgeOffset(indata.fit.sprintEdge,'v17_ribbon_'+r+'_seg'+s,'cape_top') || [0,0,0]);
    }
    if (indata.clearanceMatrices) {
      return indata.clearanceMatrices.map(([geo,stance,look,turn,wings,slim,amount])=>{
        const m=matrices(wearerPose(geo,indata.fit,stance,look,turn,wings,0,0,slim,undefined,amount));
        return indata.parts.map(n=>m[n]);
      });
    }
    if (indata.torsoMatrices) {
      return indata.torsoMatrices.map(aim => {
        const model=matrices(wearerPose(indata.geo,indata.fit,...aim));
        return indata.parts.map(n=>model[n] || model[n.replace(/^rim_/,'')]);
      });
    }
    if (indata.torsoSamples) {
      const f=indata.fit;
      return indata.torsoSamples.map(([s,p,y,a,e,d,w]) => {
        const shape=torsoShape(f.torso,s,p,y,backset(f,s,p,y),seating(f.seat,s,p,y,a,!!w)*d,
          plateInfluence(f.plates,s,p,y,e,!!w)*d,a,e,d,!!w);
        return [shape[0], ...shape.slice(1).flatMap(v=>v || [0,0,0,0,0,0,1,1,1])];
      });
    }
    if (indata.plateSamples) {
      const f=indata.fit, names=f.plates.names;
      const rig={bones:[...names.map(name=>({name,cubes:[{},{}]})),{name:'cape_top'}]};
      return indata.plateSamples.map(([s,p,y,w,arm])=>{
        const model=matrices(wearerPose(rig,f,s,p,y,!!w,0,arm));
        if (model.cape_top.some((v,i)=>v!==ident()[i])) throw Error('ajuste de placas fuera de la montura');
        return [plateInfluence(f.plates,s,p,y,arm,!!w), ...names.map(name=>model[name]),
          ...names.map(name=>model['rim_'+name] || model[name])];
      });
    }
    if (indata.seatSamples) {
      const f={...indata.fit,torso:null};
      const rig={bones:[{name:f.seat.frame},{name:'v20_mount_shoulders'},{name:f.drapeBone}]};
      return indata.seatSamples.map(([s,p,y,w,arm])=>{
        const [frame,returns,drape]=wearerPose(rig,f,s,p,y,!!w,arm).bones;
        return [seating(f.seat,s,p,y,arm,!!w),frame.scale[2],returns.scale[0],-drape.rotation[0]];
      });
    }
    if (indata.backingSamples) {
      const f=indata.fit;
      return indata.backingSamples.map(([s,p,y,w]) => backingShape(f.backing,f.bodyAngle,s,p,y,backset(f,s,p,y),!!w));
    }
    if (indata.shoulderSamples) {
      return indata.shoulderSamples.map(([stance,look,yaw,wings,arm]) => [
        ...shoulderScales(stance,look,yaw,!!wings).slice(1), ...yokeScales(stance,look,arm,!!wings)]);
    }
    if (indata.fitSamples) {
      const {fit}=indata;
      const rig={bones:[{name:fit.bone},{name:fit.drapeBone},{name:fit.gussetBone}]};
      return indata.fitSamples.map(aim => {
        const [move,drape,gusset]=wearerPose(rig,fit,...aim).bones;
        return [move.offset[2],gusset.scale[2],-drape.rotation[0]];
      });
    }
    const clips=prepareClips(indata.clips), geo=indata.geo;
    return {hidden:[...runtimeHidden(geo)], poses:indata.tests.map(({clip,t,aim}) => {
      const base=poseAt(geo,clips[clip],t);
      const posed=aim ? wearerPose(base,indata.fit,...aim) : base;
      return { byName: matrices(posed), sampleFaces: collect(posed, runtimeHidden(geo)).filter((_,i)=>i%37===0) };
    })};
  })();`, context, { filename:'preview/app.js' });
process.stdout.write(JSON.stringify(matrices));
