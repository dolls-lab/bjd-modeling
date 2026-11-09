# 原脸 UV 转移（仅预览材质）

`face-uv-transfer.npz` 使用最终 v14 的 `head_after / head_triangles`，坐标和三角顺序不变。原 v14 Blend、STL、PMX 均只读。

- `head_uv_blender`：形状 `(505398, 3, 2)`，与每个三角的三个角对应；V 已从 PMX 转成 `1−v`，不要再次翻转。
- `head_makeup_weight`：形状 `(505398, 3)`，作为材质混合权重。0 为匹配肤色，1 为原 `脸.png`；不用作透明度。
- `skin_base_linear_rgb`：用于 Blender 材质颜色插槽。对应原额头取样 sRGB 约 `(242,213,202)/255`，已明确解码成线性 RGB。PNG 图像节点本身仍设为 sRGB。
- `head_vertices / head_triangles`：用于核对实际 PRINT 对应关系，不要求改变原网格。

映射使用固定历史坐标变换和最近原脸三角的重心插值，不做拟合缩放。原 face 材质有主脸、两耳前面、两耳背面共 5 个 UV 岛；跨岛三角单独处理，避免穿过图集中眼珠或眉睫色块。外表皮可见性、法向和距离遮罩避免内壁及后脑误投；原脸覆盖之外过渡为统一肤色。

`apply_face_material.py` 提供创建独立预览网格和材质的 Blender helper。若向原网格赋值，应按 `mesh.loop_triangles` 映射到 polygon loop；同一 quad 的两个三角在 UV 岛边界可能存在每角差异，应先核查重复 loop 值。不可把这组每三角 UV 直接当作每顶点 UV。

原眉毛、睫毛、眼白、虹膜、眼部阴影是独立 PMX 几何，由 `source-reference` 提供，不在此脸材质中生成。头皮不显示源脸图集中别的色块，眼洞内壁保持肤色。皮肤材质始终不透明。

`uv-check-*.png` 是无光照颜色诊断图，只有头壳，未装头盖、眼珠和眉睫；不是最终妆面效果图。最终预览由上层 scene 加入这些对象并渲染。

`uv-transfer-report.json` 记录源模型哈希、变换、遮罩和色彩规则；`uv-mask-review.json` 为独立核查。此流程不声称还原官方游戏着色器，不改变可打印模型。
