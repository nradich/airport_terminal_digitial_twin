import {test,expect} from '@playwright/test';
import {createHash} from 'node:crypto';
const hash=(buffer:Buffer)=>createHash('sha256').update(buffer).digest('hex');

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
 await page.selectOption('#run','5767b836d78146fdab7d786a1795f8c7');
 await expect(page.locator('#identity')).toContainText('5767b836d78146fdab7d786a1795f8c7');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
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
 await expect(page.locator('#mlflow')).toHaveAttribute('href',/7a617dc8b34b41f98b02725e04db4944/);
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
 await page.route('**/5767b836d78146fdab7d786a1795f8c7/replays',async route=>{const response=await route.fetch();await new Promise(resolve=>setTimeout(resolve,1500));await route.fulfill({response});});
 await page.selectOption('#run','5767b836d78146fdab7d786a1795f8c7');
 await page.selectOption('#run','7a617dc8b34b41f98b02725e04db4944');
 await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('#identity')).toContainText('7a617dc8b34b41f98b02725e04db4944');
 await expect(page.locator('#metrics')).toContainText('peak_pax_A4: 213');
});

test('pause during scenario blend settles exact colours and audit identity',async({page})=>{
 await page.goto('/');await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('#metrics')).toContainText('peak_pax_A4: 213');
 const canvas=page.locator('canvas');
 await page.selectOption('#run','5767b836d78146fdab7d786a1795f8c7');
 await expect(canvas).toHaveAttribute('data-blending','true');
 await page.getByRole('button',{name:'Pause',exact:true}).click();
 await expect(canvas).toHaveAttribute('data-blending','false');
 await expect(page.getByRole('button',{name:'Play',exact:true})).toBeVisible();
 await expect(page.locator('#status')).toHaveText('Unity Catalog connected');
 await expect(page.locator('#identity')).toContainText('5767b836d78146fdab7d786a1795f8c7');
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

