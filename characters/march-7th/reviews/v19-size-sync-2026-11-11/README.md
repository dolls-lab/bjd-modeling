# 三月七 v19 · 三尺寸同步

2026-11-11 用户确认四分 v18 和 v19 都保留，并指定三分、特六以四分 v19 为基础。此次新增三分 v3 与特六 v4；历史版本文件不改写。

| 尺寸 | 最新模型 | 相对四分 v19 比例 | 参考头围 | 颈座直径 | 颈槽宽 × 长 |
| --- | --- | --- | --- | --- | --- |
| 四分 | [v19 Blender](../../1-4/versions/v19-lip-refine/march7-bjd-head-1-4-v19.blend) | 1 | 约 18 cm | 23 mm | 7 × 14 mm |
| 三分 | [v3 Blender](../../1-3/versions/v3-from-v19/march7-bjd-head-1-3-v3.blend) | 1.25 | 约 22.5 cm | 32 mm | 9 × 18 mm |
| 特六 | [v4 Blender](../../1-6-special/versions/v4-from-v19/march7-bjd-head-1-6-special-v4.blend) | 0.8889703623 | 约 16 cm | 21 mm | 6.5 × 13 mm |

三分和特六均直接读取完整的四分 v19 头壳和后盖等比调整，仅在颈口附近局部重建接口。继承 v19 的嘴唇、脸颊和头型，不再叠加旧三分 v2、特六 v3 的嘴周修改。

头围在既定参考截面测量；这里的三分、特六是尺寸分类。两版仍未选定具体娃体，沿用既有可调打样参数，没有新增实物适配结论。参数、STL 和各自检查记录见 [三分 v3 说明](../../1-3/versions/v3-from-v19/README.md)、[特六 v4 说明](../../1-6-special/versions/v4-from-v19/README.md)。

## 同角度截图

[完整头部：正面、斜侧](three-sizes-overview.png) · [嘴部近景与正侧面](face-and-side-comparison.png)

三列依次为四分 v19、三分 v3、特六 v4。画面中统一头部大小，便于直接核对面雕和头型；不表示实际尺寸相同。渲染来自已保存模型，统一相机相对位置、材质和光照，不做修图。

## 核验

- 对实际 STL 做缩放后的面部／头型保护区比较；颈部接口局部单独核验，后盖全域比较。
- 每版检查闭合拓扑、眼球包围体、颈座与槽口、后盖装配和离散开盖路径。
- [三分独立复核](../../1-3/versions/v3-from-v19/independent-review.json) · [特六独立复核](../../1-6-special/versions/v4-from-v19/independent-review.json)。
- [渲染溯源](render-provenance.json) · [拼版溯源](board-provenance.json) · [历史文件保护](source-integrity-after.json)。

数字网格与离散采样验证不能代替实际打印、装配与强度验证。

保留的 [四分 v18](../../1-4/versions/v18-lip-only/README.md) 与 [四分 v19](../../1-4/versions/v19-lip-refine/README.md) 文件保持不变；它们目录内“待确认”的文字是生成当时的历史记录，当前确认状态以本页及角色总览为准。
