"""Final invariant checks and portable ZIP. Only rooftop and required support files."""
import json,zipfile,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
manifest=json.loads((ROOT/'rooftop_manifest.json').read_text());assert len(manifest['assets'])==43
report={'requested_assets':43,'checks':[]};tiles=[]
for e in manifest['assets']:
    p=ROOT/e['file'];assert p.exists()
    if e['type']=='models':assert e['triangles']<e['budget'];continue
    im=Image.open(p).convert('RGB');a=np.asarray(im)
    if e['type']=='textures' and 'atlas' not in e['name']:
        assert np.array_equal(a[:,0],a[:,-1]),p.name
        if 'facade' not in e['name']:assert np.array_equal(a[0],a[-1]),p.name
        tile=im.resize((240,240));repeat=Image.new('RGB',(480,510),'#eeeae0')
        for y in [0,240]:
            for x in [0,240]:repeat.paste(tile,(x,y))
        ImageDraw.Draw(repeat).text((8,487),e['name'],fill='#33291e');tiles.append(repeat)
        report['checks'].append({'name':e['name'],'repeat_edges':'PASS'})
    if e['type']=='panoramas':
        assert im.width==im.height*2 and np.array_equal(a[:,0],a[:,-1])
        assert np.all(a[0]==a[0,0]) and np.all(a[-1]==a[-1,0])
        report['checks'].append({'name':e['name'],'ratio_wrap_poles':'PASS'})
    if e['type']=='effects':
        assert im.size==(2048,2048)
        for y in range(4):
            for x in range(4):
                cell=a[y*512:(y+1)*512,x*512:(x+1)*512]
                assert cell.max()>0
                assert max(cell[0].max(),cell[-1].max(),cell[:,0].max(),cell[:,-1].max())==0,(p.name,y,x)
        report['checks'].append({'name':e['name'],'16_cells_black_boundaries':'PASS'})
    if e['name']=='ui_rooftop_loading':assert im.width*9==im.height*16
    if e['name']=='ui_rooftop_thumbnail':assert im.width==im.height
sheet=Image.new('RGB',(480*4,510*math.ceil(len(tiles)/4)),'#eeeae0')
for i,t in enumerate(tiles):sheet.paste(t,((i%4)*480,(i//4)*510))
sheet.save(ROOT/'previews'/'rooftop_texture_repeat_sheet.jpg',quality=94)
(ROOT/'production'/'rooftop_final_checks.json').write_text(json.dumps(report,indent=2))
paths={ROOT/e['file'] for e in manifest['assets']}
paths.update(ROOT/e['preview'] for e in manifest['assets'])
for pattern in ['rooftop_*.html','rooftop_*.md','rooftop_*.json','rooftop_art_bible.txt','production/*rooftop*.*','effects/rooftop*.json','textures/rooftop_tex_facade_emissive.png','concepts/rooftop*prompts.txt','concepts/rooftop*prompt.txt','concepts/rooftop_concept_main_option_*.png','previews/rooftop*']:
    paths.update(ROOT.glob(pattern))
paths.update((ROOT/'production'/'rooftop_source').rglob('*.png'))
paths.update((ROOT/'textures').glob('support_rooftop_*.png'))
for f in ['build_models.py','process_images.py','inspect_assets.py']:paths.add(ROOT/'production'/f)
for f in ['uthan_tex_bark_banyan.png','uthan_tex_wall_mud.png','support_rooftop_cotton.png','support_rooftop_lungi.png']:paths.add(ROOT/'textures'/f)
paths.update(p for p in (PROJECT/'game'/'vendor'/'three').rglob('*') if p.is_file())
archive=ROOT/'Old_Dhaka_Rooftop_Night.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(paths):
        if p.is_file():z.write(p,p.relative_to(PROJECT).as_posix())
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(json.dumps(dict(archive=str(archive),files=len(paths),zip_mb=round(archive.stat().st_size/1e6,2),checks='PASS')))
