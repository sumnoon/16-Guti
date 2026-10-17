"""Assemble a self-contained inventory/gallery for the 43 requested rooftop assets."""
import json,re,html,hashlib,zipfile
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
models={e['name']:e for e in json.loads((ROOT/'production'/'rooftop_model_validation.json').read_text())}
brief=(ROOT/'rooftop_art_bible.txt').read_text(encoding='utf-8-sig')
items=[]
for n,name in re.findall(r'^(\d+)\.\s+([a-z][a-z0-9_]+)',brief,re.M):
    n=int(n)
    if n<=3 or n==41:folder='concepts'
    elif n<=12:folder='textures'
    elif n<=14:folder='panoramas'
    elif n<=17:folder='effects'
    elif n<=40:folder='models'
    else:folder='ui'
    file=f'{folder}/{name}'+('.glb' if folder=='models' else '.png');p=ROOT/file
    assert p.exists(),f'Missing {n}: {file}'
    e=dict(number=n,name=name,type=folder,file=file,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),preview=f'previews/{name}.png' if folder=='models' else file)
    if folder=='models':e.update(triangles=models[name]['triangles'],budget=models[name]['budget'],status='Procedural model; art refinement needed')
    else:
        e['size']=list(Image.open(p).size)
        e['status']='Generated artwork'
        if folder=='textures':e['status']='Finished texture; repeat axes in handoff'
        if folder=='panoramas':e['status']='LDR panorama; wrap and poles corrected'
        if folder=='effects':e['status']='4 x 4 effect sheet · 512 px cells'
    items.append(e)
assert len(items)==43
manifest=dict(environment='Old Dhaka Rooftop Night',master='concepts/rooftop_concept_main.png',approved_option='C',asset_count=len(items),assets=items)
(ROOT/'rooftop_manifest.json').write_text(json.dumps(manifest,indent=2))
cards=[]
for e in items:
    detail=f'{e["triangles"]:,} / {e["budget"]:,} triangles' if 'triangles' in e else ' × '.join(map(str,e['size']))+' px'
    viewer=f' <a href="rooftop_viewer.html?asset={e["name"]}">Inspect 3D</a>' if e['type']=='models' else ''
    cards.append(f'<article data-type="{e["type"]}"><a href="{e["file"]}"><img loading="lazy" src="{e["preview"]}" alt="{e["name"]}"></a><div><small>{e["number"]:02d} · {e["type"]}</small><h2>{e["name"]}</h2><p>{detail}</p><p class="status">{e["status"]}</p><a href="{e["file"]}" download>Download</a>{viewer}</div></article>')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Old Dhaka Rooftop Night · Asset library</title><style>
*{box-sizing:border-box}body{margin:0;background:#16213e;color:#eee6d9;font:15px system-ui,sans-serif}header{padding:36px max(24px,5vw);border-bottom:1px solid #5b4a8a;background:#10192f}h1{font:42px Georgia,serif;margin:6px 0 12px}header p{max-width:850px;line-height:1.6;color:#ccc5bc}a{color:#ffb84d}nav{display:flex;flex-wrap:wrap;gap:8px;padding:20px 5vw}button{background:#27324c;color:#eee6d9;border:1px solid #5b4a8a;padding:10px 16px;cursor:pointer}button[aria-pressed=true]{background:#ffb84d;color:#16213e}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:22px;padding:0 5vw 50px}article{background:#222e47;border:1px solid #41475b;min-width:0}article img{width:100%;height:235px;object-fit:contain;background:#10192f}article>div{padding:18px}h2{font:16px ui-monospace,monospace;overflow-wrap:anywhere;margin:9px 0}small,.status{color:#bdb6c9}.status{font-size:12px}article a+ a{margin-left:18px}article[hidden]{display:none}</style>
<header><small>SHOLO GUTI · ENVIRONMENT ASSET LIBRARY</small><h1>Old Dhaka Rooftop Night</h1><p>43 requested files · approved master: option C. Browse concept artwork, materials, effects, UI and 23 procedural GLBs. Read the handoff for production limitations and validation results.</p><a href="rooftop_README.md">Handoff notes</a> · <a href="rooftop_manifest.json">Manifest</a> · <a href="previews/rooftop_model_contact_sheet.jpg">Model contact sheet</a> · <a href="rooftop_viewer.html">3D viewer</a></header>
<nav>'''+''.join(f'<button data-filter="{t}" aria-pressed="{str(t=="all").lower()}">{t.title()}</button>' for t in ['all','concepts','textures','panoramas','effects','models','ui'])+'</nav><main>'+''.join(cards)+'''</main><script>for(const b of document.querySelectorAll('button'))b.onclick=()=>{for(const c of document.querySelectorAll('article'))c.hidden=b.dataset.filter!=='all'&&c.dataset.type!==b.dataset.filter;for(const q of document.querySelectorAll('button'))q.setAttribute('aria-pressed',q===b)}</script></html>'''
(ROOT/'rooftop_index.html').write_text(page,encoding='utf-8')
print(json.dumps(dict(assets=len(items),models=sum(e['type']=='models' for e in items),images=sum(e['type']!='models' for e in items),total_mb=round(sum(e['bytes'] for e in items)/1e6,2))))
