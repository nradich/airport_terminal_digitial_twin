import {build} from 'esbuild';
import {mkdir,copyFile} from 'node:fs/promises';
await mkdir('../static',{recursive:true});
await build({entryPoints:['src/main.ts'],bundle:true,format:'esm',outfile:'../static/viewer.js',minify:true});
await copyFile('index.html','../static/index.html');
