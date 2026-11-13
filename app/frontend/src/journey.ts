import {localClock,countdown} from './airport-clock';
import * as THREE from 'three';
import {journeyMap} from './journey-map';

type Arm = { probability:number; ci:number[]; p50:number; p90:number; bins:number[];
  means:Record<string,number>; sample:Record<string,number> };
type Profile = {kind:string; bag:boolean; coffee:boolean; restroom:boolean; lanes:number;
  ahead:number; arms:Arm[]; gain:number; gain_ci:number[]};
type Experiment = {run_id:string; url:string; inputs:{flight:string; gate:string; entry:string;
  departure?:string;close:string; budget:number; trials:number; queue:number; policy:Record<string,unknown>}; profiles:Profile[]};
const labels:Record<string,string> = {bag:'Bag drop',security_wait:'Security line',
  screening:'Screening',coffee:'Coffee',restroom:'Restroom',walk:'Walk to gate'};
const percent = (p:number) => (100*p).toFixed(1)+'%';
const minutes = (s:number) => (s/60).toFixed(1)+' min';

export function journeyPanel(scene:THREE.Scene, load:(id:string)=>Promise<Experiment[]>,
                             recorded:(step:number)=>Promise<{step:number;push_id:string}[]>,
                             durations:(run:string,params:URLSearchParams)=>Promise<
                               {lanes:number;histogram:{seconds:number;n:number}[]}[]>,
                             gatePoint:(id:string)=>THREE.Vector3|undefined, pause:()=>void, zone:()=>string) {
  const panel=document.createElement('section');
  panel.innerHTML=`<h2>Will I make my flight?</h2><button data-load disabled>Explore this minute</button>
    <button id="busiest" disabled>Jump to busiest minute</button><p data-story></p><p data-status aria-live="polite"></p><div data-controls hidden>
    <label>Flight<select data-run></select></label>
    <div><label>I arrive <input data-arrival type="number" min="0" max="1440" step="1" required> minutes</label>
    <label><select data-reference aria-label="Arrival time reference">
    <option value="close">before boarding closes</option><option value="departure">before departure</option>
    </select></label></div>
    <label>Checkpoint<select data-kind><option value="standard">Standard security</option>
    <option value="precheck">TSA PreCheck</option></select></label>
    <label><input type="checkbox" data-bag checked> Checked bag</label>
    <label><input type="checkbox" data-coffee> Coffee</label>
    <label><input type="checkbox" data-restroom> Restroom</label>
    <div data-outcome aria-live="polite"></div><ol data-route aria-label="Route through the terminal"></ol>
    <label>Replay trial 1<select data-arm><option>Baseline</option><option>Additional lane</option></select></label>
    <button data-play>Play passenger journey</button><p data-clock aria-live="off"></p>
    <details><summary>Journey times and bottlenecks</summary><table><caption>Journey time distribution · trial counts</caption>
    <thead><tr><th>Minutes</th><th>Baseline</th><th>+1 lane</th></tr></thead><tbody></tbody></table>
    <p data-bottleneck></p></details><a data-link target="_blank" rel="noopener">Journey in MLflow</a>
    <details><summary>Model assumptions</summary><p>Queue mix, service times and stop locations are synthetic.
    The queue stays fixed until this passenger joins it. Each lane starts available.
    Times below are minimum, most likely and maximum seconds.</p><pre style="white-space:pre-wrap" data-policy></pre></details></div>`;
  document.getElementById('planner')!.append(panel);
  const el=<T extends HTMLElement>(key:string)=>panel.querySelector<T>('[data-'+key+']')!;
  const run=el<HTMLSelectElement>('run'), kind=el<HTMLSelectElement>('kind'), arm=el<HTMLSelectElement>('arm');
  const checked=(k:string)=>el<HTMLInputElement>(k).checked;
  let id='', generation=0, frame=0, experiments:Experiment[]=[];
  let chosen:Profile, experiment:Experiment;
  const map=journeyMap(scene,gatePoint);
  const arrival=el<HTMLInputElement>('arrival'),reference=el<HTMLSelectElement>('reference');
  const play=el<HTMLButtonElement>('play');
  let budget=0, request=0,sourceTimer=0;
  const cache=new Map<string,ReturnType<typeof durations>>();
  function activeStep(index:number){
    map.highlight(index);
    Array.from(el('route').children).forEach((item,i)=>item.classList.toggle('active',i===index));
  }
  const group=new THREE.Group();
  scene.add(group);
  const person=new THREE.Mesh(new THREE.CapsuleGeometry(.53,1.4),new THREE.MeshStandardMaterial({color:0x44edf2}));
  const crowd=new THREE.InstancedMesh(new THREE.CapsuleGeometry(.22,.65),
    new THREE.MeshStandardMaterial({color:0xe4b581}),100);
  group.add(person,crowd);
  function stop() {
    cancelAnimationFrame(frame); group.visible=false; el('clock').textContent='';
    el('play').textContent='Play passenger journey'; frame=0;
    activeStep(-1);
  }
  let sceneMinute=0, journeyMinute=0;
  function showSource(){
    el('story').textContent='Scene at minute '+sceneMinute+' · Journey recorded at minute '+journeyMinute+'.';
  }
  function selectPublication(next:string,step=0) {
    sceneMinute=step;
    if(next && experiments.length && !el('controls').hidden){
      id=next;stop();showSource();return;
    }
    el('story').textContent='';
    ++generation; id=next; stop(); experiments=[]; el('controls').hidden=true;
    ++request;clearTimeout(sourceTimer);cache.clear();map.clear();
    if(next){map.locate();sourceTimer=window.setTimeout(()=>void read(false),550);}
    el('status').textContent=''; el<HTMLButtonElement>('load').disabled=!next;
  }
  function render() {
    stop(); experiment=experiments[run.selectedIndex];
    chosen=experiment.profiles.find(p=>p.kind===kind.value && p.bag===checked('bag') &&
      p.coffee===checked('coffee') && p.restroom===checked('restroom'))!;
    const {inputs}=experiment, [base,extra]=chosen.arms;
    const buffer=Number(inputs.policy.boarding_buffer_minutes??15);
    const departure=inputs.departure??new Date(Date.parse(inputs.close)+buffer*60000).toISOString();
    el('status').title='UTC · close '+inputs.close+' · departure '+departure+' · queue '+(inputs.entry||'—');
    el('status').textContent=inputs.flight+' · Gate '+inputs.gate.replace('GATE_','')+
      ' · Boarding closes '+localClock(inputs.close,zone())+' · Departs '+localClock(departure,zone())+
      ' · Queue frozen '+localClock(inputs.entry,zone())+'.';
    const keys=Object.keys(labels).filter(k=>k in base.sample);
    map.route(keys,inputs.gate);
    el('route').replaceChildren(...['Arrive at terminal',...keys.map(k=>k==='walk'?
      'Walk to '+inputs.gate.replace('GATE_',''):labels[k])].map(label=>{
      const li=document.createElement('li');li.textContent=label;return li;
    }));
    void estimate();
    const body=panel.querySelector('tbody')!; body.replaceChildren();
    for(let i=0;i<Math.max(base.bins.length,extra.bins.length);i++) {
      const tr=body.insertRow();
      for(const v of [i*5+'–<'+(i+1)*5,base.bins[i]||0,extra.bins[i]||0]) tr.insertCell().textContent=String(v);
    }
    const bottleneck=(a:Arm)=>{const [k,v]=Object.entries(a.means).sort((x,y)=>y[1]-x[1])[0];return labels[k]+' ('+minutes(v)+')';};
    el('bottleneck').textContent='Longest average stage: '+bottleneck(base)+' → '+bottleneck(extra)+'.';
    el<HTMLAnchorElement>('link').href=experiment.url;
    el('policy').textContent=inputs.trials+' paired trials. Frozen queue: '+inputs.queue+
      '.\nChance colors: green ≥ 80%, amber ≥ 50%, red below 50%.\n95% intervals at original recorded entry: ';
    el('policy').append(runLink(base.ci.map(percent).join('–')),' / ',runLink(extra.ci.map(percent).join('–')),
      '.\n'+Object.entries(inputs.policy).map(([k,v])=>k.replaceAll('_',' ')+': '+v).join('\n'));
  }
  function runLink(label:string){
    const link=document.createElement('a');
    link.href=experiment.url;link.target='_blank';link.rel='noopener';
    link.textContent=label;link.title='MLflow run '+experiment.run_id.slice(0,8);
    return link;
  }
  async function estimate(){
    const ticket=++request;
    stop();play.disabled=true;
    if(!arrival.validity.valid){el('outcome').textContent='Enter a whole number from 0 to 1440 minutes.';return;}
    const buffer=reference.value==='departure'?Number(experiment.inputs.policy.boarding_buffer_minutes??15):0;
    budget=(arrival.valueAsNumber-buffer)*60;
    let chances=chosen.arms.map(a=>a.probability);
    if(budget!==experiment.inputs.budget){
      const query=new URLSearchParams({checkpoint:chosen.kind,bag:String(chosen.bag),
        coffee:String(chosen.coffee),restroom:String(chosen.restroom)});
      const key=experiment.run_id+'/'+query;
      el('outcome').textContent='Checking recorded journey times…';
      try{
        if(!cache.has(key))cache.set(key,durations(experiment.run_id,query));
        const rows=await cache.get(key)!;
        if(ticket!==request)return;
        if(rows.length!==2)throw Error('Incomplete staffing pair');
        chances=rows.map((arm,i)=>{
          if(arm.lanes!==chosen.lanes+i || arm.histogram.reduce((s,b)=>s+b.n,0)!==experiment.inputs.trials)
            throw Error('Incomplete trial distribution');
          return arm.histogram.reduce((s,b)=>s+(b.seconds<=budget?b.n:0),0)/experiment.inputs.trials;
        });
      }catch{if(ticket===request){cache.delete(key);el('outcome').textContent='Recorded trial times unavailable. Try again.';}return;}
    }
    play.disabled=false;
    const outcome=el('outcome');
    const support=(budget<0?'Boarding closed '+minutes(-budget)+' before arrival. ':
      'You have '+minutes(budget)+' to reach the gate. ');
    outcome.replaceChildren();
    const title=document.createElement('strong');title.textContent='Chance of making boarding';
    const cards=document.createElement('div');cards.className='chance-pair';outcome.append(title,cards);
    const trials=experiment.inputs.trials;
    const extraSuccesses=Math.round(chances[1]*trials)-Math.round(chances[0]*trials);
    const similar=Math.abs(extraSuccesses)*100<trials;
    const figures=similar?chances.slice(0,1):chances;
    figures.forEach((chance,i)=>{
      const card=document.createElement('div'), value=document.createElement('strong');
      value.textContent=percent(chance);
      const caption=document.createElement('span');
      caption.className='lane-count';
      caption.textContent=i===0?chosen.lanes+(chosen.lanes===1?' lane':' lanes'):'+1 lane';
      value.className='chance '+(chance>=.8?'likely':chance>=.5?'uncertain':'unlikely');
      card.append(value,caption,runLink('Open in MLflow'));cards.append(card);
    });
    const detail=document.createElement('p');outcome.append(detail);
    if(similar)detail.append("An extra lane wouldn't change your odds. ");
    detail.append(support+chosen.ahead+' ahead of you in '+(chosen.kind==='standard'?'standard security.':'TSA PreCheck.'));
  }
  async function read(manual:boolean){
    clearTimeout(sourceTimer);if(manual)pause(); const ticket=++generation;
    const selected=id, minute=sceneMinute;
    if(!experiments.length)el('status').textContent='Reading recorded journeys…';
    try { let data=await load(selected); if(ticket!==generation || selected!==id)return;
      let source=minute;
      if(!data.length && !experiments.length){
        const candidates=await recorded(minute);
        for(const candidate of candidates){
          if(ticket!==generation || selected!==id)return;
          if(candidate.push_id===selected)continue;
          data=await load(candidate.push_id);
          if(data.length){source=candidate.step;break;}
        }
      }
      if(ticket!==generation || selected!==id)return;
      if(!data.length){
        if(experiments.length){showSource();el('story').textContent+=' No journey was recorded for this scene minute.';}
        else el('status').textContent='No passenger journey has been recorded for this replay.';
        return;
      }
      if(experiments.length && source===journeyMinute){showSource();return;}
      experiments=data;journeyMinute=source;showSource();
      run.replaceChildren(...data.map(e=>new Option(e.inputs.flight+' · '+e.run_id.slice(0,8),e.run_id)));
      arrival.value=String(Math.max(0,data[0].inputs.budget/60));reference.value='close';
      el('controls').hidden=false;render();
    } catch {if(ticket===generation && selected===id)el(experiments.length?'story':'status').textContent='Journey lookup unavailable for this minute.';}
  }
  el('load').onclick=()=>void read(true);
  arrival.oninput=()=>void estimate();
  panel.onchange=(e)=>{if(e.target!==arrival)render();};
  el('play').onclick=()=>{
    if(frame){stop();return;}
    pause();
    const points=map.points;
    const segments=Object.entries(chosen.arms[arm.selectedIndex].sample)
      .sort(([a],[b])=>Object.keys(labels).indexOf(a)-Object.keys(labels).indexOf(b));
    const total=segments.reduce((s,[,d])=>s+d,0), start=performance.now();
    const entry=points.entry, matrix=new THREE.Matrix4();
    group.visible=!!gatePoint(experiment.inputs.gate); el('play').textContent='Stop passenger replay';
    function animate(now:number) {
      const t=Math.min(total,(now-start)*.06); // 60 simulated seconds per wall second
      let elapsed=0, from=entry;
      for(const [key,duration] of segments) {
        if(t<=elapsed+duration || key==='walk'){
          const f=Math.min(1,(t-elapsed)/Math.max(1,duration));
          activeStep(segments.findIndex(([stage])=>stage===key)+1);
          if(group.visible){person.position.lerpVectors(from,points[key],key==='walk'?f:Math.min(1,f*6));person.position.y=1.5;}
          crowd.count=key==='security_wait'?Math.min(100,Math.ceil(chosen.ahead*(1-f))):0;
          for(let i=0;i<crowd.count;i++) crowd.setMatrixAt(i,matrix.makeTranslation(-14+(i%6)*.6,.7,4.8+Math.floor(i/6)*.62));
          crowd.instanceMatrix.needsUpdate=true;crowd.computeBoundingSphere();
          el('clock').textContent=labels[key]+' · '+minutes(t)+' elapsed · '+'Boarding closes in '+countdown(budget-t);
          break;
        }
        elapsed+=duration;from=points[key];
      }
      if(t<total)frame=requestAnimationFrame(animate);
      else{frame=0;el('play').textContent='Replay passenger journey';el('clock').textContent=
        (total<=budget?'Made boarding':'Missed boarding')+' · '+minutes(total)+' elapsed · Boarding closes in '+countdown(budget-total);}
    }
    frame=requestAnimationFrame(animate);
  };
  selectPublication('');return selectPublication;
}
