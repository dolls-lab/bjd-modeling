# 三月七三分 BJD 头壳 v1 · 基于四分 v14

以已确认的四分 v14 素头为来源，整体等比放大 **1.25 倍**，保留脸型、五官、眼洞、耳朵及头部弧线；局部扩大颈球座、下方颈部入口和拉筋槽。没有重新雕刻面部，没有全头平滑或重网格。

当前是未选定娃体的可调打样版。32 mm 球座按假设球头设计，不能据此认定适配某款三分娃体。

## 打开与查看

- [Blender 模型](march7-bjd-head-1-3-v1.blend)：只保留当前主头壳、后盖及查看用灯光／相机。单位为 mm。
- [头壳 STL](march7-head-shell-1-3-v1.stl) · [后盖 STL](march7-head-cap-1-3-v1.stl)：两件配套使用，STL 导入按毫米。
- [与原四分 v14 的尺寸对比](fourth-vs-third.png)：同一正交镜头下的正面、侧面。
- [六角度预览](third-multiview.png) · [颈口及内部](neck-interface.png)。

这是素头结构版本；原四分妆面及发型预览保持在 `../../../1-4/versions/march7-bjd-1-4-v0.14-makeup/`，没有覆盖。

## 本版尺寸

| 项目 | 三分 v1 |
| --- | ---: |
| 等比倍率 | 1.25 |
| 头围参考截面外轮廓 | 224.98 mm，约 22.5 cm |
| 头顶区紧绷皮尺凸包周长扫描最大值 | 约 226.01 mm |
| 归座后总宽 × 前后深 × 高 | 69.44 × 79.70 × 87.14 mm |
| 颈球座直径 | 32 mm |
| 球头假设直径／径向间隙 | 31.5 mm／0.25 mm |
| 拉筋槽 | 9 × 18 mm，长轴沿前后 Y 方向 |
| 球座顶部至内平台的名义厚度 | 4 mm |
| 眼珠球形包络参考直径 | 20 mm |
| 普通壳体名义厚度 | 3.25 mm，非全局最小厚度 |
| 后盖设计缝 | 0.3125 mm |
| 磁铁孔直径 × 深度 | 5.3125 × 2.75 mm |
| 定位销／配套盲孔直径 | 5／5.625 mm |

头围采用 v14 当前实际参考截面的约 179.98 mm 等比放大，不使用旧参数中已注明为历史目标的 190 mm。颈座球心向下调整，使球座顶部位置和 4 mm 名义余厚保持不变。参数里的 **90 mm 颈围只是待定设计参考**，没有把它除以 π 后当成球头直径。

头围选择参考厂商的三分实例：[ResinSoul Dai](https://www.resinsoul.com/05-chanpin/p-001-1.asp?id=355) 标注头围 21 cm、颈围 8 cm；[Dollmore Youth Eve / Mio](https://www.dollmore.net/Product/Detail/view/pid/21669) 标注头围 22.7 cm、颈围 7.2 cm。它们说明尺寸存在差异，不代表本版已适配这些娃体。本版约 22.5 cm 是保留三月七原比例并令原 16 mm 眼球包络对应约 20 mm 的打样选择。

## 核对范围

原四分 v14 文件哈希保持不变，新的 Blend 保存重开后网格一致。`validation.json` 从导出 STL 独立检查闭合、连通、朝向、退化／重复面、主壳与后盖配合、退出路径、颈孔及眼球包络；`neck-and-girth-review.json` 记录头围、外表面对照和颈圈径向抽样。

颈部之外的源／目标顶点按 1.25 倍做双向位置核对；后盖全部按等比核对。颈圈 6 个高度、24 个方向的有限径向抽样最小约 2.316 mm，不能代替全表面最薄壁厚或打印强度证明。原眼缘、磁铁附近等继承的局部薄处仍需试打检查。

实物打印、树脂收缩、磁铁装配、S 钩和实际颈球活动尚未验证。选定娃体后，需要颈顶球面直径／外形、插入高度和连接件规格，再调整接口；名义颈围单独不足以确认适配。

## 调整与复现

当前可直接驱动几何的参数位于 [parameters.json](parameters.json)：

- `uniform_scale`：整头及配套后盖等比倍率。
- `neck_seat_diameter_mm`：颈球座直径。
- `neck_roof_thickness_mm`：球座顶部至平台的名义厚度。
- `neck_slot_width_mm`、`neck_slot_length_mm`：拉筋槽宽、长。

其他头围、眼珠、壳厚、磁铁孔、定位结构及盖缝数字是本版说明／等比派生值，不能通过单改这些说明字段改变几何。身体颈围字段也仅记录待定参考。

为保留原头壳，本版构建器只扩大已有颈部孔腔；目标球座、槽不能小于等比后的 v14 原孔腔。若以后需要更小颈球，应另做适配内衬或局部重建颈座，不能用缩窄外脸来补偿。

后续改尺寸请复制到新的版本目录并更新参数，保留当前版本。运行顺序：

```sh
blender --background --factory-startup --python build_model.py
python3 validate_model.py
blender --background --factory-startup --python render_preview.py
python3 assemble_previews.py
```

建模使用 Blender 4.5.9；独立校验使用 Python 3.11、NumPy 2.0.2、SciPy 1.15.3、trimesh 5.2.0、manifold3d 3.5.4。拼图脚本使用 Pillow 和 macOS 的 STHeiti 字体。实际渲染 PNG 只做排版缩放，没有修图。

原素材说明见 [source-usage-rules.txt](source-usage-rules.txt)。
