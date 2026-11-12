import * as THREE from 'three';

type Arm = { probability:number; ci:number[]; p50:number; p90:number; bins:number[];
  means:Record<string,number>; sample:Record<string,number> };
type Profile = {kind:string; bag:boolean; coffee:boolean; restroom:boolean; lanes:number;
  ahead:number; arms:Arm[]; gain:number; gain_ci:number[]};
type Experiment = {run_id:string; url:string; inputs:{flight:string; gate:string; entry:string;
  close:string; budget:number; trials:number; queue:number; policy:Record<string,unknown>}; profiles:Profile[]};
const labels:Record<string,string> = {bag:'Bag drop',security_wait:'Security line',
  screening:'Screening',coffee:'Coffee',restroom:'Restroom',walk:'Walk to gate'};
const percent = (p:number) => (100*p).toFixed(1)+'%';
const minutes = (s:number) => (s/60).toFixed(1)+' min';

export function journeyPanel(scene:THREE.Scene, load:(id:string)=>Promise<Experiment[]>,
                             gatePoint:(id:string)=>THREE.Vector3|undefined, pause:()=>void) {
  const panel=document.createElement('section');
  panel.innerHTML=`<h3>Will I make my flight?</h3><button data-load disabled>Explore this minute</button>
    <p data-status aria-live="polite"></p><div data-controls hidden>
    <label>Recorded flight and run<select data-run></select></label>
    <label>Checkpoint<select data-kind><option value="standard">Standard security</option>
    <option value="precheck">TSA PreCheck</option></select></label>
    <label><input type="checkbox" data-bag checked> Checked bag</label>
    <label><input type="checkbox" data-coffee> Coffee</label>
    <label><input type="checkbox" data-restroom> Restroom</label>
    <p data-outcome></p><table><caption>Journey time distribution · trial counts</caption>
    <thead><tr><th>Minutes</th><th>Baseline</th><th>+1 lane</th></tr></thead><tbody></tbody></table>
    <p data-bottleneck></p><label>Replay trial 1<select data-arm><option>Baseline</option>
    <option>Additional lane</option></select></label><button data-play>Play passenger journey</button>
    <p data-clock aria-live="off"></p><a data-link target="_blank" rel="noopener">Journey in MLflow</a>
    <details><summary>Model assumptions</summary><p>Queue mix, service times and stop locations are synthetic.
    The queue stays fixed until this passenger joins it. Each lane starts available.
    Times below are minimum, most likely and maximum seconds.</p><pre style="white-space:pre-wrap" data-policy></pre></details></div>`;
  document.getElementById('metrics')!.before(panel);
  const el=<T extends HTMLElement>(key:string)=>panel.querySelector<T>('[data-'+key+']')!;
  const run=el<HTMLSelectElement>('run'), kind=el<HTMLSelectElement>('kind'), arm=el<HTMLSelectElement>('arm');
  const checked=(k:string)=>el<HTMLInputElement>(k).checked;
  let id='', generation=0, frame=0, experiments:Experiment[]=[];
  let chosen:Profile, experiment:Experiment;
  const group=new THREE.Group();
  scene.add(group);
  const person=new THREE.Mesh(new THREE.CapsuleGeometry(.53,1.4),new THREE.MeshStandardMaterial({color:0x44edf2}));
  const crowd=new THREE.InstancedMesh(new THREE.CapsuleGeometry(.22,.65),
    new THREE.MeshStandardMaterial({color:0xe4b581}),100);
  group.add(person,crowd);
  function stop() {
    cancelAnimationFrame(frame); group.visible=false; el('clock').textContent='';
    el('play').textContent='Play passenger journey'; frame=0;
  }
  function selectPublication(next:string) {
    ++generation; id=next; stop(); experiments=[]; el('controls').hidden=true;
    el('status').textContent=''; el<HTMLButtonElement>('load').disabled=!next;
  }
  function render() {
    stop(); experiment=experiments[run.selectedIndex];
    chosen=experiment.profiles.find(p=>p.kind===kind.value && p.bag===checked('bag') &&
      p.coffee===checked('coffee') && p.restroom===checked('restroom'))!;
    const {inputs}=experiment, [base,extra]=chosen.arms;
    el('status').textContent=inputs.flight+' · '+inputs.gate.replace('GATE_','')+' · '+
      minutes(inputs.budget)+' from entry to boarding close ('+inputs.close.slice(11,16)+' UTC).';
    el('outcome').textContent=chosen.ahead+' ahead · '+chosen.lanes+' → '+(chosen.lanes+1)+' lanes. '+
      'Chance of making boarding: '+percent(base.probability)+' → '+percent(extra.probability)+
      ' (+'+(100*chosen.gain).toFixed(1)+' points). Median '+minutes(base.p50)+' → '+minutes(extra.p50)+
      '. 90th percentile '+minutes(base.p90)+' → '+minutes(extra.p90)+'.';
    const body=panel.querySelector('tbody')!; body.replaceChildren();
    for(let i=0;i<Math.max(base.bins.length,extra.bins.length);i++) {
      const tr=body.insertRow();
      for(const v of [i*5+'–<'+(i+1)*5,base.bins[i]||0,extra.bins[i]||0]) tr.insertCell().textContent=String(v);
    }
    const bottleneck=(a:Arm)=>{const [k,v]=Object.entries(a.means).sort((x,y)=>y[1]-x[1])[0];return labels[k]+' ('+minutes(v)+')';};
    el('bottleneck').textContent='Longest average stage: '+bottleneck(base)+' → '+bottleneck(extra)+'.';
    el<HTMLAnchorElement>('link').href=experiment.url;
    el('policy').textContent=inputs.trials+' paired trials. Frozen queue: '+inputs.queue+
      '.\n95% sampling intervals: '+base.ci.map(percent).join('–')+' / '+extra.ci.map(percent).join('–')+
      '.\n'+Object.entries(inputs.policy).map(([k,v])=>k.replaceAll('_',' ')+': '+v).join('\n');
  }
  el('load').onclick=async()=>{
    pause(); const ticket=++generation; stop(); el('controls').hidden=true;
    el('status').textContent='Reading recorded journeys…';
    try { const data=await load(id); if(ticket!==generation)return;
      experiments=data;
      if(!data.length){el('status').textContent='No journey recorded for this minute.';return;}
      run.replaceChildren(...data.map(e=>new Option(e.inputs.flight+' · '+e.run_id.slice(0,8),e.run_id)));
      el('controls').hidden=false;render();
    } catch {if(ticket===generation)el('status').textContent='Journey data unavailable for this minute.';}
  };
  panel.onchange=render;
  el('play').onclick=()=>{
    if(frame){stop();return;}
    pause();
    const dest=gatePoint(experiment.inputs.gate);
    const gate=dest || new THREE.Vector3(0,1,0);
    const points:Record<string,THREE.Vector3>={bag:new THREE.Vector3(-8,1.5,5),
      security_wait:new THREE.Vector3(-12,1.5,4.5),screening:new THREE.Vector3(-10,1.5,0),
      coffee:new THREE.Vector3(5,1.5,3),restroom:new THREE.Vector3(15,1.5,-3),
      walk:new THREE.Vector3(gate.x,1.5,gate.z*.65)};
    const segments=Object.entries(chosen.arms[arm.selectedIndex].sample)
      .sort(([a],[b])=>Object.keys(labels).indexOf(a)-Object.keys(labels).indexOf(b));
    const total=segments.reduce((s,[,d])=>s+d,0), start=performance.now();
    const entry=new THREE.Vector3(-6,1.5,7), matrix=new THREE.Matrix4();
    group.visible=!!dest; el('play').textContent='Stop passenger replay';
    function animate(now:number) {
      const t=Math.min(total,(now-start)*.06); // 60 simulated seconds per wall second
      let elapsed=0, from=entry;
      for(const [key,duration] of segments) {
        if(t<=elapsed+duration || key==='walk'){
          const f=Math.min(1,(t-elapsed)/Math.max(1,duration));
          person.position.lerpVectors(from,points[key],key==='walk'?f:Math.min(1,f*6));
          crowd.count=key==='security_wait'?Math.min(100,Math.ceil(chosen.ahead*(1-f))):0;
          for(let i=0;i<crowd.count;i++) crowd.setMatrixAt(i,matrix.makeTranslation(-14+(i%6)*.6,.7,4.8+Math.floor(i/6)*.62));
          crowd.instanceMatrix.needsUpdate=true;crowd.computeBoundingSphere();
          el('clock').textContent=labels[key]+' · '+minutes(t)+' elapsed · '+minutes(experiment.inputs.budget-t)+' to close';
          break;
        }
        elapsed+=duration;from=points[key];
      }
      if(t<total)frame=requestAnimationFrame(animate);
      else{frame=0;el('play').textContent='Replay passenger journey';el('clock').textContent=
        (total<=experiment.inputs.budget?'Made boarding':'Missed boarding')+' · '+minutes(total)+' elapsed';}
    }
    frame=requestAnimationFrame(animate);
  };
  selectPublication('');return selectPublication;
}
