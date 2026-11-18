// Verify the actual app.js path for the new sparks, not a separate mock.
// stdin: layout exported from CapeState.java. argv: optional runtime Java TSV.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const aura = JSON.parse(fs.readFileSync(0, 'utf8'));
const samples = process.argv[2] ? fs.readFileSync(process.argv[2], 'utf8').trim().split('\n') : [];
const target = () => ({ getContext: () => ({}), addEventListener() {} });
const context = vm.createContext({ document: { getElementById: target }, aura, samples, assert });
const source = fs.readFileSync(path.join(__dirname, '../preview/app.js'), 'utf8').split('\nboot().catch')[0];
vm.runInContext(`${source}
{
  AURA=aura;
  for (const line of samples) {
    const [state,p,i,ground,a,b,c,x,y,z,high]=line.trim().split('\\t');
    const result=sparkOrigin(state,+p,+i,ground==='true',[+a,+b,+c]);
    const expected=[+x,+y,+z];
    assert(result.point.every((v,i)=>Math.abs(v-expected[i])<2e-15),line);
    assert.equal(result.collar,high==='true',line);
  }
  // One half of the billboard is behind the wearer and one half is visible.
  const side=24, image=new Uint8ClampedArray(side*side*4).fill(32);
  const depth=new Float32Array(side*side).fill(-Infinity);
  const sprite=new Uint8Array(16*16*4).fill(255);
  for(let y=0;y<side;y++) for(let x=0;x<12;x++) depth[y*side+x]=2;
  overEmber(image,depth,side,sprite,12,12,1,16,.5,[1,.5,.8]);
  assert.equal(image[(12*side+8)*4],32,'la chispa atravesó al portador');
  assert.equal(image[(12*side+15)*4],144,'cobertura visible incorrecta');
  assert.equal(image[(12*side+15)*4+3],32,'la chispa escribió alfa');
  assert.equal(depth[12*side+15],-Infinity,'una chispa translúcida escribió profundidad');
  overEmber(image,depth,side,sprite,12,12,3,16,.5,[1,.5,.8]);
  assert.equal(image[(12*side+8)*4],144,'la chispa delante desapareció');
}
`, context, { filename: 'preview/app.js' });
console.log(`Chispas visor: prueba de profundidad y ${samples.length} posiciones contrastadas con Java`);
