import {readFileSync} from 'node:fs';
import validator from 'gltf-validator';
const report=await validator.validateBytes(new Uint8Array(readFileSync(process.argv[2])));
console.info(JSON.stringify(report.issues,null,2));
if(report.issues.numErrors)process.exit(1);
