# 三月七四分 BJD 头壳 v0.10 · 降低额头顶部

本版在 v9 圆润头型上，将最高点降低约 **3 mm**。从 Z=40 mm 起逐渐增加下移量，母面最高点由 72.792 mm 降至 69.792 mm；保留头顶到后脑的连续圆弧。v9 原文件保留不变。

变形只作用于上额头和头顶。母面五官核心最高 Z=38.962 mm，耳朵最高 Z=31.565 mm，均在不变区域内。X/Y 坐标不变；竖直变形在两端连续到二阶导数，避免生硬压平头顶或产生新的过渡折线。随后重新生成 2.6 mm 空心壳、后盖和圆形安装孔。

## 文件

- `march7-bjd-head-v0.10-draft.blend`：Blender 工程。
- `march7-head-shell-v0.10-draft.stl`：主头壳。
- `march7-head-cap-v0.10-draft.stl`：本版配套后盖，请与主壳成套使用。
- `forehead-height-comparison.png`：左 v9、右 v10，正面与侧面同角度、同尺度渲染。
- `comparison-renders/`：正面、侧面、前斜侧原始渲染。

STL 坐标单位为毫米。Blender 的两个 `PRINT_` 对象是交付零件，隐藏的 `EDITABLE_Outer_Surface_Before_Hollowing` 保存了本次降低后的母面。旧母面和基线工程仅保留在本机工作目录，不打入交付包。

## 检查与使用范围

`mother-surface-report.json` 记录精确改动、母面核心保持情况和变形映射；它不代表最终重网格后的打印件逐点一致。实际模型的表面比对、Blend/STL 一致性、网格闭合、装配和后盖拆卸、16 mm 装眼路径、自交与壁厚采样分别保留在包内 JSON 报告中。

本版沿用 v9 的 16 mm 眼珠设计、颈部打样结构和后开盖方式。颈围 66 mm 是 UFdoll 囡囡体的参考值，球窝和安装间隙仍是打样设计参数，尚未实物打印或与娃体试装。

模型来源及使用约束见 `source-usage-rules.txt`。交付包不含原角色 PMX。脚本保留本机源模型及历史依赖路径，作为建模过程记录；`checksums.json` 用于核对包内文件。
