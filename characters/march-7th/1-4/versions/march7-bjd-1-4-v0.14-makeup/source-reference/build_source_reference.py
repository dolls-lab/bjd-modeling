"""Extract the original PMX head with original UV/textures into an appendable helper.
No BJD model is opened or edited. Original source positions are only transformed
by the established uniform millimetre transform. Shader is a Blender texture
reconstruction, not the game's or MMD's shader.
"""
from pathlib import Path
import sys,json,hashlib,shutil
import numpy as np,bpy
from mathutils import Vector
R=Path(__file__).resolve().parent;OUT=R.parent;V14=OUT.parent/'march7-bjd-1-4-v0.14';BASE=OUT.parent/'march7-bjd-1-4-v0.3'
sys.path.insert(0,str(BASE));from parse_pmx import load_pmx
SOURCE=Path(json.loads((V14/'parameters.json').read_text())['source_pmx']);SCALE=27.47544416498121;CHIN=18.16621208190918
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();src=load_pmx(SOURCE)
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
main=bpy.data.collections.new('PMX_SOURCE_HEAD');scene.collection.children.link(main)
collections={}
for k in ['PMX_SOURCE_FACE','PMX_SOURCE_EYES','PMX_SOURCE_HAIR','PMX_SOURCE_ACCESSORY','PMX_OPTIONAL_EXPRESSION']:
 c=bpy.data.collections.new(k);main.children.link(c);collections[k]=c
names={0:('SOURCE_00_MOUTH_INTERIOR','PMX_SOURCE_FACE'),1:('SOURCE_01_TEETH','PMX_SOURCE_FACE'),2:('SOURCE_02_BROWS_LASHES','PMX_SOURCE_FACE'),3:('SOURCE_03_SCLERA','PMX_SOURCE_EYES'),4:('SOURCE_04_IRIS_AND_HIGHLIGHT','PMX_SOURCE_EYES'),5:('SOURCE_05_EYE_SHADOW','PMX_SOURCE_EYES'),6:('SOURCE_06_FACE','PMX_SOURCE_FACE'),26:('SOURCE_26_HEAD_ACCESSORY','PMX_SOURCE_ACCESSORY'),28:('SOURCE_28_HAIR','PMX_SOURCE_HAIR'),29:('SOURCE_29_EXPRESSION_OPTIONAL','PMX_OPTIONAL_EXPRESSION')}
v=src['vertices'];world=np.column_stack([v[:,0],v[:,2],v[:,1]-CHIN])*SCALE;normals=src['normals'][:,[0,2,1]];images={};texrecs=[];mats=[];arrays={};maxround=0.
for mi,(name,collection) in names.items():
 spec=src['materials'][mi];faces=src['faces'][spec['start']:spec['end']];ids=np.unique(faces);mapping=np.full(len(v),-1,int);mapping[ids]=np.arange(len(ids));ff=mapping[faces][:,::-1]
 mesh=bpy.data.meshes.new(name+'_Geometry');mesh.from_pydata(world[ids].tolist(),[],ff.tolist());mesh.update();uv=mesh.uv_layers.new(name='Original_PMX_UV')
 for loop in mesh.loops:
  u,vv=src['uvs'][ids[loop.vertex_index]];uv.data[loop.index].uv=(float(u),1-float(vv))
 for poly in mesh.polygons:poly.use_smooth=True
 mesh.normals_split_custom_set_from_vertices(normals[ids].tolist())
 ob=bpy.data.objects.new(name,mesh);collections[collection].objects.link(ob);ob['source_material_index']=mi;ob['source_material_name']=spec['name'];ob['source_asset_type']={0:'mouth_interior',1:'teeth',2:'brows_and_lashes',3:'sclera_surface',4:'iris_and_highlight',5:'translucent_eye_shadow',6:'original_face_skin',26:'head_accessory',28:'hair',29:'optional_expression'}[mi];ob['source_geometry_unmodified']=True;ob['source_transform']='(X,Z,Y-18.16621208190918)*27.47544416498121 mm';ob['source_pmx_sha256']=sha(SOURCE)
 if mi in (5,29):ob.hide_render=True;ob.hide_viewport=True;ob['optional_overlay']='Original translucent eye shadow or expression overlay, retained but hidden by default for the makeup preview.'
 coords=np.array([p.co[:] for p in mesh.vertices]);err=float(np.max(np.abs(coords-world[ids])));maxround=max(maxround,err)
 mat=bpy.data.materials.new('SOURCE_MAT_%02d_'%mi+spec['name']);mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
 output=nodes.new('ShaderNodeOutputMaterial');lit=nodes.new('ShaderNodeBsdfPrincipled');lit.inputs['Roughness'].default_value=.5 if mi==4 else .85;lit.inputs['Specular IOR Level'].default_value=.25
 emission=nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1
 mode=nodes.new('ShaderNodeValue');mode.name='SOURCE_TexturePreviewWeight';mode.label='0 = lit material; 1 = original texture preview';mode.outputs[0].default_value=1
 shader=nodes.new('ShaderNodeMixShader');links.new(mode.outputs[0],shader.inputs[0]);links.new(lit.outputs['BSDF'],shader.inputs[1]);links.new(emission.outputs[0],shader.inputs[2])
 trans=nodes.new('ShaderNodeBsdfTransparent');alpha_mix=nodes.new('ShaderNodeMixShader');links.new(trans.outputs[0],alpha_mix.inputs[1]);links.new(shader.outputs[0],alpha_mix.inputs[2]);links.new(alpha_mix.outputs[0],output.inputs['Surface'])
 ti=spec['texture_index'];tp=SOURCE.parent/src['textures'][ti].replace('\\','/') if ti>=0 else None
 if tp:
  if tp not in images:
   im=bpy.data.images.load(str(tp),check_existing=True);im.colorspace_settings.name='sRGB';im.pack();images[tp]=im
   dest=R/'textures'/tp.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(tp,dest);texrecs.append({'original_path':str(tp),'copy':str(dest.relative_to(R)),'sha256':sha(tp),'size_px':list(im.size),'packed_in_blend':True})
  tex=nodes.new('ShaderNodeTexImage');tex.name='SOURCE_ORIGINAL_TEXTURE';tex.image=images[tp];tex.interpolation='Linear';tex.extension='REPEAT'
  col=nodes.new('ShaderNodeMixRGB');col.blend_type='MULTIPLY';col.inputs[0].default_value=1;col.inputs[2].default_value=spec['diffuse'];links.new(tex.outputs['Color'],col.inputs[1]);links.new(col.outputs[0],lit.inputs['Base Color']);links.new(col.outputs[0],emission.inputs['Color'])
  alpha=nodes.new('ShaderNodeMath');alpha.operation='MULTIPLY';alpha.inputs[1].default_value=spec['diffuse'][3];links.new(tex.outputs['Alpha'],alpha.inputs[0]);links.new(alpha.outputs[0],alpha_mix.inputs[0])
 else:
  lit.inputs['Base Color'].default_value=spec['diffuse'];emission.inputs['Color'].default_value=spec['diffuse'];alpha_mix.inputs[0].default_value=spec['diffuse'][3]
 mat['original_diffuse_rgba']=spec['diffuse'];mat['texture_preview_control']='SOURCE_TexturePreviewWeight: 1 emission texture preview, 0 principled lit';mesh.materials.append(mat)
 mats.append({'index':mi,'original_material':spec['name'],'object':name,'collection':collection,'material':mat.name,'vertices':len(ids),'triangles':len(ff),'original_face_range':[spec['start'],spec['end']],'diffuse_rgba':spec['diffuse'],'texture':str(tp) if tp else None,'uv_original_minmax':[src['uvs'][ids].min(0).tolist(),src['uvs'][ids].max(0).tolist()],'bounds_mm':[world[ids].min(0).tolist(),world[ids].max(0).tolist()],'default_visible':mi not in (5,29),'float32_roundoff_max_mm':err})
 arrays[name+'_vertices']=world[ids];arrays[name+'_triangles']=ff;arrays[name+'_source_vertex_ids']=ids;arrays[name+'_original_uv']=src['uvs'][ids];arrays[name+'_blender_uv']=np.column_stack([src['uvs'][ids,0],1-src['uvs'][ids,1]])
scene['reference_notice']='Original PMX head geometry and textures. Not a printable16mm eyeball assembly or game screenshot. SOURCE_05 is black0.3alpha shadow, not highlight. Head skin lacks full rear scalp.'
main['source_pmx_sha256']=sha(SOURCE);main['units']='mm';main['default_shader_mode']='Original texture emission preview; change SOURCE_TexturePreviewWeight to0 for lit.'
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.cycles.transparent_max_bounces=16
scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
scene.world=bpy.data.worlds.new('Reference background');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.13,.16,.2,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
studio=bpy.data.collections.new('REFERENCE_PREVIEW_STUDIO');scene.collection.children.link(studio)
camdata=bpy.data.cameras.new('Source reference camera');cam=bpy.data.objects.new('Source reference camera',camdata);studio.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=125;camdata.clip_start=.1;camdata.clip_end=3000
views=[('front',(0,-180,27),(0,0,27)),('quarter',(115,-180,85),(0,0,27)),('side',(180,0,32),(0,0,27))]
cam.location=views[0][1];cam.rotation_euler=(Vector(views[0][2])-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(R/'source-reference.blend'),compress=True)
np.savez_compressed(R/'source-head-geometry.npz',**arrays)
manifest={'source_pmx':str(SOURCE),'source_pmx_sha256':sha(SOURCE),'source_blend':'source-reference.blend','source_blend_sha256':sha(R/'source-reference.blend'),'append_collection':'PMX_SOURCE_HEAD','units':'mm','transform':{'scale':SCALE,'chin_source_y':CHIN,'formula':'world=(srcX,srcZ,srcY-chin)*scale','winding_reversed_after_axis_reflection':True,'blender_uv':'(u,1-v)'},'textures':texrecs,'materials':mats,'max_geometry_float32_roundoff_mm':maxround,'unmodified_geometry':True,'modifiers':[],'excluded_material_indices':[i for i in range(len(src['materials'])) if i not in names],'warnings':['Original eyes are eye patches/surfaces, not closed16mm physical eyeballs; use BJD seat centers from v14 build-report for spheres.','SOURCE_02 contains both brows and eyelashes. SOURCE_04 contains iris plus white highlight pieces. SOURCE_05 black diffuse/alpha0.3 is an upper-eye shadow.','Original head accessory UV exceeds1 and wraps with REPEAT; do not clamp.','Original alpha0.3 eye shadow and expression overlay are optional and hidden by default per preview design; raw material remains intact.','Shader preserves original texture×diffuse and alpha, but does not reproduce original toon/sphere shader or game lighting.','Source face does not contain complete rear scalp; reference hair is separate from the accepted v14 cranial volume.'],'previews':[f'original-texture-{n}.png' for n,_,_ in views]}
(R/'asset-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print('SOURCE_REFERENCE_SAVED '+manifest['source_blend_sha256'],flush=True)
for name,loc,target in views:
 cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(R/f'original-texture-{name}.png');bpy.ops.render.render(write_still=True)
assert sha(SOURCE)==manifest['source_pmx_sha256'];print('SOURCE_REFERENCE_RENDER_DONE',flush=True)
