// Synthetic HTTP contract tests; the live project separately tests Delta and MLflow.
import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const ids=['a'.repeat(32),'b'.repeat(32)];
let metadata:any;
test.beforeAll(async()=>{metadata=JSON.parse(await readFile('.local/contracts/metadata.json','utf8'));});
test.beforeEach(async({page})=>{
 await page.route('**/api/**',async route=>{
  const url=new URL(route.request().url()),delayed=!url.pathname.includes(ids[0]),run=ids[delayed?1:0];
  const states=metadata.labels.map((label:any)=>({asset_id:label.asset_id,status:delayed&&label.asset_id==='GATE_A4'?'crit':'ok',colour:delayed&&label.asset_id==='GATE_A4'?'#EF4444':'#22C55E',pax_count:delayed?213:6}));
  const pair=`http://mlflow.invalid/#/compare-runs?runs=${encodeURIComponent(JSON.stringify(ids))}`;
  let data:any;
  if(url.pathname==='/api/runs')data=ids.map((id,i)=>({run_id:id,scenario:i?'delay_A4':'baseline',run_name:'Contract fixture',minutes:120,push_id:'push',run_url:'http://mlflow.invalid/run/'+id,comparison:{url:pair,reason:null}}));
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
