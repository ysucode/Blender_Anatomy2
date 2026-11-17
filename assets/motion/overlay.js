// Identity overlay (content-studio/style-sheet.md): title + step chip + orange underline (anime.js),
// word-by-word captions (GSAP). Frame-by-frame via seek -> transparent PNGs.
// Worked example: replace the title, chips and cue times. usage: node overlay.js <cues.json> <outdir> [fps=24] [seconds=10]
const path = require('path'), fs = require('fs'), url = require('url');
const root = path.join(__dirname, '..', '..');            // content-studio (fonts live in its node_modules)
const V = path.join(require('os').homedir(), '.claude/skills/Blender_Anatomy2/vendor');
const { chromium } = require(path.join(V, 'node_modules/playwright-core'));
const [cuesFile, outDir, fpsA, secA] = process.argv.slice(2);
const fps = +(fpsA || 24), secs = +(secA || 10);
fs.mkdirSync(outDir, { recursive: true });
const F = path.join(root, 'node_modules/@fontsource/ibm-plex-sans-arabic/files');
const ff = (w, sub) => url.pathToFileURL(path.join(F, `ibm-plex-sans-arabic-${sub}-${w}-normal.woff2`)).href;
const msp = path.join(process.env.LOCALAPPDATA, 'ms-playwright');
const newest = fs.readdirSync(msp).filter(d => /^chromium-\d+$/.test(d)).sort((a, b) => +b.split('-')[1] - +a.split('-')[1])[0];
const exe = path.join(msp, newest, fs.readdirSync(path.join(msp, newest)).find(d => d.startsWith('chrome')), 'chrome.exe');
const cues = JSON.parse(fs.readFileSync(cuesFile, 'utf8'));

const html = `<!doctype html><html dir="rtl"><head><meta charset="utf-8">
<script src="${url.pathToFileURL(path.join(V, 'gsap/dist/gsap.min.js')).href}"></script>
<script src="${url.pathToFileURL(path.join(V, 'animejs/dist/bundles/anime.umd.min.js')).href}"></script>
<style>
@font-face{font-family:Plex;font-weight:700;src:url(${ff(700, 'arabic')})}
@font-face{font-family:Plex;font-weight:700;src:url(${ff(700, 'latin')});unicode-range:U+0000-00FF}
:root{--bg:#FFFCF2;--line:#CCC5B9;--ink2:#403D39;--ink:#252422;--acc:#EB5E28}
html,body{margin:0;width:1080px;height:1920px;background:transparent;overflow:hidden;font-family:Plex;font-weight:700}
.chip{position:absolute;left:0;right:0;top:268px;display:flex;justify-content:center}
.chip span.box{font-size:36px;line-height:1.3;color:var(--ink2);padding:2px 18px 6px;border:2px solid var(--line);border-radius:999px;background:var(--bg);opacity:0}
.chip .w{display:inline-block}
h1{position:absolute;left:0;right:0;top:318px;margin:0;text-align:center;font-size:68px;line-height:1.3;color:var(--ink)}
svg{position:absolute;inset:0}
.cap{position:absolute;left:0;right:0;bottom:${1920 - 1320}px;display:flex;justify-content:center;opacity:0}
.pill{font-size:56px;line-height:1.3;color:var(--bg);background:var(--ink);padding:8px 28px 14px;border-radius:24px;white-space:nowrap;max-width:680px}
.w{display:inline-block;opacity:0}
.pill .w{display:none}
.key{border-radius:12px;padding:0 10px}
</style></head><body>
<div class="chip" id="c1"><span class="box"><span class="w">الخطوة</span> <span class="w">01</span> <span class="w">·</span> <span class="w">المشتقة</span></span></div>
<div class="chip" id="c2"><span class="box"><span class="w">الخطوة</span> <span class="w">02</span> <span class="w">·</span> <span class="w">التكامل</span></span></div>
<h1>المشتقة والتكامل</h1>
<svg width="1080" height="1920"><path id="ul" d="M760 414 C640 422 470 410 320 418" fill="none" stroke="#EB5E28" stroke-width="6" stroke-linecap="round"/></svg>
<div id="caps"></div></body></html>`;

(async () => {
  const b = await chromium.launch({ executablePath: exe });
  const pg = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  const page = path.join(outDir, '..', '_overlay.html');
  fs.writeFileSync(page, html);
  await pg.goto(url.pathToFileURL(page).href);
  await pg.evaluate(async () => { await document.fonts.load('700 56px Plex', 'مشتقة 01'); await document.fonts.ready; });
  const info = await pg.evaluate(cues => {
    // ---- GSAP: captions, each word 0.05 s before it is spoken; one key word per line on orange
    gsap.ticker.remove(gsap.updateRoot);
    const tl = gsap.timeline({ paused: true });
    const box = document.getElementById('caps');
    for (const c of cues.chunks) {
      const d = document.createElement('div'); d.className = 'cap';
      d.innerHTML = `<div class="pill">${c.words.map((w, i) => `<span class="w${i === c.key ? ' key' : ''}">${w.w}</span>`).join(' ')}</div>`;
      box.appendChild(d);
      tl.set(d, { opacity: 1 }, c.words[0].s - .05);
      d.querySelectorAll('.w').forEach((el, i) => {
        const at = c.words[i].s - .05;
        tl.set(el, { display: 'inline-block' }, at);              // the pill grows word by word
        tl.fromTo(el, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: .3, ease: 'power3.out', immediateRender: false }, at);
        if (i === c.key) tl.to(el, { backgroundColor: '#EB5E28', color: '#252422', duration: .12 }, at);
      });
      tl.to(d, { opacity: 0, duration: .15, ease: 'power2.in' }, c.end);
    }
    // ---- anime.js: the one orange line (draws under the title, retracts and redraws on each step),
    //      and the step chip arriving word by word with a stagger
    const [ul] = anime.svg.createDrawable('#ul');
    const at = anime.createTimeline({ autoplay: false });
    const step = (sel, t) => at.add(`${sel} .box`, { opacity: [0, 1], duration: 200, ease: 'outQuad' }, t).add(`${sel} .w`, { opacity: [0, 1], translateY: [14, 0], duration: 400,
                                               ease: 'outCubic', delay: anime.stagger(90) }, t);
    at.add('#c2', { opacity: 0, duration: 1 }, 0);
    at.add('#c1 .box', { opacity: 0, duration: 1 }, 0);
    at.add(ul, { draw: ['0 0', '0 1'], duration: 700, ease: 'inOutQuad' }, 150);
    step('#c1', 250);
    at.add('#c1', { opacity: [1, 0], translateY: [0, -10], duration: 250, ease: 'inQuad' }, cues.i_start * 1000 - 250);
    at.add(ul, { draw: ['0 1', '1 1'], duration: 300, ease: 'inQuad' }, cues.i_start * 1000 - 300);
    at.add('#c2', { opacity: 1, duration: 1 }, cues.i_start * 1000);
    step('#c2', cues.i_start * 1000);
    at.add(ul, { draw: ['0 0', '0 1'], duration: 700, ease: 'inOutQuad' }, cues.i_start * 1000 + 100);
    window.__seek = t => { tl.seek(t, false); at.seek(t * 1000); };
    return gsap.version;
  }, cues);
  console.log('gsap', info);
  for (let i = 0; i < Math.round(fps * secs); i++) {
    await pg.evaluate(t => window.__seek(t), i / fps);
    await pg.screenshot({ path: path.join(outDir, String(i).padStart(4, '0') + '.png'), omitBackground: true });
  }
  await b.close();
  console.log('frames', Math.round(fps * secs));
})();
