import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',workers:1,timeout:90000,expect:{timeout:30000},use:{baseURL:process.env.TWIN_TEST_URL||'http://twin-app:8000',viewport:{width:1440,height:900},launchOptions:{args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']},screenshot:'only-on-failure'}});

