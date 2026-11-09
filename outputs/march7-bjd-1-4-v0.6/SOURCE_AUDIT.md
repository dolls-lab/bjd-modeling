源几何保护审计与重现

在本目录运行以下 Blender 后台脚本。它们只读取模型，输出数据或审计 JSON；不保存或改写 .blend / STL。

```sh
Blender -b -t 4 --python audit_source_preservation.py
```

审计输入已包含在本目录：`baseline-v0.5.blend`、`baseline-head.stl`、`baseline-cap.stl`、v6 模型与 STL、来源标签 NPZ、原保护权重 NPZ、新的 `head-visible-source-protection.npz`、原 PMX 脸片数组和构建报告。审计不依赖 `/tmp`。输出为 `source-preservation-review.json`。

审计会核对：v5 与 v6 的同索引顶点和多边形拓扑；master 原脸、耳廓、补片及共享边全部精确零位移；打印件可见源面雕和独立五官/下颌 ROI 精确零位移；颈部结构保护圆柱和各磁铁中心 7 mm 内的精确零位移；头盖和源参考不变；两版头壳与头盖 STL 的坐标、带朝向三角形集合和 Blender 一致。旧打印件全来源区域包含内壁，其变化仅作为信息报告，不再要求全部零位移。每个输入在审计前后核对哈希，构建中途变化时不会写出混合版本报告。

来源标签与保护 mask 可按顺序重新生成：

```sh
Blender -b -t 4 --python derive_source_provenance.py
Blender -b -t 4 --python make_side_protection.py
Blender -b -t 4 --python inspect_head_source_surfaces.py
Blender -b -t 4 --python make_visible_head_protection.py
```

来源标签脚本从 `parameters.json` 所指的本地原 PMX 读取脸材质，将耳正面和背面 UV 连通片与主脸区分，重建原 v3 建壳拓扑并执行相同 SUBSURF 2。只有逐多边形顶点索引匹配 v5 基线后才保存标签。原 PMX 文件需继续保留在配置路径；未复制进此目录。

`make_side_protection.py` 建立原来源保护档案。后续 `make_visible_head_protection.py` 保留 master 原档案不变，将打印件保护细分为：距实际 v5 master 不超过 0.65 mm 的源面/共享边映射点，加上独立既有眼鼻唇颊下颌 ROI。更远的源类别内腔点允许随外壳移动以保厚；旧 mask 保留。0.65 mm 阈值依据见 `head-source-surface-diagnostics.json`：按法线同向和非深内侧分类的脸部、耳部外表面最大距离分别约 0.2615、0.1954 mm；外侧原耳射线首击样本最大距离约 0.1129 mm。

master 与打印件各有按网格边长生成的 5 mm 测地距离及 smootherstep 权重。v6 构建实际采用的羽化宽度由 `parameters.json` 的 `postauricular_retraction.source_protection_feather_mm` 决定；距离缓存上限为 5 mm。内外壁如何使用相同位移场及机械排除由构建脚本决定，保护 mask 仅提供独立硬锁约束。

v6 没有 `z < 30 mm` 的整体保护断言：该区域中新增的侧脑壳是本轮允许修改的对象。原脸零新增位移仅指 v5→v6 保持，不表示打印网格与低面数原 PMX 逐点相同。最近表面误差与同索引位移分开报告；此审计不替代壁厚、视觉、打印或娃体实物试装检查。
