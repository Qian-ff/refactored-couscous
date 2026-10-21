'use strict';
// Export the exact approved path data; does not execute the prototype or import the app.
const fs=require('node:fs'),path=require('node:path');
const root=__dirname,source=fs.readFileSync(path.join(root,'prototype.js'),'utf8');
const block=source.match(/const PATHS=\{([\s\S]*?)\n\};/);
if(!block)throw Error('Approved icon registry not found.');
const paths=Array.from(block[1].matchAll(/([a-z][a-z0-9]*):'([^']+)'/g),m=>[m[1],m[2]]);
if(paths.length<20||new Set(paths.map(x=>x[0])).size!==paths.length)throw Error('Incomplete icon registry.');
for(const [name,data] of paths)if(!/^[MmLlHhVvCcSsQqTtAaZz0-9.,\s+\-]+$/.test(data))throw Error(`Unexpected path data: ${name}`);
const svg='<svg xmlns="http://www.w3.org/2000/svg">\n'+paths.map(([name,data])=>`  <symbol id="assistant-${name}" viewBox="0 0 24 24"><path d="${data}" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></symbol>`).join('\n')+'\n</svg>\n';
fs.mkdirSync(path.join(root,'assets'),{recursive:true});fs.writeFileSync(path.join(root,'assets','icons.svg'),svg);console.log(`Exported ${paths.length} approved icons.`);
