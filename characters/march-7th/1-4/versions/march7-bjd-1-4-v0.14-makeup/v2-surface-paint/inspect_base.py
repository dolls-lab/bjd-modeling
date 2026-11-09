from pathlib import Path
import bpy,json
R=Path(__file__).resolve().parent
P=R.parent.parent/'march7-bjd-1-4-v0.14/march7-bjd-head-v0.14-draft.blend'
bpy.ops.wm.open_mainfile(filepath=str(P))
data={}
for name in ['PRINT_01_Head_Shell','PRINT_02_Removable_Cap']:
    ob=bpy.data.objects[name]
    data[name]={'matrix':[list(x) for x in ob.matrix_world],'modifiers':[(m.name,m.type) for m in ob.modifiers],'materials':[]}
    for mat in ob.data.materials:
        item={'name':mat.name,'diffuse_color':list(mat.diffuse_color),'nodes':[]}
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                nd={'name':node.name,'type':node.type,'inputs':{}}
                for inp in node.inputs:
                    if hasattr(inp,'default_value'):
                        v=inp.default_value
                        try:v=list(v)
                        except TypeError:pass
                        if isinstance(v,(list,str,float,int,bool)):nd['inputs'][inp.name]=v
                item['nodes'].append(nd)
        data[name]['materials'].append(item)
(R/'base-material-inspection.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(data,ensure_ascii=False))
