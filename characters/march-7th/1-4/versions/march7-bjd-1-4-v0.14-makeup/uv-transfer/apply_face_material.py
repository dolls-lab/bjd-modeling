"""Importable Blender helper: create a separate preview mesh without moving vertices.

Usage:
    from apply_face_material import create_textured_head, create_skin_material
    obj = create_textured_head('/abs/path/face-uv-transfer.npz')
No source Blend save or source geometry mutation is performed by this module.
"""
from pathlib import Path
import json
import numpy as np
import bpy

def create_skin_material(directory, name='March7_Preview_SolidSkin'):
    directory=Path(directory)
    report=json.loads((directory/'uv-transfer-report.json').read_text())
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF')
    base=report['skin_base_linear_rgb']
    bs.inputs['Base Color'].default_value=(*base,1)
    bs.inputs['Roughness'].default_value=.78
    bs.inputs['Specular IOR Level'].default_value=.18
    return mat

def create_textured_head(transfer_path, name='PREVIEW_V14_MAKEUP_HEAD', collection=None):
    transfer_path=Path(transfer_path);directory=transfer_path.parent
    data=np.load(transfer_path);report=json.loads((directory/'uv-transfer-report.json').read_text())
    vertices=data['head_vertices'];faces=data['head_triangles']
    mesh=bpy.data.meshes.new(name+'_Mesh')
    mesh.from_pydata(vertices.tolist(),[],faces.tolist());mesh.update()
    uv=mesh.uv_layers.new(name='OriginalFaceUV')
    uv.data.foreach_set('uv',data['head_uv_blender'].ravel())
    attr=mesh.attributes.new(name='OriginalFaceWeight',type='FLOAT',domain='CORNER')
    attr.data.foreach_set('value',data['head_makeup_weight'].ravel())
    for p in mesh.polygons:p.use_smooth=True
    mat=create_skin_material(directory,'March7_Preview_OriginalFace')
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF')
    tex=nodes.new('ShaderNodeTexImage');tex.name='Original_PMX_Face_Atlas'
    tex.image=bpy.data.images.load(report['texture_path'],check_existing=True)
    tex.image.colorspace_settings.name='sRGB';tex.extension='EXTEND';tex.interpolation='Linear'
    uvnode=nodes.new('ShaderNodeUVMap');uvnode.uv_map='OriginalFaceUV';links.new(uvnode.outputs['UV'],tex.inputs['Vector'])
    weight=nodes.new('ShaderNodeAttribute');weight.attribute_name='OriginalFaceWeight'
    mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX'
    mix.inputs[1].default_value=(*report['skin_base_linear_rgb'],1)
    links.new(weight.outputs['Fac'],mix.inputs[0]);links.new(tex.outputs['Color'],mix.inputs[2])
    diffuse=report['source_material']['diffuse']
    mul=nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1
    mul.inputs[2].default_value=diffuse;links.new(mix.outputs[0],mul.inputs[1]);links.new(mul.outputs[0],bs.inputs['Base Color'])
    # Preview skin is opaque: source atlas alpha must never make printed skin disappear.
    bs.inputs['Alpha'].default_value=1
    mesh.materials.append(mat)
    obj=bpy.data.objects.new(name,mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    obj['preview_only']=True;obj['geometry_source']='final v14 head_after, unchanged coordinates and triangles'
    obj['source_blend_sha256']=report['inputs'][str(directory.parent.parent/'march7-bjd-1-4-v0.14'/'march7-bjd-head-v0.14-draft.blend')]
    obj['makeup_method']='Original face UV barycentric transfer with exterior-only material weight; raw brow/lash and eye meshes remain separate.'
    return obj
