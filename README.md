# HOOD BADDIES

Static site (no build step) + on-site PFP generator. Robinhood Chain.

- `node serve.js` → http://localhost:8987 (re-runs `pfp-build.py` whenever `kit/` changes)
- `kit/<Nth layer>/*.png` — source layers, 1254² with real alpha ("1st" = top-most, "11th" = background).
  Drop a PNG in, reload: it shows up in the generator.
- `python3 pfp-build.py` — kit → `assets/pfp/` (WebP layers, JPG backgrounds, thumbs, `manifest.json`),
  `assets/baddies/` (16 pre-rendered baddies for hero/squad) and `assets/og.jpg`. **Run before deploying.**
- Launch constants at the bottom of `index.html`: `TICKER`, `CA`, `X`, `TG` (empty = hidden). Buy link derives from `CA`.
- Deploy: `vercel deploy --prod --yes` (`kit/` is excluded by `.vercelignore`).
