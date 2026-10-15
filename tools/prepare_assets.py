"""Turn the source art in ../art into game-ready files in ../game/assets.

What it does
  models   art/models/*.glb  -> textures resized (512 px, 1024 px for banyan/house/haystack; normal maps half that),
           re-encoded as WebP, deduplicated, quantized -> game/assets/models-glb/*.glb
           and wrapped as base64 JSON         -> game/assets/models/*.json
           (Claude artifacts and some static hosts refuse .glb, JSON is served everywhere)
  textures art/textures/*.png and *_normal.png are already seamless with normal maps
           (made by art/production/process_images.py), so they are only resized
                                              -> game/assets/tex/*.jpg, *_n.jpg
  panos    art/panoramas/*.png (wrapped, 2048 x 1024) -> game/assets/tex/pano_*.jpg
  ui       loading art and Dadu portrait -> game/assets/ui/

Needs: Python with Pillow, and Node (run `npm install` in this folder once).
Run from this folder:  python prepare_assets.py
"""
import base64, json, shutil, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
import os
ART, OUT = ROOT / 'art', Path(os.environ.get('ASSETS_OUT', ROOT / 'game' / 'assets'))
NPX = 'npx.cmd' if sys.platform.startswith('win') else 'npx'
BIG = {'prop_banyan_tree', 'prop_house', 'prop_haystack'}


def models():
    (OUT / 'models').mkdir(parents=True, exist_ok=True)
    (OUT / 'models-glb').mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for src in sorted((ART / 'models').glob('*.glb')):
            size = 1024 if src.stem in BIG else 512
            t1, dst = Path(tmp) / src.name, OUT / 'models-glb' / src.name
            run = lambda *a: subprocess.run([NPX, 'gltf-transform', *a], check=True, cwd=Path(__file__).parent, capture_output=True)
            run('resize', str(src), str(t1), '--width', str(size), '--height', str(size))
            # Normal maps compress poorly as WebP; half resolution is not visible at play distance.
            run('resize', str(t1), str(t1), '--width', str(size // 2), '--height', str(size // 2), '--pattern', '*_normal')
            run('webp', str(t1), str(dst), '--quality', '82')
            run('dedup', str(dst), str(dst))
            run('quantize', str(dst), str(dst))   # KHR_mesh_quantization: 16/8-bit vertex data, read natively by three.js
            payload = {'name': src.stem, 'format': 'glb-base64', 'glb': base64.b64encode(dst.read_bytes()).decode()}
            (OUT / 'models' / f'{src.stem}.json').write_text(json.dumps(payload))
            print(f'model  {src.stem:28s} {src.stat().st_size/1e6:6.1f} MB -> {dst.stat().st_size/1e6:5.2f} MB')


def textures():
    (OUT / 'tex').mkdir(parents=True, exist_ok=True)
    for name, size in [('ground_mud', 1024), ('ground_rough', 1024), ('mat_jute', 512), ('straw', 512), ('bark_banyan', 512)]:
        for suffix, out, quality in [('', name, 86), ('_normal', f'{name}_n', 92)]:
            src = ART / 'textures' / f'uthan_tex_{name}{suffix}.png'
            if not src.is_file():
                sys.exit(f'{src} is missing: run art/production/process_images.py first.')
            im = Image.open(src).convert('RGB')
            if im.size != (size, size):
                im = im.resize((size, size), Image.LANCZOS)
            im.save(OUT / 'tex' / f'{out}.jpg', quality=quality)
        print('texture', name)
    for t in ['afternoon', 'sunset', 'night']:
        Image.open(ART / 'panoramas' / f'uthan_pano_{t}.png').convert('RGB').save(OUT / 'tex' / f'pano_{t}.jpg', quality=88)
        print('pano   ', t)


def ui():
    (OUT / 'ui').mkdir(parents=True, exist_ok=True)
    Image.open(ART / 'ui' / 'ui_uthan_loading.png').convert('RGB').save(OUT / 'ui' / 'loading.jpg', quality=85)
    d = Image.open(ART / 'concepts' / 'char_dadu_concept.png').convert('RGB'); d.thumbnail((800, 800))
    d.save(OUT / 'ui' / 'dadu.jpg', quality=85)
    print('ui      loading, dadu')


if __name__ == '__main__':
    if not shutil.which(NPX):
        sys.exit('Node.js is required for the model step (npx not found).')
    textures(); ui(); models()
