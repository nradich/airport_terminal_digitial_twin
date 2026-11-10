import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {CSS2DRenderer,CSS2DObject} from 'three/addons/renderers/CSS2DRenderer.js';

type Run={run_id:string;scenario:string;run_name:string;minutes:number;push_id:string;run_url:string};
type State={asset_id:string;status:string;colour:string};
const $=(id:string)=>document.getElementById(id)!;
const stage=$('stage');
const scene=new THREE.Scene(); scene.background=new THREE.Color('#0b1522');
let renderer:THREE.WebGLRenderer|undefined;
let camera:THREE.PerspectiveCamera|THREE.OrthographicCamera;
let controls:OrbitControls;
const labelRenderer=new CSS2DRenderer();labelRenderer.domElement.style.cssText='position:absolute;top:0;pointer-events:none';stage.append(labelRenderer.domElement);
const assets=new Map<string,THREE.Mesh>();
let model:THREE.Group|undefined, pub:any, active:Run, generation=0, imageMode=false;
const convert=(p:number[])=>new THREE.Vector3(p[0],p[2],-p[1]);

function preset(name:string){
 if(!pub||!renderer)return;
 const data=pub.cameras.find((x:any)=>x[0]===name), aspect=stage.clientWidth/stage.clientHeight;
 camera=name==='Overview'?new THREE.OrthographicCamera(-45,45,45/aspect,-45/aspect,.1,1000):new THREE.PerspectiveCamera(28.4,aspect,.1,1000);
 camera.position.copy(convert(data[2]));camera.lookAt(convert(data[3]));
 controls?.dispose();controls=new OrbitControls(camera,renderer.domElement);controls.target.copy(convert(data[3]));controls.enableDamping=true;controls.update();
}
function resize(){if(!renderer||!camera)return;const w=stage.clientWidth,h=stage.clientHeight;renderer.setSize(w,h);labelRenderer.setSize(w,h);if(camera instanceof THREE.PerspectiveCamera)camera.aspect=w/h;else{camera.top=45*h/w;camera.bottom=-camera.top;}camera.updateProjectionMatrix();}
function showImage(reason:string){imageMode=true;const img=$('fallback') as HTMLImageElement;img.src=`/api/publications/${pub.audit.push_id}/frame.png`;img.style.display='block';renderer?.domElement.style.setProperty('display','none');labelRenderer.domElement.style.display='none';$('message').textContent=`${pub.image_type} · ${reason}`;}
async function get(url:string,signal?:AbortSignal){const r=await fetch(url,{signal});const data=await r.json();if(!r.ok)throw new Error(data.message||data.error||r.statusText);return data;}
let request:AbortController|undefined;
async function select(run:Run){
 const epoch=++generation;request?.abort();request=new AbortController();active=run;$('status').textContent='Querying Unity Catalog…';
 try{
  const [publication,rows]=await Promise.all([get(`/api/publications/${run.push_id}`,request.signal),get(`/api/runs/${run.run_id}/current`,request.signal)]);
  if(epoch!==generation)return;pub=publication;
  $('identity').textContent=`Run ${run.run_id}\nPush ${pub.audit.push_id.slice(0,12)}`;
  ($('mlflow') as HTMLAnchorElement).href=run.run_url;
  $('thresholds').replaceChildren(...pub.legend.thresholds.map((row:any)=>{const p=document.createElement('div');p.textContent=row.text;return p;}));
  if(model)scene.remove(model);assets.clear();
  if(renderer){try{
   const gltf=await new GLTFLoader().loadAsync(`/api/publications/${run.push_id}/model.glb`);
   if(epoch!==generation)return;model=gltf.scene;scene.add(model);
   model.traverse(o=>{if(o instanceof THREE.Mesh){o.material=(o.material as THREE.Material).clone();if(rows.some((r:State)=>r.asset_id===o.name))assets.set(o.name,o);}});
   if(assets.size!==10)throw new Error('Expected ten stable asset nodes');
   for(const row of rows){const mesh=assets.get(row.asset_id)!;(mesh.material as THREE.MeshStandardMaterial).color.set(row.colour);mesh.userData.status=row.status;}
   for(const row of pub.labels){const element=document.createElement('div');element.className='label';element.textContent=row.text;const label=new CSS2DObject(element);label.position.copy(convert(row.anchor));model.add(label);}
   preset('Overview');resize();
  }catch(error){showImage(String(error));}}
  else showImage('WebGL unavailable');
  if(imageMode)showImage('Image playback');
  $('health').replaceChildren(...rows.filter((r:State)=>r.asset_id.startsWith('GATE_')).map((r:State)=>{const tr=document.createElement('tr');const a=document.createElement('td'),b=document.createElement('td');a.textContent=r.asset_id.replace('GATE_','');b.textContent=r.status;b.style.color=r.colour;tr.append(a,b);return tr;}));
  $('message').textContent=imageMode?`${pub.image_type} · published minute ${pub.audit.step}`:`Live SQL state · A4 ${rows.find((r:State)=>r.asset_id==='GATE_A4').status}`;
  $('status').textContent='Unity Catalog connected';
 }catch(error){if(epoch===generation){$('status').textContent='Data unavailable';$('message').textContent=String(error);}}
}
try{renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;stage.prepend(renderer.domElement);renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();if(pub)showImage('Graphics context lost');});scene.add(new THREE.HemisphereLight(0xffffff,0x7a8591,3));const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(20,60,30);scene.add(light);renderer.setAnimationLoop(()=>{if(camera&&!imageMode){controls.update();renderer!.render(scene,camera);labelRenderer.render(scene,camera);}});}catch{renderer=undefined;}
$('overview').onclick=()=>{preset('Overview');resize();};$('closeup').onclick=()=>{preset('A4CloseUp');resize();};$('image').onclick=()=>showImage('Selected');new ResizeObserver(resize).observe(stage);
get('/api/runs').then((runs:Run[])=>{const dropdown=$('run') as HTMLSelectElement;for(const r of runs){const option=new Option(`${r.scenario} · ${r.run_id.slice(0,8)}`,r.run_id);dropdown.add(option);}const initial=runs.find(r=>r.scenario==='delay_A4')||runs[0];if(!initial)throw new Error('Publish GLB-enabled runs first');dropdown.value=initial.run_id;dropdown.onchange=()=>select(runs.find(r=>r.run_id===dropdown.value)!);return select(initial);}).catch(error=>{$('message').textContent=String(error);});
