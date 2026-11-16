"""Read saved .blend and independent exported STLs; do not save or change inputs."""
from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'/private/tmp/bjd-hook-groove-deps')
import bpy,numpy as np,trimesh
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(tri):
 a=np.asarray(tri,dtype=np.float32).copy();a[a==0]=0
 return hashlib.sha256(np.sort(np.sort(a.view('V12').reshape(-1,3),axis=1).reshape(-1).view('V36')).tobytes()).hexdigest()
def arrays(o):
 o.data.calc_loop_triangles()
 v=np.array([list(o.matrix_world@vv.co) for vv in o.data.vertices],float)
 f=np.array([list(p.vertices) for p in o.data.loop_triangles],int)
 return v,f

def run(folder):
 d=Path(folder).resolve();p=json.loads((d/'parameters.json').read_text());src=d.parents[2]/p['source_directory']
 paths={'parameters':d/'parameters.json','blend':d/p['output_files']['blend'],'source_blend':src/p['source_files']['blend'],'head':d/p['output_files']['head'],'cap':d/p['output_files']['cap']}
 before={k:sha(v) for k,v in paths.items()};refs={}
 bpy.ops.wm.open_mainfile(filepath=str(paths['source_blend']))
 for name in ['REFERENCE_ONLY_S_HOOK_NOT_FOR_PRINT','REFERENCE_ONLY_CORD_NOT_FOR_PRINT']:
  o=bpy.data.objects[name];refs[name]=arrays(o)
 bpy.ops.wm.open_mainfile(filepath=str(paths['blend']));parts={};references={}
 for k,name in [('head','PRINT_01_Head_Shell'),('cap','PRINT_02_Removable_Cap')]:
  o=bpy.data.objects[name];v,f=arrays(o);tm=trimesh.load_mesh(paths[k],process=True,validate=False)
  parts[k]={'triangles_match_export':canonical(v[f])==canonical(tm.triangles),'blend_triangle_sha256':canonical(v[f]),'stl_triangle_sha256':canonical(tm.triangles),'modifiers':len(o.modifiers)}
 for name,old in refs.items():
  o=bpy.data.objects.get(name)
  if o is None:references[name]={'pass':False,'missing':True};continue
  v,f=arrays(o);references[name]={'vertices_same':np.array_equal(v,old[0]),'faces_same':np.array_equal(f,old[1]),'hidden':bool(o.hide_render and o.hide_get()),'not_for_print':bool(o.get('not_for_print'))}
  references[name]['pass']=all(references[name].values())
 unchanged=all(sha(paths[k])==h for k,h in before.items())
 report={'version':p['version'],'audit_script_sha256':sha(Path(__file__)),'input_hashes':before,'parts':parts,'references':references,'inputs_unchanged':unchanged,'pass':bool(unchanged and all(v['triangles_match_export'] and v['modifiers']==0 for v in parts.values()) and all(v['pass'] for v in references.values()))}
 (HERE/f"audit-blend-{p['version']}.json").write_text(json.dumps(report,indent=2)+'\n');print('BLEND_AUDIT',p['version'],report['pass'],flush=True)
 return report['pass']
if __name__=='__main__':
 for f in sys.argv[sys.argv.index('--')+1:]:assert run(f)
