import re,sys,json,html,zipfile
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
brief=(ROOT/'art_bible.txt').read_text(encoding='utf-8-sig')
entries=[]
models=json.loads((ROOT/'production'/'model_validation.json').read_text())
lookup={m['name']:m for m in models}
for number,name in re.findall(r'^(\d+)\. ([a-z][a-z0-9_]+)\s',brief,re.M):
    number=int(number)
    folder='concepts' if number<=3 or number==37 else 'textures' if number<=11 else 'panoramas' if number<=14 else 'models' if number<=36 else 'ui'
    extension='glb' if folder=='models' else 'png'
    path=ROOT/folder/f'{name}.{extension}'
    assert path.is_file(),path
    e=dict(item=number,name=name,path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size)
    if extension=='png':e['pixels']=list(Image.open(path).size)
    else:e.update(lookup[name]);e['preview']=f'previews/{name}.png'
    if folder=='textures':e['normal_map']=f'textures/{name}_normal.png'
    e['status']='pipeline_processed' if folder in ('textures','panoramas','models') else 'approved_reference' if folder=='concepts' else 'first_pass'
    entries.append(e)
assert len(entries)==39,len(entries)
(ROOT/'manifest.json').write_text(json.dumps(dict(master='concepts/uthan_concept_main.png',status='All 39 files present. Textures seamless, panoramas wrapped, models with LODs, colliders, baked AO and normal maps; remaining art limits in README.md',extra=dict(support_texture='textures/support_stone.png',viewer='viewer.html',collision='production/collision.json',validator='production/gltf_validator_report.json'),assets=entries),indent=2))
cards=[]
for e in entries:
    src=e.get('preview',e['path']);details=f"{e['triangles']:,} triangles / {e['budget']:,} budget · {len(e['lods'])} LODs · {e['collision']['shapes']} colliders" if 'triangles' in e else ' × '.join(map(str,e['pixels']))+' px'
    cards.append(f'<article><a href="{html.escape(e["path"])}"><img loading="lazy" src="{src}" alt="{e["name"]}"></a><h2>{e["item"]:02d} · {e["name"]}</h2><p>{details}</p><a href="{e["path"]}" download>Download {Path(e["path"]).suffix.upper()[1:]}</a></article>')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Village Uthan · Asset index</title><style>body{margin:0;background:#f2ede3;color:#352b22;font:16px system-ui}header{padding:40px 5vw 24px;max-width:1100px}h1{font:48px Georgia;margin:10px 0}header p{max-width:850px;line-height:1.6}main{padding:12px 5vw 50px;display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:22px}article{background:#fffaf0;padding:12px;border:1px solid #d6c8b5;border-radius:5px}img{width:100%;height:220px;object-fit:contain;background:#e4ded2}h2{font-size:15px;overflow-wrap:anywhere}a{color:#79402c}article p{font-size:13px;color:#6e6050}small{letter-spacing:2px;text-transform:uppercase}</style><header><small>Sholo Guti · Environment 01</small><h1>Village Uthan</h1><p>39 requested asset files. Approved environment: concept A. The concept board is decorative and inaccurate; UI ground is reserved for the correct board overlay.</p><p>Textures tile seamlessly and ship with normal maps; panoramas wrap with clean poles. GLBs pass the Khronos glTF validator and include LODs, colliders and baked AO; the chicken is rigged with idle, peck and walk clips. Model art is still procedural low-poly. Open the <a href="viewer.html">3D viewer</a> (serve over HTTP) and read the <a href="README.md">handoff notes</a>.</p></header><main>'''+''.join(cards)+'</main></html>'
(ROOT/'index.html').write_text(page,encoding='utf-8')
print(json.dumps(dict(requested_assets=len(entries),glbs=len(models))))
if '--zip' not in sys.argv:raise SystemExit   # optional: writes the archive next to this folder
archive=ROOT.parent/'Village_Uthan.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
    for p in ROOT.rglob('*'):
        if p.is_file() and not {'__pycache__','.git','.claude'}&set(p.parts):z.write(p,Path('Village_Uthan')/p.relative_to(ROOT))
print(json.dumps(dict(requested_assets=len(entries),glbs=len(models),archive=str(archive),archive_bytes=archive.stat().st_size)))
