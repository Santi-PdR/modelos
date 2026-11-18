// Exercise the actual viewer rasterizer in Node, without a DOM or GPU.
// Input: generated geometry, raw RGBA atlases, and a few fixed views on stdin.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
let frame;
const context2d = {
  createImageData: (w, h) => ({ data: new Uint8ClampedArray(w*h*4) }),
  putImageData: image => { frame = image.data; },
};
const target = () => ({ getContext: () => context2d, addEventListener() {} });
const context = vm.createContext({ document: { getElementById: target }, input,
  bytes: b64 => Buffer.from(b64, 'base64'), rendered: () => Buffer.from(frame).toString('base64') });
const source = fs.readFileSync(path.join(__dirname, '../preview/app.js'), 'utf8').split('\nboot().catch')[0];
const result = vm.runInContext(`${source}
  REF=input.reference;
  ATLAS_W=ATLAS_H=input.atlasSize;
  ATLAS=bytes(input.albedo);
  GLOW=bytes(input.emission);
  const mesh=collect(input.geo, runtimeHidden(input.geo));
  input.tests.map(({yaw, pitch, ambient, tint}) => {
    const frame=referenceFrame(input.size);
    render(mesh, yaw, pitch, 1, input.size, null, tint, ambient, frame);
    return { frame, rgba: rendered() };
  });`, context, { filename: 'preview/app.js' });
process.stdout.write(JSON.stringify(result));
