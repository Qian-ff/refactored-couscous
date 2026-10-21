'use strict';
// Export our own vector code into ready-to-copy files; never imports production code.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=__dirname;
const context=vm.createContext({module:{exports:{}}});
vm.runInContext(fs.readFileSync(path.join(root,'prototype.js'),'utf8'),context,{filename:'approved-static-prototype.js'});
const artDir=path.join(root,'assets','illustrations');fs.mkdirSync(artDir,{recursive:true});
for(const [file,kind]of [['lab-bench','bench'],['chemistry','chem'],['electrical','electric'],['personal-protection','ppe']]){
  let svg=context.labArt(kind).replace('<svg ','<svg xmlns="http://www.w3.org/2000/svg" ');
  svg=svg.replace(' aria-hidden="true"','');fs.writeFileSync(path.join(artDir,file+'.svg'),svg+'\n');
}
const paths=vm.runInContext('paths',context);
const symbols=Object.entries(paths).map(([name,d])=>`<symbol id="lc-${name}" viewBox="0 0 24 24"><path d="${d}" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round"/></symbol>`).join('\n');
fs.writeFileSync(path.join(root,'assets','icons.svg'),`<svg xmlns="http://www.w3.org/2000/svg">\n${symbols}\n</svg>\n`);
console.log('Exported 4 original illustrations and icon symbols from the approved desktop source.');
