# 三月七四分 v18 · 仅唇缘微调

以用户更认可的 v16 为基准，单独保存小幅唇部试修版，等待外观确认。本次不重建嘴周曲面，不调整其他尺寸。

- [Blender 模型](march7-bjd-head-1-4-v18.blend)
- [主壳 STL](march7-head-shell-1-4-v18.stl) · [后盖 STL](march7-head-cap-1-4-v18.stl)
- [整体对比](whole-head-comparison.png) · [嘴部近景](mouth-closeup-comparison.png) · [侧面与侧光](side-light-comparison.png)
- [保留的 v16 基准](../v16-surface-fairing/README.md)

## 调整范围

原有唇部连同嘴缝一起小幅向内收，最大内收目标 0.12 mm；两端和上下边缘使用单个连续平滑包络渐隐。原嘴缝的左右与上下位置、嘴角坐标及嘴宽保持不变；不增加新浅槽或填补脸颊。

- 所有顶点的左右 X、上下 Z 坐标不变；仅唇缘局部沿 Y 向内。
- 左右嘴角固定；支撑范围以外的脸颊、下巴、鼻部、眼部和头壳坐标固定。
- 参数支撑范围为 `|X| < 4.5 mm`，相对弧形嘴缝 Z 偏移 `[-1.4, +2.0] mm`；嘴缝本身允许随嘴唇改变 Y，但 X/Z 不动。真实变化边界更小。
- 实际改变 3,204 / 252,695 个顶点（约 1.27%），最大位移约 0.120 mm；实际变化 X 为约 ±4.474 mm、Z 为约 8.491–12.358 mm。

这里的“保留脸型”指嘴唇范围外的原始面部几何逐点不变；嘴唇本身按要求微调。不能将局部坐标保护当作外观完全一致的判断，最终看同机位正面、斜侧、侧面及侧光对比。

## 核验与文件

[build-report.json](build-report.json)记录生成与重新打开后的网格一致性。[validation.json](validation.json)独立检查实际 STL 的局部范围、保护区、拓扑、法向和嘴部壁厚。

独立核验已通过：唇部支撑范围以外、嘴角邻颊、下巴及头壳主体坐标无变化，后盖 STL 字节一致。1,890 条有效壁厚样本的最低 Y 向厚度约 2.482 mm，最大减薄约 0.0049 mm；这不是全表面法向最小壁厚或实物强度证明。嘴唇只是轻微内收，原有唇缘仍可见，是否达到减弱嘟嘴感的程度待用户看图确认。

内外壁在同一 X/Z 位置使用相同的局部位移，再于内部深处渐隐。头壳仍是闭合空心结构，眼洞、后盖和颈部接口沿用 v16；未做实物打印与娃体试装。

渲染来自保存后的实际模型，统一相机、灯光、中性材质与曝光，只做拼版，无修图。源 v16 文件保持字节不变。

```sh
blender --background --python build_model.py
python3 validate_model.py
blender --background --python render_preview.py
python3 assemble_previews.py
```

Blender 4.5.9；验证依赖 NumPy、trimesh、manifold3d。实际控制字段见 [parameters.json](parameters.json) 的 `lip_adjustment`；头围及接口字段只记录沿用尺寸。来源限制见 [source-usage-rules.txt](source-usage-rules.txt)。
