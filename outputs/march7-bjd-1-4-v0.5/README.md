# 三月七四分 BJD · v0.5 原角色面雕与脑壳衔接版

以用户偏好的 **v0.3** 为基底，面雕以本地三月七原始 PMX 为依据，整体头型和耳周连续性参考成熟二次元素头。修整脸与脑壳的交界，不继续 v0.4 的整体椭球圆化，不把其他娃头的脸形混入三月七。

参考依据见 design-reference-notes.md。预览使用与 v0.3 相同的材质、灯光和镜头。

## 文件

- march7-bjd-head-v0.5-draft.blend：新版 Blender 编辑场景。
- march7-head-shell-v0.5-draft.stl、march7-head-cap-v0.5-draft.stl：打印主体和后脑盖。
- preview-*.png：外观、内部和前后对照。
- build_head.py、solve_junction.py、parameters.json：接面生成程序、平滑求解器和参数。
- baseline-v0.3.blend、baseline-build-report.json、baseline-cap.stl：重建输入，不是新增打印件。
- source-protection-masks.npz：依据原 PMX 的面雕保护区。
- baseline-source-audit.json：原始面雕到 v0.3 的误差审计。
- head-protection-weights.npz：打印网格的面雕保护区与羽化权重。
- source-faithfulness-review.json：新版相对 v0.3 的真实对应顶点位移及原 PMX 最近表面误差。
- transition-profile-review.json：额头、太阳穴与耳侧的截面对比。
- validation.json：导出 STL 的闭合、拓扑、分件、孔洞、头围与球眼检查。
- face-opening-comparison.json：相对 v0.3 的眼洞投影比较。
- eye-insertion-check.json：从后口装入 16 mm 球眼的连续运动检查。

STL 按 **mm** 导入。Blender 场景单位比例 0.001，勿再放大 1000 倍。仅打印 PRINT_01_Head_Shell 与 PRINT_02_Removable_Cap；隐藏参考与基线输入不打印。

## 面雕保持的含义

原角色脸网格直接参与建模。v0.3 为打印做了细分、补动画缺口、闭嘴和空心实体化，并非原始低面数顶点的逐点复制。原始脸到 v0.3 最近表面距离已审计：眼周 P95 约 0.133 mm、鼻部 0.113 mm、唇周 0.200 mm、面颊 0.214 mm；最近表面距离不等于对应顶点位移。

本次锁定眼鼻唇、面颊、下颌及耳廓。允许调整原脸外周约 8 mm 的上额与侧面接面带，五官保护区优先于这条范围；原角色的低面数上额边缘与新增脑壳在这里形成平滑过渡。原脸内部以连续插值的边界距离识别，避免逐三角面划分造成台阶。

平滑采用有位置约束的最小弯曲求解，随后把同一位移场传到内外壳层。耳后下方 z≤30 mm 保留 v3，30–38 mm 逐渐加入修整，避免在耳后制造新的横痕。后盖与机械连接区保留。具体位移、保护区零位移及源模型误差见 source-faithfulness-review.json，不把“保持 v3 面雕”等同于“与原 PMX 逐点相同”。

原 PMX 五官区与 v3 之间的打印化差异在本次没有增加。允许调整的外周带仍有变化，报告单列历史 4 mm 内区与当前 8 mm 内区，避免把扩大接面范围说成整张原脸完全未动。

## 重建

保持基线与保护区文件完整，用 Blender 4.5：

```sh
blender --background --factory-startup -t 4 --python make_head_protection.py
blender --background --factory-startup -t 4 --python build_head.py -- --export-fairing
python solve_junction.py
blender --background --factory-startup -t 4 --python build_head.py
python validate_mesh.py --check-eye-clearance
python check_eye_insertion.py
python compare_eye_apertures.py --pitch-mm 0.05
blender --background --factory-startup -t 4 --python render_detail_comparison.py
```

求解和验证依赖 numpy、scipy、trimesh、manifold3d、Pillow；眼孔比较还需 v0.3 文件夹。参数中的原 PMX 路径用于来源核查，换电脑须更新。junction_fairing 控制接面修整；其他尺寸字段是继承记录，改颈座、五金或眼珠需要回到完整建模流程。

## 尺寸及装配

目标头围约 190 mm，本版指定水平截面的实测外轮廓为 **188.14 mm**（原定 ±2 mm 范围内），16 mm 球眼，配 UFdoll 四分囡囡体。颈围参考 66 mm；23 mm 球面颈座和 7 × 14 mm 拉筋槽为可调打样设计，未取得原厂接口尺寸。四颗 4 × 2 mm 磁铁分置主体与盖，孔径 4.25 mm、深 2.2 mm；定位柱 Ø4 mm、盲孔 Ø4.5 mm。

从后方拆盖，球眼先经开口中央进入再移向眼窝，粘磁铁前确认极性。数字球眼不含眼柄、凸虹膜、眼泥、手指或工具。

**仍为未实物打印和试装的打样版。** 数字检查不能保证收缩、材料强度、磁铁胶层、颈球与拉筋配合。倾斜接缝的浮点接触片单独分类并保留原始体积；头围仅在二维测量时闭合 0.00001 mm 精度微隙，不改打印 STL。

原模型版权 miHoYo，编辑神帝宇。原使用说明注明允许改造、非商业和勿二次配布，见 source-usage-rules.txt。本次仅本地保存，未上传或公开发布。
