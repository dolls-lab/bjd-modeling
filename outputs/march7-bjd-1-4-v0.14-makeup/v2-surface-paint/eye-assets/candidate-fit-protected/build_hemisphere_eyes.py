"""Import in Blender: objects, report = build_eyes(collection).
Creates only two true hemisphere cups. Original source eye geometry is never loaded.
No existing object/material is modified or removed, and no file is saved.
"""
from pathlib import Path
import json,hashlib
import numpy as np
import bpy
P=Path(__file__).resolve().parent

def build_eyes(collection=None):
    collection=collection or bpy.context.scene.collection
    data=np.load(P/'hemisphere-eye-geometry.npz')
    assets=json.loads((P/'eye-assets-report.json').read_text())
    objects=[];records=[]
    inner=bpy.data.materials.new('March7_Hemisphere_White_Inside');inner.use_nodes=True
    bs=inner.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.86,.86,.86,1)
    bs.inputs['Roughness'].default_value=.34;bs.inputs['Specular IOR Level'].default_value=.35
    for side in ['negative','positive']:
        name='PREVIEW_EYE_HEMISPHERE_'+side.upper()
        v=data['vertices_'+side];f=data['faces_'+side];uv=data['uv_'+side];mi=data['material_index_'+side]
        mesh=bpy.data.meshes.new(name+'_Geometry');mesh.from_pydata(v.tolist(),[],f.tolist());mesh.update()
        uvlay=mesh.uv_layers.new(name='Iris_On_Spherical_Surface')
        uvlay.data.foreach_set('uv',uv[f].ravel())
        mat=bpy.data.materials.new('March7_Hemisphere_Iris_'+side);mat.use_nodes=True
        nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF')
        bs.inputs['Roughness'].default_value=.24;bs.inputs['Specular IOR Level'].default_value=.45
        bs.inputs['Coat Weight'].default_value=.22;bs.inputs['Coat Roughness'].default_value=.16
        bs.inputs['Emission Strength'].default_value=0
        tex=nodes.new('ShaderNodeTexImage');tex.name='Original_March7_Iris_Baked_On_Hemisphere'
        image=bpy.data.images.load(str(P/f'march7-hemisphere-eye-{side}.png'),check_existing=True)
        image.colorspace_settings.name='sRGB';image.pack();tex.image=image;tex.extension='EXTEND';tex.interpolation='Linear'
        coord=nodes.new('ShaderNodeUVMap');coord.uv_map=uvlay.name
        links.new(coord.outputs['UV'],tex.inputs['Vector']);links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        # Opaque white/iris surface: no alpha eye cards and no emitted-light shader.
        bs.inputs['Alpha'].default_value=1
        mesh.materials.append(mat);mesh.materials.append(inner)
        for poly,material_id in zip(mesh.polygons,mi):poly.material_index=int(material_id);poly.use_smooth=True
        ob=bpy.data.objects.new(name,mesh);collection.objects.link(ob)
        ob['preview_only']=True;ob['surface_type']='Open-back physical hemispherical cup, not an original game eye patch'
        ob['outer_radius_mm']=9.;ob['inner_radius_mm']=8.4;ob['front_axis']='-Y';ob['center_mm']=data['center_'+side].tolist()
        ob['iris_source']='Original PMX iris/highlight rasterized offline onto real spherical exterior';ob['emission_strength']=0.;ob['skin_edge_adaptation']='Locally retracted behind v14 front skin by0.35mm; paired inner surface follows'
        objects.append(ob)
        records.append({'object':name,'vertices':len(v),'triangles':len(f),'center_mm':data['center_'+side].tolist(),'outer_radius_mm':9.,'inner_radius_mm':8.4,'cup_wall_mm':.6,'shape':'Spherical main cup with hidden-edge skin retraction','exact_sphere':False,'outer_material':mat.name,'inner_material':inner.name,'packed_image':image.name,'image_sha256':hashlib.sha256((P/f'march7-hemisphere-eye-{side}.png').read_bytes()).hexdigest(),'emission_strength':0.})
    report={'objects':records,'original_game_eye_meshes_created':False,'geometry_source_npz_sha256':hashlib.sha256((P/'hemisphere-eye-geometry.npz').read_bytes()).hexdigest(),'source_bake_report':'eye-assets-report.json','fit_report':'eye-assets-report.json','fit_note':'Spherical main cup with local hidden-edge retraction to protect actual head skin; appearance-only, not a physical eye clearance pass.','existing_head_or_cap_modified':False,'preview_only':True}
    return objects,report
