import {build} from 'esbuild';
import {createHash} from 'node:crypto';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
await mkdir('../static',{recursive:true});
await build({entryPoints:['src/main.ts'],bundle:true,format:'esm',outfile:'../static/viewer.js',minify:true});
const revision=createHash('sha256').update(await readFile('../static/viewer.js')).digest('hex').slice(0,16);
await writeFile('../static/index.html',(await readFile('index.html','utf8')).replace('./viewer.js',`./viewer.js?v=${revision}`));
