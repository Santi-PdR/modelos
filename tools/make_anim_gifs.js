// renderiza los 18 frames del GIF de animacion
// Uso:  node tools/make_anim_gifs.js   (desde la raiz del repo, con preview/assets/ al dia)
// Escribe los .raw en /tmp y deja el render del visor como PNG.
'use strict';
const fs=require('fs'), vm=require('vm');
const ROOT=__dirname + '/../preview/assets/';
const fakeCtx={createImageData:(w,h)=>({width:w,height:h,data:new Uint8ClampedArray(w*h*4)}),
 putImageData:(img)=>{global.__IMG=img;}, clearRect(){},fillRect(){},drawImage(){},
 getImageData:()=>({data:new Uint8ClampedArray(fs.readFileSync(ROOT+'atlas.raw'))}),
 set fillStyle(v){},get fillStyle(){return '';}};
const el=()=>({getContext:()=>fakeCtx,addEventListener(){},setPointerCapture(){},style:{},width:480,height:480,textContent:'',onclick:null,onchange:null,oninput:null,value:'0.35',checked:true});
const document={getElementById:el,createElement:el};
const sandbox={document,console,Math,Uint8ClampedArray,Float32Array,Array,Object,Set,Number,String,parseInt,parseFloat,
 performance:{now:()=>0},requestAnimationFrame:()=>{},fetch:async()=>({json:async()=>({}),text:async()=>''}),Image:function(){this.width=128;this.height=128;}};
sandbox.globalThis=sandbox; sandbox.getImg=()=>global.__IMG;
vm.createContext(sandbox);
let src=fs.readFileSync(__dirname + '/../preview/app.js','utf8').replace(/boot\(\)\.catch\([\s\S]*?\);\s*$/,'');
src+=`\nglobalThis.__api={init(g,a,w,h){GEO=g;ATLAS=a;ATLAS_W=w;ATLAS_H=h;hidden=runtimeHidden(g);SIZE=380;}, state(v){motionState=v;},
 frame(t,s,yaw,pitch,player){const g=animate(GEO,t,s);const f=collect(g,hidden,{cloth:true,collar:true,shreds:true,particles:true,energy:true});
 if(player)f.push(...playerFaces());render(f,yaw,pitch,1.0,380);return f.length;},img(){return getImg();}};`;
vm.runInContext(src,sandbox,{filename:'app.js'});
const geo=JSON.parse(fs.readFileSync(ROOT+'armor.geo.json','utf8'))['minecraft:geometry'][0];
sandbox.__api.init(geo,new Uint8ClampedArray(fs.readFileSync(ROOT+'atlas.raw')),128,128);
for(let i=0;i<18;i++){
  const t=i*0.30;
  sandbox.__api.frame(t,0.80,14,12,false);
  fs.writeFileSync('/tmp/gifframe_'+String(i).padStart(2,'0')+'.raw',Buffer.from(sandbox.__api.img().data));
}
console.log('18 frames renderizados');
