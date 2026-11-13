import {test,expect} from '@playwright/test';
import {createHash} from 'node:crypto';
let baselineId:string,delayId:string,longRunId:string;
test.beforeAll(async({request})=>{const rows=await (await request.get('/api/runs')).json();const paired=rows.find((r:any)=>r.comparison?.baseline_run_id);if(!paired)throw new Error('Publish an explicit filming pair first');baselineId=paired.comparison.baseline_run_id;delayId=paired.comparison.delay_run_id;longRunId=rows.find((r:any)=>r.minutes===120)?.run_id;});
const hash=(buffer:Buffer)=>createHash('sha256').update(buffer).digest('hex');
test.afterEach(async({context})=>{for(const page of context.pages())await page.unrouteAll({behavior:'ignoreErrors'});await context.unrouteAll({behavior:'ignoreErrors'});});

test('live GLB has ten labels and independent governed colours, orbit and presets',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('.label')).toHaveCount(10);
 const canvas=page.locator('canvas');
 const rows=JSON.parse((await canvas.getAttribute('data-asset-states'))!);
 expect(rows.find((r:any)=>r.asset_id==='GATE_A4')).toMatchObject({status:'crit',colour:'#ef4444'});
 expect(rows.find((r:any)=>r.asset_id==='GATE_A1').colour).toBe('#22c55e');
 const before=hash(await canvas.screenshot());const box=(await canvas.boundingBox())!;
 await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+120,box.y+box.height/2+50,{steps:10});await page.mouse.up();
 await expect.poll(async()=>hash(await canvas.screenshot())).not.toBe(before);
 await page.getByRole('button',{name:'Gate A4 close-up'}).click();await expect.poll(async()=>hash(await canvas.screenshot())).not.toBe(before);
 await page.selectOption('#run',baselineId);
 await expect(page.locator('#identity')).toContainText(baselineId);await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 const baseline=JSON.parse((await canvas.getAttribute('data-asset-states'))!);
 expect(baseline.find((r:any)=>r.asset_id==='GATE_A4').colour).toBe('#22c55e');
});

test('model failure displays matching PNG and missing image is explicit',async({page})=>{
 await page.route('**/model.glb',r=>r.abort());await page.goto('/');
 await expect(page.locator('#fallback')).toBeVisible();
 await expect(page.locator('#message')).toContainText('Heatmap preview');
 await expect.poll(()=>page.locator('#fallback').evaluate((e:HTMLImageElement)=>e.naturalWidth)).toBeGreaterThan(100);
 await page.route('**/frame.png',r=>r.abort());await page.reload();
 await expect(page.locator('#message')).toHaveText('Frame unavailable for this publication');
});

test('WebGL unavailable uses image mode',async({page})=>{
 await page.addInitScript(()=>{HTMLCanvasElement.prototype.getContext=(()=>null) as any;});
 await page.goto('/');await expect(page.locator('#fallback')).toBeVisible();
 await expect(page.locator('#message')).toContainText('Heatmap preview');
});

test('audited scrub and replay use exact MLflow steps and immutable push identities',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('#mode')).toHaveText('Audited replay');
 await expect(page.locator('#metrics')).toContainText('peak_pax_A4: 213');
 const push=await page.locator('#identity').textContent();
 await page.locator('#timeline').fill('10');await page.locator('#timeline').dispatchEvent('input');
 await expect(page.locator('#step')).toHaveText('Minute 10 / 59');
 await expect(page.locator('#identity')).not.toHaveText(push!);
 await expect(page.locator('#metrics')).not.toContainText('peak_pax_A4: 213');
 await page.getByRole('button',{name:'Play',exact:true}).click();
 await expect(page.locator('#step')).not.toHaveText('Minute 10 / 59');
 await page.getByRole('button',{name:'Pause',exact:true}).click();
 await expect(page.locator('#mlflow')).toHaveAttribute('href',new RegExp(delayId));
});

test('unavailable historical version stops SQL replay and offers exact image',async({page})=>{
 await page.route('**/timeline?**',r=>r.fulfill({status:410,contentType:'application/json',body:JSON.stringify({error:'AUDIT_VERSION_UNAVAILABLE'})}));
 await page.goto('/');await expect(page.locator('#fallback')).toBeVisible();
 await expect(page.locator('#message')).toContainText('AUDIT_VERSION_UNAVAILABLE');
 await expect(page.locator('#metrics')).toBeEmpty();
 await page.locator('#timeline').fill('10');await page.locator('#timeline').dispatchEvent('input');
 await expect(page.locator('#step')).toHaveText('Minute 10 / 59');
 await expect.poll(()=>page.locator('#fallback').evaluate((e:HTMLImageElement)=>e.naturalWidth)).toBeGreaterThan(100);
});

test('late scenario responses cannot overwrite selected run',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await page.route(`**/${baselineId}/replays`,async route=>{const response=await route.fetch();await new Promise(resolve=>setTimeout(resolve,1500));await route.fulfill({response});});
 await page.selectOption('#run',baselineId);
 await page.selectOption('#run',delayId);
 await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('#identity')).toContainText(delayId);
 await expect(page.locator('#metrics')).toContainText('peak_pax_A4: 213');
});

test('pause during scenario blend settles exact colours and audit identity',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('#metrics')).toContainText('peak_pax_A4: 213');
 const canvas=page.locator('canvas');
 await page.selectOption('#run',baselineId);
 await expect(canvas).toHaveAttribute('data-blending','true');
 await page.getByRole('button',{name:'Pause',exact:true}).click();
 await expect(canvas).toHaveAttribute('data-blending','false');
 await expect(page.getByRole('button',{name:'Play',exact:true})).toBeVisible();
 await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('#identity')).toContainText(baselineId);
 await expect(page.locator('#metrics')).toContainText('peak_pax_A4: 126');
 await expect(page.locator('#step')).toHaveText('Minute 59 / 59');
 const rows=JSON.parse((await canvas.getAttribute('data-asset-states'))!);
 expect(rows.find((r:any)=>r.asset_id==='GATE_A4')).toMatchObject({status:'ok',colour:'#22c55e'});
 expect(rows.find((r:any)=>r.asset_id==='GATE_A1').colour).toBe('#22c55e');
});

test('resize updates the WebGL canvas to the stage size',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('.label')).toHaveCount(10);
 const before=await page.locator('#stage').evaluate(el=>{
  const canvas=el.querySelector('canvas') as HTMLCanvasElement;
  return {stageW:el.clientWidth,stageH:el.clientHeight,canvasW:canvas.width,canvasH:canvas.height,cssW:canvas.clientWidth,cssH:canvas.clientHeight};
 });
 expect(before.cssW).toBe(before.stageW);
 expect(before.cssH).toBe(before.stageH);
 await page.setViewportSize({width:900,height:700});
 await expect.poll(async()=>page.locator('#stage').evaluate(el=>(el.querySelector('canvas') as HTMLCanvasElement).clientWidth)).not.toBe(before.cssW);
 const mid=await page.locator('#stage').evaluate(el=>{
  const canvas=el.querySelector('canvas') as HTMLCanvasElement;
  return {stageW:el.clientWidth,stageH:el.clientHeight,cssW:canvas.clientWidth,cssH:canvas.clientHeight,labelCount:el.querySelectorAll('.label').length};
 });
 expect(mid.cssW).toBe(mid.stageW);
 expect(mid.cssH).toBe(mid.stageH);
 expect(mid.labelCount).toBe(10);
 await page.setViewportSize({width:1440,height:900});
 await expect.poll(async()=>page.locator('#stage').evaluate(el=>(el.querySelector('canvas') as HTMLCanvasElement).clientWidth)).toBeGreaterThan(mid.cssW);
 const after=await page.locator('#stage').evaluate(el=>{
  const canvas=el.querySelector('canvas') as HTMLCanvasElement;
  return {stageW:el.clientWidth,stageH:el.clientHeight,cssW:canvas.clientWidth,cssH:canvas.clientHeight};
 });
 expect(after.cssW).toBe(after.stageW);
 expect(after.cssH).toBe(after.stageH);
 await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('.label')).toHaveCount(10);
});

test('live publication explains five SQL sensor rows and comparison opens the exact pair',async({page,context})=>{
 await context.route('http://localhost:5000/**',async route=>{const response=await route.fetch({url:route.request().url().replace('localhost:5000','mlflow:5000')});await route.fulfill({response});});
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('#explanation')).toHaveText('213 passengers ≥ critical threshold 180');
 await expect(page.locator('#sensors tr')).toHaveCount(5);
 await expect(page.locator('#provenance-details')).not.toHaveAttribute('open','');
 await page.locator('#gate-diagnostics > summary').click();
 await page.getByRole('button',{name:'Explain A1',exact:true}).click();
 await expect(page.locator('#explanation')).toContainText('healthy');
 await page.getByRole('button',{name:'Explain A4',exact:true}).click();
 await expect(page.locator('#explanation')).toContainText('213 passengers');
 const popupPromise=context.waitForEvent('page');await page.locator('#compare').click();const popup=await popupPromise;
 await expect(popup).toHaveURL(/compare-runs/);
 expect(decodeURIComponent(popup.url())).toContain(baselineId);
 expect(decodeURIComponent(popup.url())).toContain(delayId);
 await expect(popup.getByText('peak_pax_A4',{exact:true}).first()).toBeVisible({timeout:30000});
 await expect(popup.locator('body')).toContainText('126');await expect(popup.locator('body')).toContainText('213');
 await popup.screenshot({path:'.local/filming/mlflow-comparison.png'});
});

test('live 120-step stale scrub does not roll back a later cached selection',async({page})=>{
 test.skip(!longRunId,'Publish the separate 120-step fixture first');
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await page.route('**/timeline?**',async route=>{if(route.request().url().includes('start_step=0')&&route.request().url().includes(longRunId)){const response=await route.fetch();await new Promise(resolve=>setTimeout(resolve,1500));await route.fulfill({response});}else await route.continue();});
 await page.selectOption('#run',longRunId);await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await page.locator('#timeline').fill('10');await page.locator('#timeline').dispatchEvent('input');
 await page.locator('#timeline').fill('100');await page.locator('#timeline').dispatchEvent('input');
 await expect(page.locator('#step')).toHaveText('Minute 100 / 119');await page.waitForTimeout(2200);
 await expect(page.locator('#step')).toHaveText('Minute 100 / 119');
});
