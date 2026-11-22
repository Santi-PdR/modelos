// Verify the actual app.js path for the new sparks, not a separate mock.
// stdin: layout exported from CapeState.java. argv: optional runtime Java TSV.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const aura = JSON.parse(fs.readFileSync(0, 'utf8'));
const rows = file => file ? fs.readFileSync(file, 'utf8').trim().split('\n') : [];
const samples = rows(process.argv[2]), looks = rows(process.argv[3]), blends = rows(process.argv[4]);
const crouch = rows(process.argv[5]), banks = rows(process.argv[6]);
const target = () => ({ getContext: () => ({}), addEventListener() {} });
const context = vm.createContext({ document: { getElementById: target }, aura, samples, looks, blends, crouch, banks, assert });
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
  for (const line of looks) {
    const [p,streak,phase,...expected] = line.trim().split('\\t').map(Number);
    const look=emberLook(p,streak,phase);
    [look.frame,look.alpha,look.scale,...look.tint].forEach((v,i)=>{
      assert(Math.abs(v-expected[i])<2e-15,line);
    });
  }
  for (const line of blends) {
    const [,,,life,p,,index] = line.trim().split('\\t').map(Number);
    assert.equal(emberSpriteIndex(p,life,AURA.ember),index,line);
  }
  for (const line of crouch) {
    const [side,height,back,...expected] = line.trim().split('\\t').map(Number);
    const [x,y,z]=crouchSparkPoint([side,height,back],AURA.crouch);
    const {scale,renderDrop}=AURA.crouch;
    const feet=(Math.fround(1.501)-1.5)*scale-renderDrop;
    const actual=[-x*scale,y*scale+feet,z*scale]; // yaw 180°, same axes as the GEO
    assert(actual.every((v,i)=>Math.abs(v-expected[i])<2e-15),line);
  }
  for (const line of banks) {
    const [p,drift,expected]=line.trim().split('\\t').map(Number);
    assert(Math.abs(emberBank(p,drift,AURA.bank)-expected)<2e-15,line);
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
  overEmber(image,depth,side,sprite,12,12,3,16,.08,[1,.5,.8]);
  assert.equal(image[(12*side+8)*4],144,'no se respetó el corte de alfa vanilla al apagarse');
  if (banks.length) {
    // A vertical marker in texture space should lean toward positive screen
    // X at the top, but remain occluded where it crosses behind the sleeve.
    const marker=new Uint8Array(16*16*4);
    for(let y=2;y<14;y++) for(let x=7;x<=8;x++) marker.fill(255,(y*16+x)*4,(y*16+x+1)*4);
    const tilted=new Uint8ClampedArray(image.length).fill(32);
    overEmber(tilted,depth,side,marker,12,12,1,16,1,[1,1,1],emberBank(.2,.04,AURA.bank));
    assert.equal(tilted[(7*side+14)*4],255,'el extremo alto de la brasa no acompaña el avance');
    assert.equal(tilted[(7*side+16)*4],32,'la inclinación cambió el ancho de la brasa');
    assert.equal(tilted[(17*side+10)*4],32,'la brasa inclinada traspasó la oclusión');
  }
}
`, context, { filename: 'preview/app.js' });
console.log(`Chispas visor: ${samples.length} orígenes, ${looks.length} apariencias, ${blends.length} índices, ${crouch.length} nacimientos agachados y ${banks.length} inclinaciones contrastadas con Java; profundidad y corte alfa intactos.`);
