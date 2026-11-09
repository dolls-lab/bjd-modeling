"""Create a separate appearance preview from immutable accepted v14 geometry."""
from pathlib import Path
import json, hashlib, sys
import numpy as np
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

R=Path(__file__).resolve().parent
BASE=R.parent/'march7-bjd-1-4-v0.14'
SOURCE=R/'source-reference/source-reference.blend'
OUT=R/'march7-v14-makeup-preview.blend'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
basefile=BASE/'march7-bjd-head-v0.14-draft.blend'
basehash=sha(basefile)
assert basehash=='cdb0839449d64a6867cae512fef653a1221315ab97c70b1a8e554a4aa232f96a'
bpy.ops.wm.open_mainfile(filepath=str(basefile));scene=bpy.context.scene
def geometry(ob):
    ob.data.calc_loop_triangles()
    v=np.asarray([ob.matrix_world@p.co for p in ob.data.vertices],np.float32)
    t=np.asarray([q.vertices[:] for q in ob.data.loop_triangles],np.int32)
    return v,t,hashlib.sha256(v.tobytes()+t.tobytes()).hexdigest()
head=bpy.data.objects['PRINT_01_Head_Shell'];cap=bpy.data.objects['PRINT_02_Removable_Cap']
before={o.name:geometry(o)[2] for o in [head,cap]}
for ob in list(bpy.data.objects):
    if ob.type in {'LIGHT','CAMERA'}:bpy.data.objects.remove(ob,do_unlink=True)
    elif ob.type=='MESH':ob.hide_render=True;ob.hide_set(True)
def collection(name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
skincol=collection('01_V14_Painted_Head')
eyecol=collection('02_Character_Eyes_Brows_Mouth_PREVIEW_ONLY')
haircol=collection('03_Optional_Original_Hair_PREVIEW_ONLY')
studio=collection('04_Preview_Studio')
for ob in [head,cap]:
    for c in list(ob.users_collection):c.objects.unlink(ob)
    skincol.objects.link(ob);ob.hide_render=False;ob.hide_set(False);ob.hide_viewport=False
    ob['appearance_preview']='Geometry identical to accepted v14. Only materials/UV added.'

u=np.load(R/'uv-transfer/face-uv-transfer.npz')
rep=json.loads((R/'uv-transfer/uv-transfer-report.json').read_text())
v,t,_=geometry(head)
assert np.array_equal(v,u['head_vertices'].astype(np.float32)) and np.array_equal(t,u['head_triangles'])
uv=head.data.uv_layers.new(name='March7_Original_Face_UV')
mask=head.data.attributes.new(name='March7_Face_Weight',type='FLOAT',domain='CORNER')
loopuv=np.zeros((len(head.data.loops),2),np.float32);loopweight=np.zeros(len(head.data.loops),np.float32)
corneruv=u['head_uv_blender'];cornerweight=u['head_makeup_weight']
for ti,tri in enumerate(head.data.loop_triangles):
    loopuv[np.asarray(tri.loops)]=corneruv[ti]
    loopweight[np.asarray(tri.loops)]=cornerweight[ti]
uv.data.foreach_set('uv',loopuv.ravel());mask.data.foreach_set('value',loopweight)
basecolor=rep['skin_base_linear_rgb'];diff=rep['source_material']['diffuse']
def skin_material(name):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links
    bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*[basecolor[i]*diff[i] for i in range(3)],1)
    bs.inputs['Roughness'].default_value=.7;bs.inputs['Specular IOR Level'].default_value=.18
    bs.inputs['Subsurface Weight'].default_value=0.0
    return m
skin=skin_material('V14_March7_Original_Makeup');n=skin.node_tree.nodes;l=skin.node_tree.links;bs=n.get('Principled BSDF')
tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(rep['texture_path'],check_existing=True);tex.image.colorspace_settings.name='sRGB';tex.image.pack();tex.extension='EXTEND'
un=n.new('ShaderNodeUVMap');un.uv_map=uv.name;l.new(un.outputs['UV'],tex.inputs['Vector'])
attr=n.new('ShaderNodeAttribute');attr.attribute_name=mask.name
mix=n.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(*basecolor,1);l.new(attr.outputs['Fac'],mix.inputs[0]);l.new(tex.outputs['Color'],mix.inputs[2])
mul=n.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=diff;l.new(mix.outputs[0],mul.inputs[1]);l.new(mul.outputs[0],bs.inputs['Base Color'])
em=n.new('ShaderNodeEmission');em.inputs['Strength'].default_value=1;l.new(mul.outputs[0],em.inputs['Color'])
shader=n.new('ShaderNodeMixShader');shader.inputs[0].default_value=.6;l.new(bs.outputs[0],shader.inputs[1]);l.new(em.outputs[0],shader.inputs[2]);l.new(shader.outputs[0],n.get('Material Output').inputs['Surface'])
head.data.materials.clear();head.data.materials.append(skin)
capmat=skin_material('V14_Matched_Cranium_Skin');cn=capmat.node_tree.nodes;cl=capmat.node_tree.links;cbs=cn.get('Principled BSDF')
ce=cn.new('ShaderNodeEmission');ce.inputs['Color'].default_value=cbs.inputs['Base Color'].default_value;ce.inputs['Strength'].default_value=1
cs=cn.new('ShaderNodeMixShader');cs.inputs[0].default_value=.6;cl.new(cbs.outputs[0],cs.inputs[1]);cl.new(ce.outputs[0],cs.inputs[2]);cl.new(cs.outputs[0],cn.get('Material Output').inputs['Surface'])
cap.data.materials.clear();cap.data.materials.append(capmat)

with bpy.data.libraries.load(str(SOURCE),link=False) as (a,b):b.collections=['PMX_SOURCE_HEAD']
ref=b.collections[0];scene.collection.children.link(ref);ref.name='90_Original_March7_Reference'
sourceobs=list(ref.all_objects)
preview=[]
for ob in sourceobs:
    if ob.type!='MESH':continue
    mi=int(ob['source_material_index'])
    for m in ob.data.materials:
        node=m.node_tree.nodes.get('SOURCE_TexturePreviewWeight')
        if node:node.outputs[0].default_value=.85 if mi in {3,4} else .6
        for bs in [q for q in m.node_tree.nodes if q.type=='BSDF_PRINCIPLED']:
            bs.inputs['Roughness'].default_value=.6 if mi==4 else .7
            bs.inputs['Specular IOR Level'].default_value=.18
    if mi not in {0,1,2,3,4,26,28}:continue
    new=ob.copy();new.data=ob.data.copy();new.name=ob.name.replace('SOURCE_','LOOK_')
    (haircol if mi in {26,28} else eyecol).objects.link(new)
    new.hide_viewport=False;new.hide_render=False;new.hide_set(False)
    new['preview_only']=True;new['do_not_print']='Appearance reference; not a printable eye/wig/attachment.'
    preview.append(new)

# Prevent eyebrow/lash overlay from disappearing inside the accepted skin.
# Only displace an overlay vertex forward when the near-front skin is within1mm.
bvh=BVHTree.FromPolygons(v.tolist(),t.tolist(),all_triangles=True)
conform=[]
for ob in preview:
    if ob.get('source_material_index')!=2:continue
    count=0;maxshift=0.
    for p in ob.data.vertices:
        x,y,z=p.co
        hit,_,_,_=bvh.ray_cast(Vector((x,-50,z)),Vector((0,1,0)),50)
        if hit is not None and abs(hit.y-y)<1.0:
            target=min(y,hit.y-.04);delta=y-target
            if delta>0:p.co.y=target;count+=1;maxshift=max(maxshift,delta)
    ob.data.update();conform.append({'object':ob.name,'vertices_moved':count,'maximum_forward_offset_mm':maxshift,'head_geometry_moved':False})

# Brows represent painted marks and must follow the scalp instead of floating
# like the original game overlay. Separate them from the naturally raised lashes.
features=json.loads((R/'source-reference/eye-feature-components.json').read_text())
browids=set(i for group in features['SOURCE_02_BROWS_LASHES'] if group['suggested_semantic']=='eyebrow' for i in group['object_vertex_indices'])
original=next(ob for ob in sourceobs if ob.get('source_material_index')==2)
ids=sorted(browids);reindex={v:i for i,v in enumerate(ids)}
polys=[poly for poly in original.data.polygons if all(i in browids for i in poly.vertices)]
bmsh=bpy.data.meshes.new('Conforming_Original_Eyebrows')
bmsh.from_pydata([original.data.vertices[i].co[:] for i in ids],[],[[reindex[i] for i in poly.vertices] for poly in polys]);bmsh.update()
buv=bmsh.uv_layers.new(name='Original_PMX_UV')
for newpoly,oldpoly in zip(bmsh.polygons,polys):
    for a,b in zip(newpoly.loop_indices,oldpoly.loop_indices):buv.data[a].uv=original.data.uv_layers.active.data[b].uv
    newpoly.use_smooth=True
for mat in original.data.materials:bmsh.materials.append(mat)
brows=bpy.data.objects.new('LOOK_Original_Eyebrows_Conformed',bmsh);eyecol.objects.link(brows)
brows['preview_only']=True;brows['head_geometry_moved']=False
sub=brows.modifiers.new('Subdivide painted brow for surface conformity','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=3;sub.render_levels=3
sw=brows.modifiers.new('Fit painted brows to unchanged v14 skin','SHRINKWRAP');sw.target=head;sw.wrap_method='NEAREST_SURFACEPOINT';sw.wrap_mode='ON_SURFACE';sw.offset=.025
lashes=next(ob for ob in preview if ob.get('source_material_index')==2)
bm=bmesh.new();bm.from_mesh(lashes.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i] for i in ids],context='VERTS');bm.to_mesh(lashes.data);bm.free();lashes.data.update()
conform.append({'object':brows.name,'source_eyebrow_vertices':len(ids),'method':'Simple subdivision level3 then nearest-surface shrinkwrap of eyebrow overlay only','offset_mm':.025,'head_geometry_moved':False})

ref.hide_render=True;ref.hide_viewport=True
haircol.hide_render=True;haircol.hide_viewport=True
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=40;scene.cycles.use_denoising=True;scene.cycles.transparent_max_bounces=16
scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.world=bpy.data.worlds.new('Soft Neutral Preview');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.23,.25,.29,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
scene.view_settings.view_transform='Standard'
for name,loc,power,size in [('Key',(-80,-140,180),170000,110),('Fill',(120,-90,80),110000,100),('Rim',(0,100,140),150000,90)]:
    ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.shape='DISK';ld.size=size
    ob=bpy.data.objects.new(name,ld);studio.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,35))-ob.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Appearance Review Camera');cam=bpy.data.objects.new('Appearance Review Camera',cd);studio.objects.link(cam);scene.camera=cam
cd.type='ORTHO';cd.clip_start=.1;cd.clip_end=3000;cd.ortho_scale=98
cam.location=(0,-200,35);cam.rotation_euler=(Vector((0,0,35))-cam.location).to_track_quat('-Z','Y').to_euler()
scene['preview_note']='v14 head/cap coordinates unchanged. Original March7 texture, eye surfaces and brows; optional source hair. Visual evaluation only. Original PRINT STL remains in v14 folder.'
scene['how_to_show_hair']='Enable viewport/render for collection03_Optional_Original_Hair_PREVIEW_ONLY.'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.object.select_all(action='DESELECT');head.select_set(True);bpy.context.view_layer.objects.active=head
for im in bpy.data.images:
    if im.source=='FILE' and not im.packed_file:im.pack()
assert before=={o.name:geometry(o)[2] for o in [head,cap]}
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT),compress=True)
# Verify persisted file, not only the in-memory scene.
bpy.ops.wm.open_mainfile(filepath=str(OUT))
after={name:geometry(bpy.data.objects[name])[2] for name in before}
assert before==after and sha(basefile)==basehash
report={'unpainted_blend_sha256':basehash,'preview_blend_sha256':sha(OUT),'source_reference_sha256':sha(SOURCE),'uv_transfer_sha256':sha(R/'uv-transfer/face-uv-transfer.npz'),'print_geometry_before':before,'print_geometry_after_saved_reload':after,'print_geometry_exactly_unchanged':before==after,'original_file_unchanged':sha(basefile)==basehash,'eye_brow_attachments_are_preview_only':True,'overlay_offsets':conform,'packed_images':[im.name for im in bpy.data.images if im.packed_file],'source_textures':'Original local PMX atlas; no generative image alteration.','head_material':'Exterior UV projection with faded matching skull skin; no transparency or displacement.'}
(R/'preview-build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('MAKEUP_PREVIEW_SAVED '+report['preview_blend_sha256'],flush=True)
