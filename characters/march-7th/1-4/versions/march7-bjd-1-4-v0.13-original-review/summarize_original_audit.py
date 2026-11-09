from pathlib import Path
import json,hashlib
import numpy as np
P=Path(__file__).parent;V=P.parent/'march7-bjd-1-4-v0.13'
a=json.loads((P/'face-audit.json').read_text());e=json.loads((P/'eye-original-comparison.json').read_text());c=json.loads((P/'face-contour-comparison.json').read_text());d=np.load(P/'face-distance-samples.npz');stl=V/'march7-head-shell-v0.13-draft.stl';blob=stl.read_bytes();n=int.from_bytes(blob[80:84],'little');dt=np.dtype([('normal','<f4',(3,)),('v','<f4',(3,3)),('a','<u2')]);v=np.frombuffer(blob,offset=84,dtype=dt,count=n)['v'].reshape(-1,3).astype(float);raw=d['source_vertices']
def tip(q):
 m=(abs(q[:,0])<=5)&(q[:,2]>=13)&(q[:,2]<=27)&(q[:,1]<-12);r=q[m];return r[np.argmin(r[:,1])]
t0=tip(raw);t1=tip(v)
a['nose_protrusion_extrema']={'original_tip_coordinate_mm':t0.tolist(),'v13_tip_coordinate_mm':t1.tolist(),'frontmost_Y_retreat_mm':float(t1[1]-t0[1]),'delta_xyz_mm':(t1-t0).tolist(),'definition':'Minimum Y among source/final vertices in |X|<=5,13<=Z<=27,Y<-12; true coordinate extrema of each piecewise-linear mesh, not index correspondence. The original sharp low-poly nose tip and rounded PRINT extremum need not be the same anatomical point.'}
a['eye_aperture_original_comparison']={'report':'eye-original-comparison.json','figure':'eye-original-comparison.png','sample_pitch_mm':e['sample_pitch_mm'],'eyes':[{'eye_id':q['eye_id'],'original':q['metrics']['raw_pmx'],'v13':q['metrics']['print_v13'],'changes':q['changes_print_minus_raw']} for q in e['eyes']],'pair_spacing':e['pair_spacing'],'warning':'Original zero-thickness skin aperture versus final through-hole includes wall/eyeball-seat occlusion. It proves effective openings differ; it is not a pointwise rim displacement measure.'}
a['main_face_contours']={'report':'face-contour-comparison.json','figure':'face-audit-overview.png','horizontal_sections':c['front_face_horizontal_sections'],'definition':c['section_definition']}
a['conclusion']={'exact_original_geometry_match':False,'summary_zh':'鼻口、下巴和主脸颊的表面大部分与原模型接近，但不是逐点原样。原始眼洞与当前有效通孔的轮廓和间距有可测差别；原鼻尖被圆顺。额头和太阳穴经过明确重塑，不能归入原始面雕完全一致。','major_skin_area_weighted_distance_median_range_mm':[min(a['source_to_final_surface'][k]['source_surface_area_weighted']['median_mm'] for k in ['nose','mouth_skin_2mm_geodesic_band','chin','main_cheeks']),max(a['source_to_final_surface'][k]['source_surface_area_weighted']['median_mm'] for k in ['nose','mouth_skin_2mm_geodesic_band','chin','main_cheeks'])],'no_model_changes_made':True}
assert hashlib.sha256(stl.read_bytes()).hexdigest()==a['files']['head_stl']['sha256'];(P/'face-audit.json').write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
names=[('鼻部','nose'),('嘴周皮肤（原唇边测地2mm）','mouth_skin_2mm_geodesic_band'),('下巴','chin'),('主脸颊','main_cheeks'),('原眼缘周围皮肤2mm带','original_eye_skin_2mm_band'),('中额35–45mm','central_forehead_Z35_to45'),('太阳穴非五官皮肤','temple_nonfeature_skin'),('高额45mm以上','high_forehead_Z45_plus')]
rows=[]
for name,key in names:
 q=a['source_to_final_surface'][key];s=q['source_surface_area_weighted'];rows.append(f"| {name} | {s['median_mm']:.3f} | {s['p95_mm']:.3f} | {q['maximum_over_source_vertices_and_surface_samples_mm']:.3f} |")
txt='''# 原始三月七 PMX → v13 面部核对

结论：**面雕来源明确，主要鼻口、脸颊、下巴表面接近原模型，但不能称“与原模型完全一致”或“从未改变五官”。** 眼洞和鼻尖有明确的几何差异；额颞部属于后续重塑。

直接读取原 PMX「脸」材质的 2176 个三角形，以固定变换 `[X,Z,Y−18.16621208190918]×27.47544416498121` 对照最终 v13 STL。没有重新拟合、配准或改尺度，也没有用 v12→v13 不动的记录代替此核对。模型和旧报告均未改动。

## 原始皮肤到最终表面的距离

单位 mm。中位数与95百分位按原始三角面积加权；最大值取原始顶点与面内采样的最大观测值，不是全连续表面的严格上界。距离是到最近三角面的距离，不是相同点的位移。

| 分区 | 中位数 | 95百分位 | 最大观测值 |
|---|---:|---:|---:|
'''+ '\n'.join(rows)+f'''

大部分鼻口、下巴和主脸颊的距离中位数约 0.019–0.032 mm；这与原表面整体接近，但局部尖点/边缘仍有更大变化。原鼻尖到当前最近表面约 **0.477 mm**；两者各自最前端沿 Y 方向差约 **{float(t1[1]-t0[1]):.3f} mm**，体现尖点被圆顺。原下巴最底点到当前皮肤约 0.070 mm。

额头/太阳穴按独立分区展示。其大变化来自历次头颅衔接和额顶重塑，不能用主脸颊的小误差代表整张原脸片。

## 眼洞与眼距

在相同坐标、相同深度的 +Y 射线投影下，网格间距0.05 mm：

| 指标 | 原 PMX | v13 |
|---|---:|---:|
| 单眼宽×高 | 11.50×9.30 mm | 11.00×9.55 mm |
| 单眼有效面积 | 81.6575 mm² | 82.395–82.4175 mm² |
| 两眼面积质心的水平间距 | 27.1152 mm | 26.6473 mm |

主要变化是外眼角收窄。各眼面积质心向内约0.234 mm、向上约0.080–0.084 mm；轮廓重合度约92.6%。原31点眼洞环与原始三角投影互相验证一致；独立的8点上睑细缝已排除，未误当成主眼洞。

原模型是零厚皮肤，v13是带壁厚和眼窝的通孔。上述差异也包含厚度遮挡，不能全部解释为外眼皮向内移动；同样，皮肤最近距离小也不能证明眼洞边缘不变。

## 脸颊和下巴轮廓

固定 Z=4/8/12/16/20/24/28 mm 的前脸横截面，仅保留Y≤−8mm以排除后脑/耳部。Z4–24的总宽差约−0.251至+0.017 mm；Z28的上颊/眼外侧截面总宽增加约0.565 mm。此定义是前脸截面，不能冒充整头轮廓或每个角度的剪影。中线鼻唇侧面曲线见图。

## 文件与重现

- `face-audit.json`：完整双向距离、采样/区域定义、原鼻尖/下巴查询、输入SHA和结论。
- `face-audit-overview.png`：主要面部差异热图、中线侧面与前脸横截线。
- `eye-original-comparison.json/png`：原始眼洞与实际通孔、眼距对比。
- `face-contour-comparison.json`：截线原始测量。
- `audit_original_face.py`：Blender背景运行，直接读PMX/STL；只写本核对目录。
- `compare_original_eyes.py`、`review_original_contours.py`、`summarize_original_audit.py`：眼洞、截线和说明脚本。

局限：这些数字不是“相似度评分”；原模型的材质、眼白/眼珠、眉毛、睫毛及头发未包含在皮肤几何核对中。反向统计限定双方可见前皮肤，排除内腔及原开口中新增的填面。原始面片没有完整后脑，因此无法据此宣称整个BJD头是官方原头壳。

最终头壳 SHA-256：`{a['files']['head_stl']['sha256']}`。
'''
(P/'README.md').write_text(txt);print('Final original review summary written; model files unchanged.')
