// Caption strip frames (transparent 1080x200) with GSAP, one PNG per film frame, deterministic via seek.
// Run by captions.py:  node captions.js <fps> <frames>
const path = require('path'), fs = require('fs'), url = require('url'), os = require('os');
const SKILL = path.join(os.homedir(), '.claude/skills/Blender_Anatomy2');
const { chromium } = require(path.join(SKILL, 'vendor/node_modules/playwright-core'));
const CAPS = path.join(__dirname, 'caps'), OUT = path.join(CAPS, 'f');
const fps = +process.argv[2], frames = +process.argv[3];
fs.rmSync(OUT, { recursive: true, force: true }); fs.mkdirSync(OUT, { recursive: true });
const chunks = JSON.parse(fs.readFileSync(path.join(CAPS, 'chunks.json'), 'utf8'));
const fontDir = path.join(__dirname, '../../node_modules/@fontsource/ibm-plex-sans-arabic/files');
const font = s => url.pathToFileURL(path.join(fontDir, `ibm-plex-sans-arabic-${s}-700-normal.woff2`)).href;
const msp = path.join(process.env.LOCALAPPDATA, 'ms-playwright');
const newest = fs.readdirSync(msp).filter(d => /^chromium-\d+$/.test(d)).sort((a, b) => +b.split('-')[1] - +a.split('-')[1])[0];
const exe = path.join(msp, newest, fs.readdirSync(path.join(msp, newest)).find(d => d.startsWith('chrome')), 'chrome.exe');

const html = `<!doctype html><html dir="rtl"><head><meta charset="utf-8">
<script src="${url.pathToFileURL(path.join(SKILL, 'vendor/gsap/dist/gsap.min.js')).href}"></script><style>
@font-face{font-family:Plex;font-weight:700;src:url(${font('arabic')})}
@font-face{font-family:Plex;font-weight:700;src:url(${font('latin')});unicode-range:U+0000-00FF}
html,body{margin:0;width:1080px;height:200px;background:transparent;overflow:hidden}
.cap{position:absolute;left:0;right:0;bottom:0;display:flex;justify-content:center;opacity:0}
.pill{font:700 56px/1.3 Plex;color:#FFFCF2;background:#252422;padding:8px 28px 14px;border-radius:24px;white-space:nowrap}
.pill.ai{background:#EB5E28;color:#252422}.pill.cta{font-size:62px}
.w{display:none;opacity:0}.key{border-radius:12px;padding:0 10px}
</style></head><body><div id="caps"></div></body></html>`;

(async () => {
  const b = await chromium.launch({ executablePath: exe });
  const pg = await b.newPage({ viewport: { width: 1080, height: 200 } });
  const page = path.join(CAPS, '_page.html');            // fonts from file:// need a real file page
  fs.writeFileSync(page, html);
  await pg.goto(url.pathToFileURL(page).href);
  await pg.evaluate(async () => { await document.fonts.load('700 56px Plex', 'ساعة 01'); await document.fonts.ready; });
  await pg.evaluate(chunks => {
    gsap.ticker.remove(gsap.updateRoot);                  // only seek moves time
    const tl = gsap.timeline({ paused: true }), box = document.getElementById('caps');
    for (const c of chunks) {
      const d = document.createElement('div'); d.className = 'cap';
      d.innerHTML = `<div class="pill ${c.style}">${c.words.map(w => `<span class="w${w.key ? ' key' : ''}">${w.w}</span>`).join(' ')}</div>`;
      box.appendChild(d);
      const pill = d.firstChild, spans = d.querySelectorAll('.w');
      spans.forEach(e => e.style.display = 'inline-block'); // measure the full line, shrink to the 680 px safe width
      let size = parseFloat(getComputedStyle(pill).fontSize);
      while (pill.getBoundingClientRect().width > 680 && size > 36) { size -= 2; pill.style.fontSize = size + 'px'; }
      spans.forEach(e => e.style.display = '');
      tl.set(d, { opacity: 1 }, Math.max(0, c.words[0].s - .05));
      spans.forEach((el, i) => {
        const at = Math.max(0, c.words[i].s - .05);
        tl.set(el, { display: 'inline-block' }, at);
        tl.fromTo(el, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: .3, ease: 'power3.out', immediateRender: false }, at);
        if (c.words[i].key) tl.to(el, { backgroundColor: c.style === 'ai' ? '#252422' : '#EB5E28',
                                        color: c.style === 'ai' ? '#FFFCF2' : '#252422', duration: .12 }, at);
      });
      tl.to(d, { opacity: 0, duration: .15, ease: 'power2.in' }, c.end);
    }
    window.__seek = t => { tl.seek(t, false); };          // return nothing: a returned timeline crashes the page
  }, chunks);
  for (let i = 0; i < frames; i++) {
    await pg.evaluate(t => window.__seek(t), i / fps);
    await pg.screenshot({ path: path.join(OUT, String(i).padStart(5, '0') + '.png'), omitBackground: true });
  }
  await b.close();
  console.log('caption frames', frames);
})();
