const http = require('http');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = __dirname;
const PORT = process.env.PORT || 8987;
const TYPES = { '.html':'text/html; charset=utf-8', '.css':'text/css', '.js':'text/javascript', '.json':'application/json',
  '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.webp':'image/webp', '.svg':'image/svg+xml',
  '.ico':'image/x-icon', '.mp3':'audio/mpeg' };

// Rebuild the PFP layers/manifest whenever the kit changes (drop a PNG into kit/<layer>/, reload the page).
const KIT = path.join(ROOT, 'kit');
let lastSig = '';
function pfpBuild() {
  try {
    const sig = fs.readdirSync(KIT).filter(d => fs.statSync(path.join(KIT, d)).isDirectory()).map(d =>
      fs.readdirSync(path.join(KIT, d)).map(f => f + ':' + fs.statSync(path.join(KIT, d, f)).mtimeMs).join(',')).join('|');
    if (sig === lastSig) return;
    lastSig = sig;
    console.log(execFileSync('python3', [path.join(ROOT, 'pfp-build.py')], { encoding: 'utf8' }).trim());
  } catch (e) { console.error('pfp-build failed:', e.message); }
}
pfpBuild();

http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/') p = '/index.html';
  if (p === '/assets/pfp/manifest.json') pfpBuild();
  const file = path.join(ROOT, path.normalize(p).replace(/^(\.\.[/\\])+/, ''));
  if (!file.startsWith(ROOT)) { res.writeHead(403); return res.end('forbidden'); }
  fs.stat(file, (err, st) => {
    if (err || !st.isFile()) { res.writeHead(404); return res.end('not found'); }
    const type = TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream';
    const range = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range || '');
    if (range) {   // audio seeking
      const start = range[1] ? +range[1] : 0, end = range[2] ? Math.min(+range[2], st.size - 1) : st.size - 1;
      res.writeHead(206, { 'Content-Type': type, 'Content-Range': `bytes ${start}-${end}/${st.size}`, 'Accept-Ranges': 'bytes', 'Content-Length': end - start + 1 });
      return fs.createReadStream(file, { start, end }).pipe(res);
    }
    res.writeHead(200, { 'Content-Type': type, 'Content-Length': st.size, 'Accept-Ranges': 'bytes', 'Cache-Control': 'no-store' });
    fs.createReadStream(file).pipe(res);
  });
}).listen(PORT, () => console.log('hoodbaddies on http://localhost:' + PORT));
