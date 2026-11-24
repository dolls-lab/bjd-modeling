# 三月七四分 v16 · 嘴周连续曲面试修

本次只修改四分，供用户确认嘴周外观后再决定其他尺寸。三分与特六文件保持原样；四分 v14、v15 也完整保留。

用户指出 v15 嘴角至脸颊存在补块般的边缘。本版撤掉 v15 双侧局部填谷，保留其嘴唇收平处方，重新对较宽、连通的嘴周表面做曲面公平化：同时允许凸处回收与凹处舒展，使嘴周与脸颊连续相接。

- [打开 Blender 模型](march7-bjd-head-1-4-v16.blend)
- [主壳 STL](march7-head-shell-1-4-v16.stl) · [后盖 STL](march7-head-cap-1-4-v16.stl)
- [完整头部六视角](full-views/contact-sheet.png) · [单张全景原图](full-views/README.md)
- [嘴周近景对比](surface-closeup.png)
- [正面、斜侧、侧面及额外侧光对比](mouth-comparison.png) · [整体效果](whole-head-comparison.png)
- [上版四分 v15](../v15-mouth-soft/README.md) · [四分 v14 基础](../march7-bjd-1-4-v0.14/README.md)

头围、整体宽深高、眼洞、颈座、拉筋槽和后盖沿用四分基础尺寸。原 23 mm 假设颈球座、7 × 14 mm 槽未改，实物打印与适配仍待验证。

## 处理范围与方法

以 v14 的打印网格为基底，单独采样已保存的 lip_dy 收平嘴唇。嘴唇处方直接在实际顶点上求值，避免先放到较粗网格再插值使唇缘变形。v15 的 cheek_dy 不参与本次建模。

在中心 Z=12 mm、左右半径 13 mm、上下半径 8.5 mm 的连通区域上，求解带原表面位置约束的薄板平滑问题。边界外的表面、鼻部和中央唇部固定；通过整张局部曲面的弯曲能量来约束连接，而非把两个外凸位移块叠到脸上。最终网格只改变局部 Y（前后）坐标，X/Z 与拓扑不变。

中央唇部保护椭圆为 (X=0,Z=9.9) mm、半径 3.8 × 1.8 mm；鼻部保护椭圆为 (0,20) mm、半径 4 × 6 mm。边界和保护区共同参与求解；没有在求解后乘两个椭圆填块权重。参数见 [parameters.json](parameters.json)，求解结果见 [surface-field-report.json](surface-field-report.json)。

嘴角附近的表面和较宽的脸颊范围连续调整，因此本版与 v15 的局部几何不同，也不再是原 v14 脸部的严格等比复制。中央嘴唇沿用原收平处方，微笑轮廓及全头 X/Z 坐标保留。

## 检查与限制

[validation.json](validation.json)独立加载 STL，检查源文件哈希、X/Z 和范围外保护、鼻部核心、原嘴唇处方、闭合／连通／法向／退化面、嘴颊壁厚抽样、眼球和颈球包络及后盖配合。变形向内腔方向渐隐，部分较外侧位置内外壁的位移不同；报告分别记录最大增厚、最大减薄与最薄有效样本，不宣称全域壁厚严格不变。

壁厚是有限方向的 Y 向材料抽样，不是全表面法向最薄壁厚或打印强度证明。数字网格通过不能证明外观满意，因此额外保留同相机、同灯光及侧光的实际模型近景，由用户确认。PNG仅做排版，未修图。

## 复现

```sh
python3 prepare_surface.py
blender --background --factory-startup --python build_model.py
python3 validate_model.py
blender --background --factory-startup --python render_preview.py
python3 assemble_previews.py
```

Blender 4.5.9；独立求解／校验使用 Python 3.11、NumPy、SciPy、trimesh、manifold3d；拼图使用 Pillow。后续修改另存版本。原素材使用说明保留在 [source-usage-rules.txt](source-usage-rules.txt)。
