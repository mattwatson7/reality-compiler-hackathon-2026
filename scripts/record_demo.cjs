/* Optional production tool. Uses an already installed Playwright; installs nothing.
   NODE_PATH/PLAYWRIGHT_BROWSERS_PATH and DEMO_CHROMIUM select existing runtimes.
   DEMO_URL must point to the explicitly isolated, paid-disabled loopback server.
   No page content, results or provenance is altered for filming. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'output/demo-production');
const final = path.join(root, 'docs/submission-final');
const base = process.env.DEMO_URL || 'http://127.0.0.1:8002';
assert(['127.0.0.1', 'localhost'].includes(new URL(base).hostname));
const run = process.env.DEMO_RUN;
assert(run, 'Set DEMO_RUN to a freshly imported captured-evidence review.');
const scenes = JSON.parse(fs.readFileSync(path.join(final, 'narration.json')));
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
fs.mkdirSync(output, { recursive: true });
fs.mkdirSync(path.join(final, 'screenshots'), { recursive: true });

(async () => {
  const browser = await chromium.launch({headless:true, executablePath:process.env.DEMO_CHROMIUM});
  const context = await browser.newContext({viewport:{width:1440,height:810},
    recordVideo:{dir:path.join(output,'raw'),size:{width:1440,height:810}}, reducedMotion:'reduce'});
  // Refuse any browser request outside the local application during production.
  await context.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin
    ? route.continue() : route.abort());
  const page = await context.newPage();
  const started = Date.now();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  const events = [];
  const json = async url => {const r=await context.request.get(base+url);assert(r.ok());return r.json();};
  const health = await json('/api/health');
  assert.equal(health.meta.paid_inference_enabled,false);
  const ledger = await json('/api/costs');
  const job = await json('/api/jobs/'+run);
  assert.equal(job.execution_mode,'offline_capture_review');
  assert.equal(job.footage_origin,'generated');
  assert.equal(job.result.verdict,'PASS');
  const cvRun=process.env.DEMO_CV_RUN;
  assert(cvRun,'Set DEMO_CV_RUN to the fresh local-CV upload run.');
  const cvJob=await json('/api/jobs/'+cvRun);
  assert.equal(cvJob.status,'completed');
  assert.equal(cvJob.footage_origin,'generated');
  assert.equal(cvJob.mode,'local_cv');
  // A user-declared origin alone cannot establish that pixels are generated.
  // Require the exact generated source already verified by capture import.
  assert.equal(cvJob.media_metadata.source_sha256,job.media_metadata.source_sha256);
  assert.deepEqual(cvJob.inference_usage,[]);
  const historyBefore = await json('/api/jobs/'+run+'/evaluations');
  await page.goto(base+'/?run='+run);
  await page.getByRole('heading',{name:'One recording. Different requirements.'}).waitFor();
  await page.getByLabel('Second evaluation').selectOption('0');
  const video=page.getByLabel('Verification video');
  await video.evaluate(v=>new Promise(resolve=> {if(v.readyState>=2)resolve();else v.addEventListener('loadeddata',resolve,{once:true});}));
  const top = async locator => locator.evaluate(e=>e.scrollIntoView({block:'start'}));
  const snap = async id => page.screenshot({path:path.join(final,'screenshots',id+'.jpg'),type:'jpeg',quality:92});
  async function shot(id,action) {
    const spec=scenes.find(s=>s.id===id);
    const begin=(Date.now()-started)/1000;
    await action();
    await snap(id);
    const elapsed=(Date.now()-started)/1000-begin;
    // WAVE duration is supplied by the renderer's timing preparation.
    const times=JSON.parse(fs.readFileSync(path.join(output,'durations.json')));
    await sleep(Math.max(0,(times[id]-elapsed)*1000));
    events.push({id,title:spec.title,start:begin,end:(Date.now()-started)/1000});
    console.log('Recorded '+id);
  }
  await shot('opening',async()=>{await top(page.locator('.intro'));});
  await shot('program',async()=>{await top(page.locator('main > .program'));await page.getByRole('region',{name:'Program events',exact:true}).scrollIntoViewIfNeeded();});
  // Selection is inserted as an explicitly labeled historical still during editing.
  await shot('selection',async()=>{await top(page.locator('.workspace'));});
  await shot('tracking',async()=>{await top(page.locator('.workspace'));await video.evaluate(async v=>{v.currentTime=0;await v.play();});await sleep(4500);await page.getByLabel('Video playhead').fill('0.75');});
  await shot('evidence',async()=>{
    await top(page.locator('.verdict-panel'));
    await page.getByText('Saved supporting frames (10)',{exact:true}).click();
    await page.getByText('Saved supporting frames (11)',{exact:true}).click();
    await page.locator('.evidence-list a').filter({hasText:'object_entered_region: object2'}).click();
    await sleep(1200);await top(page.locator('.evidence-list'));
  });
  // Source inspection of a separate genuine local-CV application run is prepared
  // by a prior UI upload/selection. Never graft a mapping onto historical Meta data.
  await shot('source',async()=>{
    await page.goto(base+'/?run='+cvRun);
    await page.getByText('Inspect original source frame',{exact:true}).click();
    await page.getByLabel('Video playhead').fill('2.1');
    await page.getByRole('button',{name:'Inspect source at playhead'}).click();
    await top(page.locator('.source-attribution'));
    await page.getByAltText(/Original decoded source frame/).waitFor();
  });
  await page.goto(base+'/?run='+run);
  await page.getByLabel('Second evaluation').selectOption('0');
  const revisions=[];
  async function revise(text,expected) {
    const field=page.getByLabel('Revised procedure',{exact:true});
    await field.fill('');await field.pressSequentially(text,{delay:25});
    const response=page.waitForResponse(r=>r.url().endsWith('/evaluations')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Evaluate same evidence',exact:true}).click();
    const r=await response;assert(r.ok());const body=await r.json();
    assert.equal(body.result.verdict,expected);assert.equal(body.reuse_status,'reused');
    assert.deepEqual(body.inference_usage,[]);revisions.push(body);
    await page.getByLabel('Evidence reuse verified').waitFor();
  }
  await shot('reverse',async()=>{
    await top(page.getByRole('region',{name:'Compare procedures',exact:true}));
    await revise('Move the cup into the visible marked region before moving the blue block into that region.','FAIL');
  });
  await shot('comparison',async()=>{await top(page.locator('.comparison-selectors'));});
  await shot('unknown',async()=>{
    await top(page.getByRole('region',{name:'Compare procedures',exact:true}));
    await revise('Move the blue block into the visible marked region before moving the cup into that region. Ensure the cup is sterile.','UNKNOWN');
    await top(page.locator('.comparison-selectors'));
  });
  await shot('provenance',async()=>{
    await top(page.locator('.comparison-selectors'));
  });
  await shot('closing',async()=>{
    await top(page.locator('.comparison-selectors'));
  });
  const history=await json('/api/jobs/'+run+'/evaluations');
  assert.equal(history.length,historyBefore.length+2);
  assert.equal(new Set([history[0],...revisions].map(h=>h.evidence_fingerprint)).size,1);
  assert.deepEqual(await json('/api/costs'),ledger);
  assert.equal((await json('/api/jobs/'+run)).result.verdict,'PASS');
  await page.setViewportSize({width:390,height:844});
  await top(page.locator('.comparison-selectors'));
  await snap('mobile-comparison');
  const widths=await page.evaluate(()=>({width:innerWidth,document:document.documentElement.scrollWidth}));
  assert(widths.document<=widths.width,'Mobile horizontal overflow');
  await page.setViewportSize({width:1440,height:810});
  fs.writeFileSync(path.join(final,'browser-verification.json'),JSON.stringify({date:'2026-10-28',run,cvRun,health,ledger,
    initial_history_count:historyBefore.length,final_history_count:history.length,mobile:widths,errors,
    original:history[0],revisions,job_provenance:job.provenance,legacy_source_mapping:job.media_metadata.source_timing??null},null,2));
  await context.close();
  const videoPath=await page.video().path();
  fs.writeFileSync(path.join(output,'recording.json'),JSON.stringify({video:videoPath,started,events},null,2));
  await browser.close();
  assert.deepEqual(errors,[]);
  console.log('Saved real browser recording and verified API exports.');
})().catch(e=>{console.error(e);process.exit(1);});
