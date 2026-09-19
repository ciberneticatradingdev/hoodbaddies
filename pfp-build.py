#!/usr/bin/env python3
"""Build the PFP generator assets from the layer kit.

kit/<Nth name>/*.png  ->  assets/pfp/<layer>/<slug>.webp (+ thumbs/, manifest.json)
                          assets/baddies/*.jpg (pre-rendered gallery), assets/og.jpg

Drop a PNG (1254x1254, real alpha) into a kit folder and re-run (serve.js does it on reload).
Kit folders are numbered top-down: "1st" is the top-most layer, "11th" is the background.
"""
import hashlib, json, os, random, re, shutil, sys
from PIL import Image, ImageEnhance

ROOT = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(ROOT, 'kit')
OUT = os.path.join(ROOT, 'assets', 'pfp')
GALLERY = os.path.join(ROOT, 'assets', 'baddies')
SIZE, THUMB = 1254, 240
THUMB_FILL = (255, 200, 228)

# layer key -> kit folder keyword
KIT_DIRS = {'bg': 'background', 'body': 'body', 'eyes': 'eyes', 'brows': 'brows', 'mouth': 'mouth', 'hair': 'hairs',
            'hats': 'hats', 'glasses': 'glasses', 'top': 'top', 'items': 'items', 'overlays': 'overlays'}
# bottom -> top
DRAW_ORDER = ['bg', 'body', 'eyes', 'brows', 'mouth', 'hair', 'hats', 'glasses', 'top', 'items', 'overlays']
FIXED = ['body', 'brows']          # single-file layers, always drawn
# thumbnail crop boxes on the 1254 canvas (None = whole canvas)
CROP = {'eyes': (419, 329, 979, 889), 'mouth': (580, 580, 960, 960), 'glasses': (400, 290, 1040, 930),
        'top': (227, 454, 1027, 1254), 'items': (654, 654, 1254, 1254)}
# what the thumbnail mannequin wears under/around the previewed trait
THUMB_BASE = {'eyes': 'lime', 'mouth': 'normal', 'hair': 'straight-3', 'top': 'crop-top-1'}

LABEL_FIX = {'af': 'AF', 'lv': 'LV', 'b': 'B', 'y2k': 'Y2K', 'mcbag': 'McBag', 'iphone17': 'iPhone 17', 'bldg': 'Building',
             'amex': 'Amex', 'n': '&'}


def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def label(name):
    words = re.sub(r"[^A-Za-z0-9' ]+", ' ', name).split()
    return ' '.join(LABEL_FIX.get(w.lower(), w[:1].upper() + w[1:]) for w in words)


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s.lower())]


def kit_dir(layer):
    for d in os.listdir(KIT):
        if os.path.isdir(os.path.join(KIT, d)) and KIT_DIRS[layer] in d.lower():
            return os.path.join(KIT, d)
    return None


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()[:8]


def newer(src, dst):
    return not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst)


def main():
    os.makedirs(os.path.join(OUT, 'thumbs'), exist_ok=True)
    items, keep = {}, set()

    # 1) convert layers
    for layer in DRAW_ORDER:
        src_dir = kit_dir(layer)
        items[layer] = []
        if not src_dir:
            continue
        os.makedirs(os.path.join(OUT, layer), exist_ok=True)
        files = sorted((f for f in os.listdir(src_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))), key=natural)
        for f in files:
            stem = os.path.splitext(f)[0]
            sid = slugify(stem)
            ext = 'jpg' if layer == 'bg' else 'webp'
            rel = f'{layer}/{sid}.{ext}'
            dst = os.path.join(OUT, rel)
            src = os.path.join(src_dir, f)
            if newer(src, dst):
                im = Image.open(src)
                if im.size != (SIZE, SIZE):
                    im = im.resize((SIZE, SIZE), Image.LANCZOS)
                if layer == 'bg':
                    im.convert('RGB').save(dst, quality=86, optimize=True, progressive=True)
                else:
                    im.convert('RGBA').save(dst, 'WEBP', quality=92, method=6, exact=False)
            keep.add(rel)
            items[layer].append({'id': sid, 'label': label(stem), 'src': rel, '_kit': src})

    def img(layer, sid=None):
        pool = items[layer]
        it = next((x for x in pool if x['id'] == sid), pool[0] if pool else None)
        return Image.open(it['_kit']).convert('RGBA') if it else None

    def compose(state, size=SIZE, fill=None):
        """state: layer -> id (or None). Fixed layers are always drawn."""
        im = Image.new('RGBA', (SIZE, SIZE), (fill or (0, 0, 0)) + (255,))
        for layer in DRAW_ORDER:
            if layer in FIXED:
                x = img(layer)
            elif state.get(layer):
                x = img(layer, state[layer])
            else:
                x = None
            if x is not None:
                if x.size != (SIZE, SIZE):
                    x = x.resize((SIZE, SIZE), Image.LANCZOS)
                im = Image.alpha_composite(im, x)
        return im if size == SIZE else im.resize((size, size), Image.LANCZOS)

    # 2) thumbs
    for layer in DRAW_ORDER:
        if layer in FIXED:
            continue
        for it in items[layer]:
            rel = f'thumbs/{layer}-{it["id"]}.webp'
            dst = os.path.join(OUT, rel)
            keep.add(rel)
            it['thumb'] = rel
            if not newer(it['_kit'], dst):
                continue
            if layer == 'bg':
                t = Image.open(it['_kit']).convert('RGB')
            else:
                st = dict(THUMB_BASE)
                if layer in ('eyes', 'mouth'):
                    st.pop('hair')
                st[layer] = it['id']
                t = compose(st, fill=THUMB_FILL)
                if layer == 'overlays':   # captions are white: preview them on a dimmed baddie
                    base = ImageEnhance.Brightness(compose(dict(THUMB_BASE), fill=(60, 20, 60)).convert('RGB')).enhance(.45)
                    t = Image.alpha_composite(base.convert('RGBA'), img(layer, it['id']))
                if layer in CROP:
                    t = t.crop(CROP[layer])
                t = t.convert('RGB')
            t.resize((THUMB, THUMB), Image.LANCZOS).save(dst, 'WEBP', quality=82, method=6)

    # 3) prune files whose kit source is gone
    for layer in DRAW_ORDER + ['thumbs']:
        d = os.path.join(OUT, layer)
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f'{layer}/{f}' not in keep:
                    os.remove(os.path.join(d, f))

    # 4) pre-rendered gallery (seeded, so it only changes when the kit does)
    os.makedirs(GALLERY, exist_ok=True)
    rng = random.Random(1809)
    ids = lambda l: [x['id'] for x in items[l]]
    gallery = []
    for n in range(16):
        st = {l: rng.choice(ids(l)) for l in ('bg', 'eyes', 'mouth', 'hair', 'top')}
        st['hats'] = rng.choice(ids('hats')) if rng.random() < .6 else None
        st['glasses'] = rng.choice(ids('glasses')) if rng.random() < .35 else None
        st['items'] = rng.choice(ids('items')) if rng.random() < .55 else None
        st['overlays'] = 'date-stamp' if 'date-stamp' in ids('overlays') and rng.random() < .5 else None
        name = f'baddie-{n + 1:02d}.jpg'
        dst = os.path.join(GALLERY, name)
        sig = json.dumps(st, sort_keys=True)
        sigf = dst + '.sig'
        if not os.path.exists(dst) or not os.path.exists(sigf) or open(sigf).read() != sig:
            compose(st, size=720).convert('RGB').save(dst, quality=85, optimize=True, progressive=True)
            open(sigf, 'w').write(sig)
        gallery.append(f'{name}?v={md5(dst)}')

    # og image: three baddies side by side
    og = Image.new('RGB', (1200, 630), (12, 6, 18))
    for i in range(3):
        b = Image.open(os.path.join(GALLERY, f'baddie-{i + 1:02d}.jpg')).resize((400, 400), Image.LANCZOS)
        og.paste(b, (i * 400, 115))
    og.save(os.path.join(ROOT, 'assets', 'og.jpg'), quality=86)

    # 5) manifest, cache-busted by content hash
    manifest = {'size': SIZE, 'order': DRAW_ORDER, 'fixed': {}, 'gallery': gallery}
    for layer in DRAW_ORDER:
        out = []
        for it in items[layer]:
            e = {'id': it['id'], 'label': it['label'], 'src': f'{it["src"]}?v={md5(os.path.join(OUT, it["src"]))}'}
            if 'thumb' in it:
                e['thumb'] = f'{it["thumb"]}?v={md5(os.path.join(OUT, it["thumb"]))}'
            out.append(e)
        if layer in FIXED:
            manifest['fixed'][layer] = out[0]['src'] if out else None
        else:
            manifest[layer] = out
    body = json.dumps(manifest, indent=1)
    with open(os.path.join(OUT, 'manifest.json'), 'w') as f:
        f.write(body)

    # stamp the manifest version into index.html (the HTML itself is never cached)
    v = hashlib.md5(body.encode()).hexdigest()[:8]
    index = os.path.join(ROOT, 'index.html')
    if os.path.exists(index):
        html = open(index).read()
        new = re.sub(r"const PFP_V = '[^']*'", f"const PFP_V = '{v}'", html)
        if new != html:
            open(index, 'w').write(new)

    total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(OUT) for f in fs)
    print('pfp-build: ' + ', '.join(f'{l} {len(items[l])}' for l in DRAW_ORDER if l not in FIXED) + f' · {total / 1e6:.1f} MB · v{v}')


if __name__ == '__main__':
    main()
