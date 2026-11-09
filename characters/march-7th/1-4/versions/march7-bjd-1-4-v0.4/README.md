# 三月七四分 BJD 头壳 · v0.4 额头与太阳穴圆顺版

在 v0.3 面部修整版上，重塑面部连接脑壳的宽区域：将前额至头顶、太阳穴至侧脑的截面逐渐过渡为平滑椭圆弧。重点修正原连接处偏方、突然转弯的轮廓。

本版直接变形已验证的 v0.3 网格，不重建拓扑。保持高度 Z 不变，以同一位移场调整内外壁；五官所在的 z≤35 mm 区域、耳廓保护区、颈座、定位柱和磁铁座保留。后盖 STL 与 v0.3 完全相同，分盖位置仍在耳后。额颞部的过渡带使用二阶连续权重，实际效果用相同灯光、材质和相机的渲染及截面复核。

## 文件

- `march7-bjd-head-v0.4-draft.blend`：新版可编辑场景。
- `march7-head-shell-v0.4-draft.stl`：打印主体。
- `march7-head-cap-v0.4-draft.stl`：后脑盖，与前版相同。
- `preview-comparison.png`、`preview-side-comparison.png`：修改前后对照。
- `parameters.json`、`build_head.py`：本版变形参数和重建脚本。
- `baseline-v0.3.blend`、`baseline-build-report.json`、`baseline-cap.stl`：用于重建的前版输入，不是另外需要打印的零件。
- `validation.json`、`validate_mesh.py`：新 STL 的独立检查结果和脚本。
- `face-opening-comparison.json`、`compare_eye_apertures.py`：v0.3 与 v0.4 眼孔射线投影对比。
- `eye-insertion-check.json`、`check_eye_insertion.py`：16 mm 球眼安装路径检查。
- `build-report.json`：位移范围、机械参数与网格统计。
- `cranium-profile-review.json`、`cranium-profile-comparison.png`：实际导出轮廓的前后对照与保护区核查。

所有 STL 数值按 **mm** 导入。Blender 的单位比例为 0.001；勿再放大 1000 倍。场景中仅 `PRINT_01_Head_Shell` 与 `PRINT_02_Removable_Cap` 属于打印件。隐藏对象是原始脸参考和编辑用外表面。

## 重建

保持文件夹内基线输入齐全，使用 Blender 4.5：

本版由 `cranium_rounding` 参数驱动额颞部变形；其余尺寸字段记录基线结构。修改眼珠、颈座或磁铁规格需要回到原完整建模流程或直接编辑网格，不能仅改这些记录字段。

```sh
blender --background --factory-startup -t 4 --python build_head.py
python validate_mesh.py --check-eye-clearance
python check_eye_insertion.py
```

独立验证需要 numpy、trimesh、manifold3d；眼孔对比还需要 scipy、Pillow 和旧版文件夹。原 PMX 路径用于来源及保护区核查，移动到其他电脑时须更新 parameters.json。

## 尺寸、装配与验证范围

本版指定截面外周长复测 **189.468 mm**。主体与后盖的闭合、连通、孔洞拓扑、分件和球眼容纳检查通过；完整结果与限制见对应 JSON 报告。

头围目标约 190 mm、16 mm 球眼，目标娃体为 UFdoll 四分囡囡体。颈围 66 mm 的参考沿用 [DOLK 商品表格](https://dolk.jp/portal/itemDetail/?ItmID=215136)，不是用户实物测量。23 mm 球面颈座、7 × 14 mm 拉筋槽属于打样设计，未取得原厂接口尺寸。四颗磁铁规格为 4 × 2 mm，孔径 4.25 mm、孔深 2.2 mm；定位柱 Ø4 mm、盲孔 Ø4.5 mm。

后盖向后略向上取下。眼珠先经后开口中央进入，再转向眼窝，用眼泥固定；直接从外部斜插可能碰壁。实际眼柄、凸虹膜、眼泥和操作工具不包含在数字球眼检查中。

检查报告与 STL 的 SHA-256 绑定，包含闭合、单连通、孔洞拓扑、分件碰撞、后盖取出、头围与球眼安装。倾斜接缝的浮点接触片单独报告；头围的二维截面仅以 0.00001 mm 精度容差闭合接触微隙，未修改 STL。壁厚法线抽样不等于严格最小壁厚证明。

**仍为打样版，尚未实物打印、接娃体、装眼或进行受力试验。** 打印收缩、颈球配合、磁铁胶层、树脂强度和支撑效果须实物确认。

## 来源

外脸基于本机已有的官方公开三月七 1.0 PMX；后脑及装配结构另建。模型版权 miHoYo，编辑神帝宇。原使用说明见 `source-usage-rules.txt`，注明允许改造、非商业和勿二次配布；本次仅本地保存，未上传发布。`design-reference-notes.md` 保留 v0.2 后脑开盖的实物参考记录。
