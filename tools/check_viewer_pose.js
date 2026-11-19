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
    if (indata.shoulderSamples) {
      return indata.shoulderSamples.map(([stance,look,yaw,wings]) => shoulderScales(stance,look,yaw,!!wings).slice(1));
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
