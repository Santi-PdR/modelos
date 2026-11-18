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
    const clips=prepareClips(indata.clips), geo=indata.geo;
    return {hidden:[...runtimeHidden(geo)], poses:indata.tests.map(({clip,t,aim}) => {
      const base=poseAt(geo,clips[clip],t);
      const posed=aim ? wearerPose(base,indata.fit,...aim) : base;
      return { byName: matrices(posed), sampleFaces: collect(posed, runtimeHidden(geo)).filter((_,i)=>i%37===0) };
    })};
  })();`, context, { filename:'preview/app.js' });
process.stdout.write(JSON.stringify(matrices));
