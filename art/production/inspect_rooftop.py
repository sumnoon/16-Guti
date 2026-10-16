"""Read-back validation and geometry renders for rooftop deliverables only."""
import json, math, io, struct, html
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
# Reuse readback and software renderer only, not the legacy script's batch operation.
scope={'__file__':str(ROOT/'production'/'inspect_assets.py')}
renderer_source=(ROOT/'production'/'inspect_assets.py').read_text().split('report=[];tiles=[]')[0]
# glTF factors are linear; decode base-colour textures before shading and encode
# the shaded foreground for display. Leave the existing display-space backdrop.
renderer_source=renderer_source.replace('rgb=rgb*tex[ty,tx]', 'sample=tex[ty,tx];rgb=rgb*np.where(sample<=.04045,sample/12.92,((sample+.055)/1.055)**2.4)')
renderer_source=renderer_source.replace('canvas[y0:y1+1,x0:x1+1][mask]=rgb[mask]', 'rgb=np.clip(rgb,0,1);rgb=np.where(rgb<=.0031308,12.92*rgb,1.055*rgb**(1/2.4)-.055);canvas[y0:y1+1,x0:x1+1][mask]=rgb[mask]')
exec(renderer_source,scope)
read_glb=scope['read_glb'];render=scope['render']
models=json.loads((ROOT/'production'/'rooftop_model_validation.json').read_text())
checks=[];tiles=[]
for entry in models:
    name=entry['name'];path=ROOT/'models'/f'{name}.glb'
    doc,parts,textures,tri=read_glb(path)
    assert tri<entry['budget'] and entry['bottom_center_origins']
    assert len(doc['meshes'])==(3 if name in ['prop_flower_pots','char_kite_flyers'] else 1)
    assert all('uri' not in im for im in doc.get('images',[]))
    offset=0
    for node in doc['nodes']:
        if 'mesh' not in node:continue
        count=len(doc['meshes'][node['mesh']]['primitives'])
        tr=np.array(node.get('translation',[0,0,0]))[[0,2,1]]*[1,-1,1]
        for i in range(offset,offset+count):
            p=list(parts[i]);p[0]=p[0]+tr;parts[i]=tuple(p)
        offset+=count
    img=render(parts,textures,size=480);img.save(ROOT/'previews'/f'{name}.png')
    tile=Image.new('RGB',(480,520),'#eeeae0');tile.paste(img,(0,0));d=ImageDraw.Draw(tile)
    d.text((12,485),name,fill='#33291e');d.text((12,502),f'{tri:,} triangles / {entry["budget"]:,} budget',fill='#6b5944');tiles.append(tile)
    checks.append(dict(name=name,readback='PASS',triangles=tri,objects=len(doc['meshes']),embedded_images=len(doc.get('images',[]))))
sheet=Image.new('RGB',(480*4,520*math.ceil(len(tiles)/4)),'#eeeae0')
for i,t in enumerate(tiles):sheet.paste(t,((i%4)*480,(i//4)*520))
sheet.save(ROOT/'previews'/'rooftop_model_contact_sheet.jpg',quality=93)
image_checks=[]
for folder in ['concepts','textures','panoramas','effects','ui']:
    for p in (ROOT/folder).glob('*.png'):
        if not(p.stem.startswith(('rooftop_','ui_rooftop_','char_rooftop_'))) or '_option_' in p.stem:continue
        im=Image.open(p).convert('RGB');a=np.asarray(im,dtype=float)
        e=dict(name=p.stem,file=p.relative_to(ROOT).as_posix(),size=list(im.size))
        if folder in ['textures','panoramas'] and 'atlas' not in p.stem:
            e.update(horizontal_wrap_error=round(float(np.abs(a[:,0]-a[:,-1]).mean()),2),vertical_wrap_error=round(float(np.abs(a[0]-a[-1]).mean()),2),interior_horizontal_error=round(float(np.abs(a[:,1:]-a[:,:-1]).mean()),2),interior_vertical_error=round(float(np.abs(a[1:]-a[:-1]).mean()),2))
        if folder=='effects':e.update(grid=[4,4],pixel_dimensions_divisible_by_4=(im.width%4==0 and im.height%4==0),black_pixel_fraction=round(float((a.max(2)==0).mean()),4))
        image_checks.append(e)
(ROOT/'production'/'rooftop_readback.json').write_text(json.dumps(checks,indent=2))
(ROOT/'production'/'rooftop_image_checks.json').write_text(json.dumps(image_checks,indent=2))
print(json.dumps(dict(models=len(checks),images=len(image_checks),preview='previews/rooftop_model_contact_sheet.jpg')))
