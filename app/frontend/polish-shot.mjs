import {chromium, expect} from '@playwright/test';
import {mkdir, writeFile} from 'node:fs/promises';

await mkdir('.local/polish', {recursive: true});
const browser = await chromium.launch({
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
});
const page = await browser.newPage({viewport: {width: 1920, height: 1080}});
await page.goto(process.env.TWIN_TEST_URL || 'http://twin-app:8000');
await expect(page.locator('#status')).toHaveText('Unity Catalog connected', {timeout: 30000});
await page.screenshot({path: '.local/polish/overview-34.png', fullPage: false});
await page.getByRole('button', {name: 'Gate A4 close-up'}).click();
await page.waitForTimeout(400);
await page.screenshot({path: '.local/polish/a4-closeup.png', fullPage: false});
const evidence = {
  message: await page.locator('#message').boundingBox(),
  title: await page.locator('h1').boundingBox(),
  statusText: await page.locator('#status').innerText(),
  messageText: await page.locator('#message').innerText(),
  labelCount: await page.locator('.label').count(),
};
evidence.messageNearTitle =
  evidence.message && evidence.title
    ? Math.abs(evidence.message.y - evidence.title.y) < 90
    : false;
await writeFile('.local/polish/evidence.json', JSON.stringify(evidence, null, 2));
console.log(JSON.stringify(evidence));
await browser.close();
