import {localClock} from './airport-clock';
import {layoutLabels} from './labels';
import * as THREE from 'three';
import {journeyPanel} from './journey';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {CSS2DRenderer,CSS2DObject} from 'three/addons/renderers/CSS2DRenderer.js';

type Run={run_id:string;scenario:string;run_name:string;minutes:number;push_id:string;run_url:string;replay_available:boolean;replay_unavailable_reason?:string;comparison:{url:string|null;reason:string|null;comparison_id?:string}};
type State={asset_id:string;status:string;colour:string};
const $=(id:string)=>document.getElementById(id)!;
const workspace = new URLSearchParams(location.search).get('workspace') === '1';
if(workspace){
 document.documentElement.classList.add('workspace-embedded');
 window.addEventListener('keydown',event=>{
  if(event.key==='Escape')parent.postMessage({type:'twin-exit-expanded'},location.origin);
 });
}
const apiPrefix = workspace ? '/app-services/airport-twin' : '';
const initialState = new URLSearchParams(location.search);
function persistState() {
 if (!active) return;
 const state = new URLSearchParams({run:active.run_id,gate:selectedGate,minute:String(step)});
 history.replaceState(null,'','?' + state + (workspace ? '&workspace=1' : ''));
 if (workspace) parent.postMessage({type:'twin-state',search:state.toString()},location.origin);
}
function evidenceLink(id:string, raw:string) {
 const link=$(id) as HTMLAnchorElement;
 link.href=raw;link.onclick=null;
 if (!workspace) return;
 try {
  const url=new URL(raw), hash=url.hash.slice(1);
  const query=new URLSearchParams(hash.split('?')[1] || '');
  const params=new URLSearchParams();
  if(id==='compare') {
   const runs=JSON.parse(query.get('runs') || '[]');
   const experiments=JSON.parse(query.get('experiments') || '[]');
   if(runs.length!==2 || !runs.every((r:any)=>typeof r==='string')) throw new Error('Comparison unavailable');
   params.set('compare',runs.join(','));
   if(experiments[0]) params.set('experiment',experiments[0]);
  } else {
   const match=hash.match(/experiments\/([^/]+)\/runs\/([^/]+)/);
   if(!match) throw new Error('Run link unavailable');
   params.set('experiment',match[1]);params.set('run',match[2]);
  }
  link.href='/experiments?'+params;
  link.onclick=event=>{event.preventDefault();persistState();parent.postMessage({type:'twin-experiment',url:link.getAttribute('href')},location.origin);};
 } catch { link.removeAttribute('href');$('comparison-note').textContent='Experiment link unavailable for this run.'; }
}
const stage=$('stage');
const scene=new THREE.Scene(); scene.background=new THREE.Color('#0b1522');
let renderer:THREE.WebGLRenderer|undefined;
let camera:THREE.PerspectiveCamera|THREE.OrthographicCamera;
let controls:OrbitControls;
const labelRenderer=new CSS2DRenderer();labelRenderer.domElement.style.cssText='position:absolute;top:0;pointer-events:none';stage.append(labelRenderer.domElement);
const assets=new Map<string,THREE.Mesh>();
const setJourneyPublication=journeyPanel(scene, id=>get('/api/publications/'+id+'/journeys'),
 (run,params)=>get('/api/journeys/'+run+'/durations?'+params),
 id=>assets.get(id)?.getWorldPosition(new THREE.Vector3()), ()=>pause(false), ()=>replay?.airport_timezone||'America/Los_Angeles');
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
function showImage(reason:string){imageMode=true;const img=$('fallback') as HTMLImageElement;img.onerror=()=>{$('message').textContent='Frame unavailable for this publication';};img.src=apiPrefix+`/api/publications/${pub.audit.push_id}/frame.png`;img.style.display='block';renderer?.domElement.style.setProperty('display','none');labelRenderer.domElement.style.display='none';$('image').textContent='3D viewer';$('message').textContent=`${pub.image_type} · ${reason}`;}
async function get(url:string,signal?:AbortSignal){const r=await fetch(apiPrefix+url,{signal});const data=await r.json();if(!r.ok)throw Object.assign(new Error(data.message||data.error||r.statusText),{status:r.status,code:data.error});return data;}
let request:AbortController|undefined;
let seekGeneration=0;
let selectedGate='GATE_A4',provenanceGeneration=0;
async function inspectGate(assetId:string,reveal=false){
 if(reveal){($('gate-diagnostics') as HTMLDetailsElement).open=true;$('provenance').scrollIntoView({block:'start',behavior:'smooth'});}
 selectedGate=assetId;persistState();const ticket=++provenanceGeneration,epoch=generation,push=pub?.audit.push_id;
 if(!push)return;$('gate-title').textContent=assetId.replace('GATE_','')+' · Why this color?';$('explanation').textContent='Checking publication evidence…';for(const id of ['sensors','verification','rule','source-versions','audit-details'])$(id).replaceChildren();
 try{const data=await get(`/api/publications/${push}/assets/${assetId}/provenance`,request?.signal);
  if(ticket!==provenanceGeneration||epoch!==generation||push!==pub?.audit.push_id)return;
  $('explanation').textContent=data.explanation;$('verification').textContent=(data.verification==='verified'?'Verified against published Delta versions':data.verification)+' · '+localClock(data.sensors[0].ts,replay?.airport_timezone||'America/Los_Angeles');$('verification').title=data.sensors[0].ts+' UTC';
  $('sensors').replaceChildren(...data.sensors.map((row:any)=>{const tr=document.createElement('tr');for(const value of [row.metric,row.value_num??row.value_str,row.warn===null?'—':`${row.warn} / ${row.crit}`,row.status]){const td=document.createElement('td');td.textContent=String(value);tr.append(td);}return tr;}));
  $('rule').textContent=data.rule+' · '+data.rule_mode;$('source-versions').textContent=`Run ${data.run_id.slice(0,8)} · push ${data.push_id.slice(0,12)} · minute ${data.step}\n`+Object.entries(data.delta_versions).map(([k,v])=>`${k} v${v}`).join(' · ');
  $('audit-details').textContent=JSON.stringify({sensors:data.sensors,details:data.details},(key,value)=>key==='ts'&&typeof value==='string'?localClock(value,replay?.airport_timezone||'America/Los_Angeles'):value,2);
 }catch(error){if(ticket===provenanceGeneration&&epoch===generation)$('explanation').textContent='Evidence unavailable: '+String(error);}
}
let replay:any,frames=new Map<number,any>(),step=0,playing=false,timer:number|undefined;
let finishBlend:(()=>void)|undefined;
async function ripple(frame:any,from:Map<string,THREE.Color>,epoch:number){
 if(!renderer||imageMode||from.size!==10)return;
 const origin=pub.labels.find((r:any)=>r.asset_id==='GATE_A4').anchor;
 const distances=new Map<string,number>(pub.labels.map((r:any)=>[r.asset_id,Math.hypot(...r.anchor.map((v:number,i:number)=>v-origin[i]))]));
 const maximum=Math.max(...distances.values())||1;const began=performance.now();
 renderer.domElement.dataset.blending='true';$('play').textContent='Pause';
 await new Promise<void>(resolve=>{
  let done=false;
  const finish=()=>{if(done)return;done=true;if(epoch===generation){paint(frame);renderer!.domElement.dataset.blending='false';$('play').textContent='Play';}if(finishBlend===finish)finishBlend=undefined;resolve();};finishBlend=finish;
  function update(now:number){if(done)return;if(epoch!==generation){finish();return;}const elapsed=(now-began)/1500;if(elapsed>=1){finish();return;}
   for(const row of frame.states){const t=Math.max(0,Math.min(1,(elapsed-.4*distances.get(row.asset_id)!/maximum)/.6)),eased=t*t*(3-2*t),mesh=assets.get(row.asset_id)!;
    const colour=from.get(row.asset_id)!.clone().lerp(new THREE.Color(row.colour),eased),pulse=.18*Math.sin(Math.PI*t);colour.lerp(new THREE.Color(1,1,1),pulse);(mesh.material as THREE.MeshStandardMaterial).color.copy(colour);}
   requestAnimationFrame(update);
  }requestAnimationFrame(update);
 });
}
let auditUnavailable=false;
function imageFrame(minute:number){const frame=replay.images.find((f:any)=>f.step===minute);if(!frame)throw new Error('No publication for requested minute');clearEvidence();assets.clear();step=minute;persistState();pub.audit={...pub.audit,push_id:frame.push_id,step};pub.image_type=frame.image_type;$('identity').textContent=`Run ${active.run_id}\nPush ${frame.push_id}\nSQL audit unavailable`;$('explanation').textContent='Historical source data unavailable; showing this publication’s image only.';($('timeline') as HTMLInputElement).value=String(step);$('step').textContent=`Minute ${step} / ${active.minutes-1}`;showImage('AUDIT_VERSION_UNAVAILABLE · published images only');ready(true);}
function pause(inspect=true){++seekGeneration;playing=false;clearTimeout(timer);finishBlend?.();$('play').textContent='Play';if(inspect&&pub)void inspectGate(selectedGate);}
function ready(enabled:boolean){
 ($('busiest') as HTMLButtonElement).disabled=!enabled||auditUnavailable;
 for(const id of ['play','timeline'])($(id) as HTMLButtonElement|HTMLInputElement).disabled=!enabled;
 for(const id of ['overview','closeup'])($(id) as HTMLButtonElement).disabled=!enabled||!renderer||assets.size!==10;
 ($('image') as HTMLButtonElement).disabled=!enabled||auditUnavailable;
}
function clearEvidence(){
 setJourneyPublication('');
 ++provenanceGeneration;
 for(const id of ['metrics','health','sensors','verification','rule','source-versions','audit-details','thresholds','step'])$(id).replaceChildren();
 $('gate-title').textContent='Select a gate';$('explanation').textContent='';
 ($('mlflow') as HTMLAnchorElement).removeAttribute('href');
 const img=$('fallback') as HTMLImageElement;img.onerror=null;img.style.display='none';img.removeAttribute('src');
 if(model)model.visible=false;labelRenderer.domElement.style.display='none';
 if(renderer){renderer.domElement.dataset.assetStates='[]';renderer.domElement.dataset.blending='false';}
}
ready(false);
function paint(frame:any,story=false){
 setJourneyPublication(frame.push_id,story?frame.step:undefined);
 step=frame.step;persistState();pub.audit={...pub.audit,push_id:frame.push_id,step};pub.image_type=frame.image_type;
 for(const row of frame.states){const mesh=assets.get(row.asset_id);if(mesh){(mesh.material as THREE.MeshStandardMaterial).color.set(row.colour);mesh.userData.status=row.status;}}
 if(renderer)renderer.domElement.dataset.assetStates=JSON.stringify([...assets].map(([id,mesh])=>({asset_id:id,status:mesh.userData.status,colour:'#'+(mesh.material as THREE.MeshStandardMaterial).color.getHexString()})));
 ($('timeline') as HTMLInputElement).value=String(step);$('step').textContent=`Minute ${step} / ${active.minutes-1}`;
 $('identity').textContent=`${active.run_name}\nRun ${active.run_id}\nPush ${frame.push_id.slice(0,12)}\nReplay ${replay.replay_id.slice(0,12)}`;
 $('metrics').replaceChildren(...Object.entries(frame.metrics).map(([key,value])=>{const p=document.createElement('p');p.textContent=`${key}: ${Number(value).toFixed(key==='avg_co2'?1:0)}`;return p;}));
 $('health').replaceChildren(...frame.states.filter((r:State)=>r.asset_id.startsWith('GATE_')).map((r:any)=>{const tr=document.createElement('tr');for(const [i,value] of [r.asset_id.replace('GATE_',''),r.status,r.pax_count].entries()){const td=document.createElement('td');if(i===0){const button=document.createElement('button');button.textContent=String(value);button.setAttribute('aria-label','Explain '+value);button.onclick=()=>void inspectGate(r.asset_id,true);td.append(button);}else td.textContent=String(value??'—');td.style.color=r.colour;tr.append(td);}return tr;}));
 $('message').textContent=`Audited minute ${step} · A4 ${frame.states.find((r:State)=>r.asset_id==='GATE_A4').status} · Security ${frame.states.find((r:State)=>r.asset_id==='SECURITY').status}${replay.thresholds_changed?' · Current thresholds differ; published thresholds retained':''}`;
 if(imageMode)showImage('Exact published minute '+step);
 if(!playing)void inspectGate(selectedGate);else{++provenanceGeneration;$('explanation').textContent='Pause to inspect this minute';for(const id of ['sensors','verification','source-versions','rule','audit-details'])$(id).replaceChildren();}
}
async function pageAt(minute:number,epoch:number){
 if(epoch!==generation||!replay)return;const run=active,selectedReplay=replay,signal=request?.signal;
 let start=Math.floor(minute/60)*60;const end=Math.min(start+60,run.minutes);
 while(start<end){const page=await get(`/api/runs/${run.run_id}/timeline?replay_id=${selectedReplay.replay_id}&start_step=${start}&end_step=${end}`,signal);if(epoch!==generation)return;for(const frame of page.frames)frames.set(frame.step,frame);selectedReplay.thresholds_changed=page.thresholds_changed;start=page.end_step;}
}
async function seek(minute:number,story=false){if(!replay||!pub)return;const epoch=generation,ticket=++seekGeneration;try{if(auditUnavailable){imageFrame(minute);return;}if(!frames.has(minute)){$('status').textContent='Loading audited page…';await pageAt(minute,epoch);}if(epoch!==generation||ticket!==seekGeneration)return;paint(frames.get(minute),story);$('status').textContent='Unity Catalog connected';}catch(error){if(epoch===generation&&ticket===seekGeneration){pause(false);$('status').textContent='Audit unavailable';if((error as any).code==='AUDIT_VERSION_UNAVAILABLE'){auditUnavailable=true;imageFrame(minute);}else{clearEvidence();ready(false);pub=undefined;replay=undefined;$('message').textContent=String(error);}}}}
$('busiest').onclick=async()=>{
 pause(false);const epoch=generation,ticket=seekGeneration;
 try{const result=await get('/api/runs/'+active.run_id+'/busiest?replay_id='+replay.replay_id,request?.signal);
   if(epoch===generation && ticket===seekGeneration)await seek(result.step,true);
 }catch{if(epoch===generation && ticket===seekGeneration)$('message').textContent='Busiest audited minute unavailable.';}
};
async function tick(){if(!playing)return;if(step>=active.minutes-1){pause();return;}await seek(step+1);if(playing)timer=window.setTimeout(tick,250);}
$('play').onclick=()=>{if(playing||finishBlend){pause();return;}playing=true;$('play').textContent='Pause';if(step>=active.minutes-1)void seek(0).then(tick);else void tick();};
$('timeline').addEventListener('input',()=>{pause();void seek(Number(($('timeline') as HTMLInputElement).value));});
async function select(run:Run){
 const previous=new Map([...assets].map(([id,mesh])=>[id,(mesh.material as THREE.MeshStandardMaterial).color.clone()]));
 const epoch=++generation;request?.abort();request=new AbortController();pause(false);clearEvidence();ready(false);frames=new Map();auditUnavailable=false;pub=undefined;replay=undefined;assets.clear();
 active=run;$('status').textContent='Querying Unity Catalog…';$('message').textContent='Loading audited replay…';$('identity').textContent=`Loading run ${run.run_id}`;$('explanation').textContent='Loading run…';
 const compare=$('compare') as HTMLAnchorElement;compare.removeAttribute('href');compare.setAttribute('aria-disabled',String(!run.comparison?.url));if(run.comparison?.url)evidenceLink('compare',run.comparison.url);$('comparison-note').textContent=run.comparison?.reason||'';
 try{
  const sets=await get(`/api/runs/${run.run_id}/replays`,request.signal);if(epoch!==generation)return;
  if(!sets.length)throw Object.assign(new Error('This run has no complete audited replay with matching source versions. Choose another available run.'),{code:'REPLAY_UNAVAILABLE'});replay=sets[0];
  const initialPublication=await get(`/api/publications/${replay.images[run.minutes-1].push_id}`,request.signal);if(epoch!==generation)return;pub=initialPublication;
  await pageAt(run.minutes-1,epoch);if(epoch!==generation)return;
  const initial=frames.get(run.minutes-1);
  const publication=await get(`/api/publications/${initial.push_id}`,request.signal),rows=initial.states;
  if(epoch!==generation)return;pub=publication;
  $('identity').textContent=`Run ${run.run_id}\nPush ${pub.audit.push_id.slice(0,12)}`;
  evidenceLink('mlflow',run.run_url);
  document.querySelectorAll<HTMLElement>('.swatch').forEach((el,i)=>{el.style.background=pub.legend.colours[['ok','warn','crit'][i]];});
  $('thresholds').replaceChildren(...pub.legend.thresholds.map((row:any)=>{const p=document.createElement('div');p.textContent=row.text;return p;}));
  if(model){scene.remove(model);model.traverse(o=>{if(o instanceof CSS2DObject)o.element.remove();if(o instanceof THREE.Mesh){o.geometry.dispose();(o.material as THREE.Material).dispose();}});}assets.clear();
  if(renderer){try{
   const gltf=await new GLTFLoader().loadAsync(apiPrefix+`/api/publications/${initial.push_id}/model.glb`);
   if(epoch!==generation)return;model=gltf.scene;scene.add(model);
   model.traverse(o=>{if(o instanceof THREE.Mesh){o.material=(o.material as THREE.Material).clone();if(rows.some((r:State)=>r.asset_id===o.name))assets.set(o.name,o);}});
   if(assets.size!==10)throw new Error('Expected ten stable asset nodes');
   for(const row of rows){const mesh=assets.get(row.asset_id)!;(mesh.material as THREE.MeshStandardMaterial).color.set(row.colour);mesh.userData.status=row.status;}
   renderer.domElement.dataset.assetStates=JSON.stringify([...assets].map(([id,mesh])=>({asset_id:id,status:mesh.userData.status,colour:'#'+(mesh.material as THREE.MeshStandardMaterial).color.getHexString()})));
   for(const row of pub.labels){
     const mesh=assets.get(row.asset_id)!;
     const bounds=new THREE.Box3().setFromObject(mesh);
     const anchor=bounds.getCenter(new THREE.Vector3());
     anchor.y=bounds.max.y+.2;
     const element=document.createElement('div');
     element.className='label';element.textContent=row.text;
     const label=new CSS2DObject(element);
     label.center.set(.5,1);label.position.copy(mesh.worldToLocal(anchor));mesh.add(label);
   }
   if(!imageMode)labelRenderer.domElement.style.display='block';preset('Overview');resize();
  }catch(error){if(epoch!==generation)return;showImage(String(error));}}
  else showImage('WebGL unavailable');
  if(imageMode)showImage('Image playback');
  $('health').replaceChildren(...rows.filter((r:State)=>r.asset_id.startsWith('GATE_')).map((r:State)=>{const tr=document.createElement('tr');const a=document.createElement('td'),b=document.createElement('td');a.textContent=r.asset_id.replace('GATE_','');b.textContent=r.status;b.style.color=r.colour;tr.append(a,b);return tr;}));
  $('message').textContent=imageMode?`${pub.image_type} · published minute ${pub.audit.step}`:`Live SQL state · A4 ${rows.find((r:State)=>r.asset_id==='GATE_A4').status}`;
  ($('timeline') as HTMLInputElement).max=String(run.minutes-1);paint(initial);ready(true);
  await ripple(initial,previous,epoch);if(epoch!==generation)return;
  $('status').textContent='Unity Catalog connected';
  if(run.minutes>60)void pageAt(0,epoch).catch(()=>{});
 }catch(error){if(epoch===generation){$('status').textContent='Audit unavailable';if((error as any).code==='AUDIT_VERSION_UNAVAILABLE'&&pub){auditUnavailable=true;($('timeline') as HTMLInputElement).max=String(run.minutes-1);imageFrame(run.minutes-1);ready(true);}else{clearEvidence();ready(false);pub=undefined;replay=undefined;$('identity').textContent=`Run ${run.run_id} · replay unavailable`;$('message').textContent=(error as any).code==='REPLAY_NOT_FOUND'?'This replay is no longer available. Refresh the run list or choose another available run.':String(error);}}}
}
try{renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;stage.prepend(renderer.domElement);renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();if(pub)showImage('Graphics context lost');});scene.add(new THREE.HemisphereLight(0xffffff,0x7a8591,3));const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(20,60,30);scene.add(light);renderer.setAnimationLoop(()=>{if(camera&&!imageMode){controls.update();renderer!.render(scene,camera);labelRenderer.render(scene,camera);layoutLabels(labelRenderer.domElement);}});}catch{renderer=undefined;}
$('overview').onclick=()=>{preset('Overview');resize();};$('closeup').onclick=()=>{preset('A4CloseUp');resize();};$('image').onclick=()=>{if(imageMode&&renderer&&model){imageMode=false;renderer.domElement.style.display='block';labelRenderer.domElement.style.display='block';$('fallback').style.display='none';$('image').textContent='Image playback';$('message').textContent='Live SQL state';}else if(pub)showImage('Selected');};new ResizeObserver(resize).observe(stage);
if(renderer){
 let pointerDown:[number,number]=[0,0];
 renderer.domElement.addEventListener('pointerdown',event=>{pointerDown=[event.clientX,event.clientY];});
 renderer.domElement.addEventListener('pointerup',event=>{
  if(!pub||!model?.visible||!camera||Math.hypot(event.clientX-pointerDown[0],event.clientY-pointerDown[1])>5)return;
  const box=renderer!.domElement.getBoundingClientRect(),ray=new THREE.Raycaster();
  ray.setFromCamera(new THREE.Vector2((event.clientX-box.left)/box.width*2-1,-(event.clientY-box.top)/box.height*2+1),camera);
  const hit=ray.intersectObjects([...assets.values()])[0];if(hit?.object.name.startsWith('GATE_'))void inspectGate(hit.object.name,true);
 });
}
let refreshing=false;
async function refreshRuns(){
 if(refreshing)return;
 refreshing=true;($('refresh') as HTMLButtonElement).disabled=true;
 try {
 const runs:Run[]=await get('/api/runs');
 const dropdown=$('run') as HTMLSelectElement;dropdown.replaceChildren();dropdown.add(new Option('Select a published run',''));
 for(const r of runs){const option=new Option(`${r.scenario} · ${r.run_id.slice(0,8)} · ${r.minutes} min${r.replay_available===false?' · replay unavailable':''}`,r.run_id);option.disabled=r.replay_available===false;option.title=r.replay_unavailable_reason||'';dropdown.add(option);}
 dropdown.onchange=()=>{const chosen=runs.find(r=>r.run_id===dropdown.value);if(chosen)void select(chosen);};
 const requested=active?.run_id || initialState.get('run');
 if(requested){
  const chosen=runs.find(r=>r.run_id===requested&&r.replay_available!==false);
  if(chosen){
   dropdown.value=chosen.run_id;
   if(!active){
    selectedGate=/^GATE_A[1-8]$/.test(initialState.get('gate')||'')?initialState.get('gate')!:'GATE_A4';
    await select(chosen);
    const minute=Number(initialState.get('minute'));
    if(initialState.has('minute')&&Number.isInteger(minute)&&minute>=0&&minute<chosen.minutes)await seek(minute);
   }
   return;
  }
  pause(false);clearEvidence();ready(false);pub=undefined;replay=undefined;
  $('message').textContent='Selected run is unavailable. Choose another published run.';
  return;
 }
 const pairs=runs.filter(r=>r.replay_available!==false&&r.scenario==='delay_A4'&&r.comparison?.comparison_id);
 if(pairs.length===1){dropdown.value=pairs[0].run_id;return select(pairs[0]);}
 $('status').textContent='Select a run';$('message').textContent='Choose an explicit published run; no unique filming pair is configured.';
 }catch(error){$('message').textContent='Refresh failed. Use Refresh data to retry. '+String(error);}
 finally{refreshing=false;($('refresh') as HTMLButtonElement).disabled=false;}
}
$('refresh').onclick=()=>void refreshRuns();
void refreshRuns();
