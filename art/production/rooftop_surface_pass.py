"""Dedicated rooftop materials and embedded roughness/metallic maps."""
import io
import numpy as np
from PIL import Image

def apply(R):
    for key,name in {'blackplastic':'tank','redplastic':'redplastic','rust':'iron','wood':'wood','clay':'clay','paper':'paper','skin':'skin','skinlight':'skin','leaf':'leaf','leaf2':'leaf','jaggery':'moa'}.items():
        R.material(key,[1,1,1],'support_rooftop_'+name,.8)
    R.M['skinlight']['color']=[1.035]*3
    # User direction: simple stylized faces, without photographic facial mapping.
    R.material('skin',[.47,.25,.13],None,.82)
    R.material('skinlight',[.52,.29,.16],None,.82)
    previous_texture=R.b.texture_image
    def texture(name,size,kind):
        path=R.ROOT/'textures'/f'{name}_normal.png'
        if kind!='normal' or not path.exists():return previous_texture(name,size,kind)
        im=Image.open(path).resize((min(size,256),min(size,256)),Image.Resampling.LANCZOS);out=io.BytesIO();im.save(out,'PNG');return out.getvalue(),'image/png'
    R.b.texture_image=texture
    previous_save=R.b.GLB.save
    def save(self,path,doc):
        for m in doc['materials']:
            key=m['name'];info=R.M.get(key)
            if not info or not info['tex']:continue
            orm=R.ROOT/'textures'/f'{info["tex"]}_orm.png'
            if not orm.exists():continue
            # RGB: unused occlusion, roughness, metallic. Store as linear PNG.
            out=io.BytesIO();Image.open(orm).resize((256,256),Image.Resampling.LANCZOS).save(out,'PNG');data=out.getvalue();idx=len(doc['images'])
            doc['images'].append(dict(bufferView=self.view(data),mimeType='image/png',name=orm.stem))
            tid=len(doc['textures']);doc['textures'].append(dict(source=idx,sampler=0))
            m['pbrMetallicRoughness'].update(metallicRoughnessTexture=dict(index=tid),roughnessFactor=1,metallicFactor=1)
        return previous_save(self,path,doc)
    R.b.GLB.save=save
