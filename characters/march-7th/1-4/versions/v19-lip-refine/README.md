# 三月七四分 v19 · 继续轻微收唇

以 v18 为基础另存的唇部微调版。嘴唇进一步向内收，减弱前突；原 v18 保留，其他尺寸未修改。当前等待用户看图确认外观。

- [Blender 模型](march7-bjd-head-1-4-v19.blend)
- [主壳 STL](march7-head-shell-1-4-v19.stl) · [后盖 STL](march7-head-cap-1-4-v19.stl)
- [整体对比](whole-head-comparison.png) · [嘴部近景](mouth-closeup-comparison.png) · [侧面及侧光](side-light-comparison.png)
- [原 v18](../v18-lip-only/README.md)

## 调整与保护范围

相对 v18，唇部最多额外内收 **0.0704 mm**，改变 3,199 / 252,695 个顶点。嘴缝随嘴唇一起小幅向内；嘴宽、嘴角以及所有顶点的左右 X、上下 Z 坐标不变。

唇部支撑范围沿用 v18：`|X| < 4.5 mm`，相对弧形嘴缝 `Z - (9.85 + 0.033*X²)` 在 `(-1.4, 2.0) mm` 内。真实变化源坐标 X 约 ±4.48 mm，Z 约 8.49–12.36 mm。范围以外的脸颊、下巴、鼻部、眼部和头型均逐点锁定；后盖字节不变。

此次只修改额外收唇的位移，不平滑或重建原来的脸部网格。过渡力度依据 v18 原有曲面的前后起伏控制，仅沿左右方向修顺收唇幅度，再以统一系数限制到每个位置原有的曲面余量以内，避免下唇收得过猛形成新的凹沟。内外壁采用同一局部位移场，并在内部深处渐隐。

这是保守微调，原有唇缘仍可见。周围坐标不变不等于视觉表情完全相同；是否达到减弱嘟嘴感的程度，以同角度截图和用户判断为准。

## 检查记录

- [生成记录](build-report.json)：实际模型保存、重新打开后网格一致；源 v18 未改写。
- [独立几何检查](validation.json)：实际 STL 的保护范围、拓扑、法向、位移与参数一致性均通过。主壳仍为闭合空心结构，眼洞、后盖、颈部接口未改。
- 9 条实际 STL 纵向剖面、0.025 mm 采样间隔，未增加显著度 ≥0.01 mm 的峰谷。这是有限采样检查，不是全表面平滑性的数学证明。
- 1,890 条有效嘴部 Y 向壁厚样本，最薄约 2.483 mm，最大减薄约 0.0092 mm；不代表全表面法向最小壁厚或实物强度。
- [渲染记录](render-provenance.json)：保存后的真实 v18/v19 网格，统一相机、灯光、中性材质及曝光；只拼版，无修图。
- [独立复核](independent-review.json) · [视觉检查](visual-review.json) · [源文件保护](source-integrity-after.json)。

本次未进行实物打印和娃体试装。头围及接口参数仅记录沿用尺寸。

## 重建

```sh
python3 prepare_lip_field.py
blender --background --python build_model.py
python3 validate_model.py
blender --background --python render_preview.py
python3 assemble_previews.py
```

Blender 4.5.9；准备/验证依赖 NumPy、SciPy、trimesh、manifold3d，拼版依赖 Pillow。实际控制字段见 [parameters.json](parameters.json) 的 `lip_adjustment`。来源说明见 [source-usage-rules.txt](source-usage-rules.txt)。
