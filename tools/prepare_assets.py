"""Turn the source art in ../art into game-ready files in ../game/assets.

What it does
  models   art/models/*.glb  -> textures resized (512 px, 1024 px for the BIG set; normal maps half that),
           re-encoded as WebP, deduplicated, quantized -> game/assets/models-glb/*.glb
           and wrapped as base64 JSON         -> game/assets/models/*.json
           (Claude artifacts and some static hosts refuse .glb, JSON is served everywhere)
  textures art/textures/*.png and *_normal.png are already seamless with normal maps
           (made by art/production/process_images.py), so they are only resized
                                              -> game/assets/tex/*.jpg, *_n.jpg
  panos    art/panoramas/*.png (wrapped, 2048 x 1024) -> game/assets/tex/pano_*.jpg
  ui       loading art and opponent portraits -> game/assets/ui/
  rooftop  the Old Dhaka Rooftop set: its models, cement / plaster / jute textures (normal maps are
           derived from the colour, the art pack ships none), panoramas, effect sheets, the kite atlas
           with white keyed out, loading art and the rival's portrait

Needs: Python with Pillow and numpy, and Node (run `npm install` in this folder once).
Run from this folder:
  python prepare_assets.py            everything
  python prepare_assets.py village    Village Uthan only
  python prepare_assets.py rooftop    Old Dhaka Rooftop only
"""
import base64, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ART, OUT = ROOT / 'art', Path(os.environ.get('ASSETS_OUT', ROOT / 'game' / 'assets'))
NPX = 'npx.cmd' if sys.platform.startswith('win') else 'npx'
# The Old Dhaka buildings stay at 512 px: six files each carry their own copy of the same facade,
# plaster and paint textures, and they are seen from 5 m and further.
BIG = {'prop_banyan_tree', 'prop_house', 'prop_haystack', 'prop_chilekotha'}
ROOFTOP_MODELS = {'bld_mosque', 'bld_oldhaka_block_1', 'bld_oldhaka_block_2', 'bld_oldhaka_block_3', 'bld_oldhaka_block_4',
                  'char_fire_breather', 'char_kite_flyers', 'guti_bottle_cap', 'guti_marble_glass', 'prop_chilekotha',
                  'prop_clothesline_roof', 'prop_fanush', 'prop_flower_pots', 'prop_kite_ghuri', 'prop_moa_plate',
                  'prop_natai_spool', 'prop_paper_lantern', 'prop_parapet_segment', 'prop_plastic_chair', 'prop_speaker',
                  'prop_string_lights', 'prop_water_tank', 'prop_wire_pole'}


def models(names):
    (OUT / 'models').mkdir(parents=True, exist_ok=True)
    (OUT / 'models-glb').mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for src in sorted((ART / 'models').glob('*.glb')):
            if not names(src.stem):
                continue
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


def normal_from_colour(im, strength):
    """Tangent-space normal map from a tileable colour texture (brightness used as height, wraps at the edges)."""
    h = np.asarray(im.convert('L').filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255.0
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    n = np.stack([-dx, dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8))


def rooftop():
    (OUT / 'tex').mkdir(parents=True, exist_ok=True)
    (OUT / 'ui').mkdir(parents=True, exist_ok=True)
    # surfaces drawn by the game itself (roof floor, the house walls below it, the players' mats)
    for name, size, strength in [('cement', 1024, 2.2), ('plaster_old', 512, 2.0), ('jute_mat', 512, 3.0)]:
        im = Image.open(ART / 'textures' / f'rooftop_tex_{name}.png').convert('RGB').resize((size, size), Image.LANCZOS)
        im.save(OUT / 'tex' / f'roof_{name}.jpg', quality=86)
        normal_from_colour(im, strength).save(OUT / 'tex' / f'roof_{name}_n.jpg', quality=92)
        print('texture', 'roof_' + name)
    # lit-window mask, aligned with the facade texture inside the building models
    Image.open(ART / 'textures' / 'rooftop_tex_facade_emissive.png').convert('L').resize((512, 512), Image.LANCZOS) \
        .save(OUT / 'tex' / 'roof_facade_emissive.jpg', quality=88)
    # kite atlas: 4 x 4 diamonds on white -> transparent background
    k = Image.open(ART / 'textures' / 'rooftop_tex_kite_atlas.png').convert('RGB').resize((512, 512), Image.LANCZOS)
    a = np.asarray(k, dtype=np.float32)
    alpha = np.clip((255.0 - a.min(-1) - 18.0) * 6.0, 0, 255).astype(np.uint8)
    Image.fromarray(np.dstack([np.asarray(k), alpha]), 'RGBA').save(OUT / 'tex' / 'roof_kites.png', optimize=True)
    print('texture roof_kites')
    for t in ['dusk', 'night']:
        Image.open(ART / 'panoramas' / f'rooftop_pano_{t}.png').convert('RGB').save(OUT / 'tex' / f'pano_rooftop_{t}.jpg', quality=88)
        print('pano    rooftop', t)
    # additive effect sheets on black: 4 x 4 cells, 256 px each is plenty at sky distance
    for fx in ['fireworks', 'fire_breath', 'sparks']:
        Image.open(ART / 'effects' / f'rooftop_fx_{fx}.png').convert('RGB').resize((1024, 1024), Image.LANCZOS) \
            .save(OUT / 'tex' / f'fx_{fx}.jpg', quality=88)
        print('fx     ', fx)
    Image.open(ART / 'ui' / 'ui_rooftop_loading.png').convert('RGB').save(OUT / 'ui' / 'loading_rooftop.jpg', quality=85)
    # the rival's face, from the front view of his concept sheet
    r = Image.open(ART / 'concepts' / 'char_rooftop_rival_concept.png').convert('RGB').crop((415, 0, 615, 200))
    r.resize((160, 160), Image.LANCZOS).save(OUT / 'ui' / 'rival.jpg', quality=88)
    print('ui      loading_rooftop, rival')


if __name__ == '__main__':
    if not shutil.which(NPX):
        sys.exit('Node.js is required for the model step (npx not found).')
    which = set(sys.argv[1:]) or {'village', 'rooftop'}
    if 'village' in which:
        textures(); ui(); models(lambda n: n not in ROOFTOP_MODELS)
    if 'rooftop' in which:
        rooftop(); models(lambda n: n in ROOFTOP_MODELS)
