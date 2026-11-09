# 原三月七头部参考资产

此文件只提取原 PMX 头部。原几何经统一毫米坐标变换，没有雕刻、补脑壳或眼球球面化；没有修改 v14。纹理已内嵌在 `source-reference.blend`，原图副本位于 `textures/`。

追加集合 `PMX_SOURCE_HEAD`，不要追加 `REFERENCE_PREVIEW_STUDIO`。脸、眼睛、头发、头饰分属独立子集合。每个物件都有 `source_material_index`、`source_material_name` 和 `source_asset_type` 属性。

| 编号 | 原材质 | 物件 | 用途 |
| --- | --- | --- | --- |
| 0 | 口腔 | SOURCE_00_MOUTH_INTERIOR | 原口腔 |
| 1 | 牙 | SOURCE_01_TEETH | 原牙齿 |
| 2 | 眉毛 | SOURCE_02_BROWS_LASHES | 眉毛与睫毛、眼睑覆盖层 |
| 3 | 眼白 | SOURCE_03_SCLERA | 原眼白表面片 |
| 4 | 眼睛 | SOURCE_04_IRIS_AND_HIGHLIGHT | 彩色虹膜、紫色瞳孔和白亮斑 |
| 5 | 眼睛1 | SOURCE_05_EYE_SHADOW | 原黑色半透明阴影，默认隐藏 |
| 6 | 脸 | SOURCE_06_FACE | 原脸片，没有完整后脑皮肤 |
| 26 | 头饰 | SOURCE_26_HEAD_ACCESSORY | 头饰；UV 超出 0..1，需 REPEAT |
| 28 | 头发 | SOURCE_28_HAIR | 原整套头发，单独开关 |
| 29 | 表情 | SOURCE_29_EXPRESSION_OPTIONAL | 可选表情覆盖层，默认隐藏 |

所有材质保留原贴图乘原 diffuse 及原透明度。节点 `SOURCE_TexturePreviewWeight` 取 1 为无光照贴图预览，取 0 为 Principled 受光材质。原人物与娃头应统一该取值、灯光和色彩管理。当前原贴图预览使用 Standard 色彩管理和 Emission 强度 1；不是游戏截图，也未复现 MMD 的 toon/sphere 着色。

## 眼睛与眉睫

- 视觉眼睛可整套取编号 3、4，保留分片相对位置和 UV。编号 5 的原 diffuse 为黑色、透明度 0.3；它是眼影，不能当作高光。
- 原眼不是闭合的 16 mm 球，物件中心也不是机械球心。若用白色 backing 球遮挡眼后空隙，应另按 v14 眼座坐标建立，并明确只是预览辅助。
- 编号 2 中两侧眉毛各 22 个顶点，中心约为 `(±11.222, -27.930, 38.789)` mm。其余分片属于睫毛或眼睑覆盖层。`eye-feature-components.json` 给出连通分片的物件内顶点索引和 UV 范围。
- 编号 4 每侧的 41 点主虹膜片使用原 UV 约 `u=.0313..2213, v=.7469..9575`；21 点紫色瞳孔片使用 `u=.2537..3296, v=.8775..9880`；20 点及 19 点白亮斑来自 `v≈.51` 的白色区。
- 若眉睫被 v14 光顺表皮遮挡，只对妆面副本做贴合或轻微外移，不改变素头。不要把整个原脸片叠在 v14 上冒充妆面；妆面应使用映射到 v14 外皮的原脸 UV。

## 坐标与复用

统一变换为 `(srcX, srcZ, srcY - 18.16621208190918) * 27.47544416498121`，单位 mm。原 PMX UV 转为 Blender `(u, 1-v)`；换轴产生反射，提取时已反转三角绕序并转换原法线。所有物件无几何 modifier。

`source-head-geometry.npz` 保存每个物件的原世界坐标、三角、原 PMX 顶点索引、原 UV 和 Blender UV。`asset-manifest.json` 记录源 PMX、贴图与 helper Blend 的 SHA，以及材质范围、坐标舍入量。

`original-texture-front/quarter/side.png` 是原几何与原贴图的真实渲染。`build_source_reference.py` 可从本机原 PMX 重建本参考文件；最终妆面场景另在上级目录生成。
