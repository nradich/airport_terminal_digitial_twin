import {build} from 'esbuild';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
await mkdir('../static',{recursive:true});
await build({entryPoints:['src/main.ts'],bundle:true,format:'esm',outfile:'../static/viewer.js',minify:true});
await writeFile('../static/index.html',await readFile('index.html'));
