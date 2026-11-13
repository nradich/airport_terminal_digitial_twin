// Synthetic HTTP contract tests; the live project separately tests Delta and MLflow.
import {test,expect} from '@playwright/test';
import {placeLabels} from '../src/labels';
import {countdown,localClock} from '../src/airport-clock';
test('airport clock observes daylight saving and boarding close',()=>{
 expect(localClock('2026-11-09T22:30:00','America/Los_Angeles')).toContain('2:30 PM PST');
 expect(localClock('2026-07-09T22:30:00Z','America/Los_Angeles')).toContain('3:30 PM PDT');
 expect([60,0.1,0,-1].map(countdown)).toEqual(['01:00','00:01','00:00','00:00']);
});
test('security markers and asset tags fit a phone camera viewport without intersection',()=>{
 // A5, Security, Bag drop, Coffee, Restroom and the five overlapping route markers.
 const boxes=[36,60,65,49,65,22,22,22,22,22].map(width=>({x:1,y:4,width,height:23}));
 const placed=placeLabels(boxes,320,240);
 for(const [i,b] of placed.entries()){
   expect(b.x).toBeGreaterThanOrEqual(0);expect(b.y+b.height).toBeLessThanOrEqual(240);
   for(const p of placed.slice(0,i))expect(b.x+b.width<=p.x || p.x+p.width<=b.x ||
     b.y+b.height<=p.y || p.y+p.height<=b.y).toBeTruthy();
 }
});
import {readFile} from 'node:fs/promises';
const ids=['a'.repeat(32),'b'.repeat(32)];
let metadata:any;
test('recorded passenger choices and paired replay clear on minute change',async({page})=>{
 await page.route('**/journeys',async route=>route.fulfill({contentType:'application/json',
   body:await readFile('.local/contracts/journey.json')}));
 await page.goto('/');
 await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await page.getByRole('button',{name:'Explore this minute'}).click();
 await expect(page.locator('[data-outcome]')).toContainText('30 ahead');
 expect(await page.locator('body').innerText()).not.toMatch(/[{}]/);
 const style=await page.locator('.chance').first().evaluate(el=>{
   const css=getComputedStyle(el);
   return {size:parseFloat(css.fontSize),weight:Number(css.fontWeight),color:css.color,
     band:el.classList[1]};
 });
 expect(style.size).toBeGreaterThanOrEqual(28);expect(style.weight).toBeGreaterThanOrEqual(700);
 expect(style.color).toBe(({likely:'rgb(34, 197, 94)',uncertain:'rgb(245, 158, 11)',
   unlikely:'rgb(251, 119, 119)'} as Record<string,string>)[style.band]);
 await page.getByLabel('Checkpoint').selectOption('precheck');
 await page.getByLabel('Coffee',{exact:true}).check();
 await expect(page.locator('[data-outcome]')).toContainText('10 ahead');
 await page.route('**/durations?**',route=>route.fulfill({json:[
   {lanes:1,histogram:[{seconds:900,n:30},{seconds:901,n:70}]},
   {lanes:2,histogram:[{seconds:900,n:60},{seconds:901,n:40}]},
 ]}));
 await page.getByRole('spinbutton').fill('15');
 await expect(page.locator('.chance')).toHaveText(['30.0%','60.0%']);
 await expect(page.locator('.lane-count')).toHaveText(['1 lane','+1 lane']);
 await expect(page.locator('.chance-pair a')).toHaveText(['Open in MLflow','Open in MLflow']);
 await page.getByLabel('Arrival time reference').selectOption('departure');
 await expect(page.locator('[data-outcome]')).toContainText('0.0 min to reach the gate');
 await expect(page.locator('.chance').first()).toHaveText('0.0%');
 await expect(page.locator('.chance')).toHaveCount(1);
 await expect(page.locator('[data-outcome]')).toContainText("An extra lane wouldn't change your odds");
 await expect(page.locator('[data-route]')).toContainText('Coffee');
 await expect(page.locator('#gate-diagnostics')).not.toHaveAttribute('open','');
 await page.getByLabel('Replay trial 1').selectOption({index:1});
 await page.getByRole('button',{name:'Play passenger journey'}).click();
 await expect(page.locator('[data-clock]')).toContainText('Bag drop');
 await page.locator('#timeline').fill('100');
 await expect(page.locator('[data-controls]')).toBeHidden();
 await expect(page.locator('[data-clock]')).toBeEmpty();
});
test.beforeAll(async()=>{metadata=JSON.parse(await readFile('.local/contracts/metadata.json','utf8'));});
test.beforeEach(async({page})=>{
 await page.route('**/api/**',async route=>{
  const url=new URL(route.request().url()),delayed=!url.pathname.includes(ids[0]),run=ids[delayed?1:0];
  const states=metadata.labels.map((label:any)=>({asset_id:label.asset_id,status:delayed&&label.asset_id==='GATE_A4'?'crit':'ok',colour:delayed&&label.asset_id==='GATE_A4'?'#EF4444':'#22C55E',pax_count:delayed?213:6}));
  const pair=`http://mlflow.invalid/#/compare-runs?runs=${encodeURIComponent(JSON.stringify(ids))}`;
  let data:any;
  if(url.pathname==='/api/runs')data=[...ids.map((id,i)=>({run_id:id,scenario:i?'delay_A4':'baseline',run_name:'Contract fixture',minutes:120,push_id:'push',run_url:'http://mlflow.invalid/run/'+id,replay_available:true,comparison:{comparison_id:"contract",url:pair,reason:null}})),{run_id:'c'.repeat(32),scenario:'baseline',minutes:60,replay_available:false,replay_unavailable_reason:'Mixed source versions',comparison:{url:null}}];
  else if(url.pathname.endsWith('/replays'))data=[{replay_id:'replay',images:Array.from({length:120},(_,step)=>({step,push_id:'push'+step,image_type:'Heatmap preview'}))}];
  else if(url.pathname.endsWith('/timeline')){const start=Number(url.searchParams.get('start_step')),end=Number(url.searchParams.get('end_step'));if(start===0)await new Promise(resolve=>setTimeout(resolve,600));data={end_step:end,frames:Array.from({length:end-start},(_,i)=>({step:start+i,push_id:'push'+(start+i),states,metrics:{peak_pax_A4:delayed?213:126},image_type:'Heatmap preview'}))};}
  else if(url.pathname.endsWith('/model.glb'))return route.fulfill({contentType:'model/gltf-binary',body:await readFile('.local/contracts/terminal.glb')});
  else if(url.pathname.endsWith('/provenance')){const asset=url.pathname.split('/').at(-2)!;data={asset_id:asset,explanation:asset==='GATE_A4'?'213 passengers ≥ critical threshold 180':'All signals healthy',verification:'verified',sensors:['pax_count','co2_ppm','hvac_temp_c','flight_status','jet_bridge_status'].map(metric=>({metric,value_num:213,value_str:null,warn:120,crit:180,status:'crit'})),rule:'Worst governed severity',rule_mode:'canonical_sql_replay',run_id:run,push_id:'push119',step:119,delta_versions:{sensor_readings:12},details:{rule_id:'contract'}};}
  else data={audit:{push_id:'push119',step:119},labels:metadata.labels,cameras:metadata.cameras,legend:{colours:{ok:'#22C55E',warn:'#F59E0B',crit:'#EF4444'},thresholds:[]},image_type:'Heatmap preview'};
  await route.fulfill({json:data});
 });
});
test('tight provenance, accessible selection, geometry picking and explicit comparison',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('#explanation')).toContainText('213 passengers ≥ critical threshold 180');
 await expect(page.locator('#sensors tr')).toHaveCount(5);
 await expect(page.locator('#provenance-details')).not.toHaveAttribute('open','');
 await expect(page.locator('#compare')).toHaveAttribute('href',/compare-runs.*aaaaaaaa.*bbbbbbbb/);
 await page.locator('#gate-diagnostics > summary').click();
 await page.getByRole('button',{name:'Explain A1',exact:true}).click();
 await expect(page.locator('#gate-title')).toContainText('A1');
 await page.getByRole('button',{name:'Gate A4 close-up'}).click();
 const canvas=page.locator('canvas'),box=(await canvas.boundingBox())!;
 await canvas.click({position:{x:box.width/2,y:box.height/2}});
 await expect(page.locator('#gate-title')).toContainText('A4');
});
test('older same-run page cannot override the final scrub selection',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await page.locator('#timeline').fill('10');await page.locator('#timeline').dispatchEvent('input');
 await page.locator('#timeline').fill('100');await page.locator('#timeline').dispatchEvent('input');
 await expect(page.locator('#step')).toHaveText('Minute 100 / 119');
 await page.waitForTimeout(1000);
 await expect(page.locator('#step')).toHaveText('Minute 100 / 119');
});

test('selector shows durations and disables incomplete audited runs',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('#run option').filter({hasText:'120 min'})).toHaveCount(2);
 await expect(page.locator('#run option').filter({hasText:'replay unavailable'})).toBeDisabled();
});

test('missing replay clears old evidence and prevents requests with the previous replay',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('#sensors tr')).toHaveCount(5);
 const requests:string[]=[];
 page.on('request',r=>{if(r.url().includes('/timeline?'))requests.push(r.url());});
 await page.route(`**/${ids[0]}/replays`,async route=>{
  await new Promise(resolve=>setTimeout(resolve,300));await route.fulfill({json:[]});
 });
 await page.selectOption('#run',ids[0]);
 await expect(page.locator('#play')).toBeDisabled();await expect(page.locator('#timeline')).toBeDisabled();
 await expect(page.locator('#status')).toHaveText('Audit unavailable');
 await expect(page.locator('#message')).toContainText('no complete audited replay');
 for(const id of ['metrics','health','sensors','verification','rule','source-versions','audit-details','step'])await expect(page.locator('#'+id)).toBeEmpty();
 await expect(page.locator('.label:visible')).toHaveCount(0);
 await expect(page.locator('#fallback')).toBeHidden();
 await expect(page.locator('canvas')).toHaveAttribute('data-asset-states','[]');
 expect(requests).toHaveLength(0);
 await page.selectOption('#run',ids[1]);await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('#sensors tr')).toHaveCount(5);await expect(page.locator('#play')).toBeEnabled();
});

test('missing replay id has an actionable error without retaining old evidence',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await page.route(`**/${ids[0]}/timeline?**`,r=>r.fulfill({status:404,json:{error:'REPLAY_NOT_FOUND'}}));
 await page.selectOption('#run',ids[0]);
 await expect(page.locator('#message')).toContainText('choose another available run');
 await expect(page.locator('#status')).toHaveText('Audit unavailable');
 await expect(page.locator('#metrics')).toBeEmpty();await expect(page.locator('#source-versions')).toBeEmpty();
 await expect(page.locator('#play')).toBeDisabled();
});


test('refresh discovers published runs and preserves the active replay on failure', async ({page}) => {
 await page.goto('/');
 await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 const selected = await page.locator('#run').inputValue();
 const initialIdentity = await page.locator('#identity').textContent();
 const published = [selected, 'd'.repeat(32)];
 await page.route('**/api/runs', route => route.fulfill({json:published.map(run_id => ({
  run_id, scenario:'delay_A4',run_name:'Newly published run',minutes:120,
  run_url:'http://mlflow.invalid/run/'+run_id,replay_available:true,comparison:{url:null},
 }))}));
 await page.getByRole('button',{name:'Refresh data',exact:true}).click();
 await expect(page.locator('#run option')).toHaveCount(3);
 await expect(page.locator('#run')).toHaveValue(selected);
 await expect(page.locator('#identity')).toHaveText(initialIdentity!);
 await page.route('**/api/runs', route => route.fulfill({status:503,json:{message:'Temporary outage'}}));
 await page.getByRole('button',{name:'Refresh data',exact:true}).click();
 await expect(page.locator('#message')).toContainText('Refresh failed');
 await expect(page.locator('#run')).toHaveValue(selected);
 await expect(page.getByRole('button',{name:'Refresh data',exact:true})).toBeEnabled();
});
