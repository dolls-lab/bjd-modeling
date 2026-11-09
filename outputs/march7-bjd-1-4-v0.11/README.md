# 三月七四分 BJD 头壳 v0.11 · 额头过渡细修

本版以 v10 为基础，参考 v8 中部额面的缓坡，调整眉上到额头的过渡。保留 v10 已降低的头顶高度、圆润侧脑和后脑，避免重新引入 v8 眉眼两侧的宽平板与方形俯视轮廓。所有旧版文件均保留原样。

## 本轮实际变化

先将 v8 的中央额头截线按 v10 同样的顶部降高对齐，仅采用中间两条截线作为参考。随后在 v10 完整母面上调整前后方向，X/Z 坐标保持不变。额头中上部最大修正约 1.729 mm，母面最高点仍为 Z=69.792 mm。

为了让眉上过渡更宽缓，释放了旧保护区中 651 个不含五官特征的额头点，其最大变化约 0.090 mm。眼孔、眼睑及闭合补片、鼻唇、主要面颊、下巴和全部耳部仍受保护：19,797 个核心面雕点及 1,834 个耳部点在母面阶段保持原位。

外围 |X|≥20 mm 的前后方向变化最多约 0.050 mm；|X|≥24 mm、后部 Y≥−2 mm 及顶部 Z≥64 mm 保持不变。以此限制对两侧头型的影响。新空心壳与安装结构由这张母面重新生成，最终打印表面仍需与 v10 独立比对，不能将母面固定等同于最终打印件逐点一致。

## 查看与使用

- `march7-bjd-head-v0.11-draft.blend`：当前 Blender 工程。
- `march7-head-shell-v0.11-draft.stl`、`march7-head-cap-v0.11-draft.stl`：配套主头壳与后盖，坐标单位为毫米。
- `forehead-transition-comparison.png`：v10 / v11 前斜侧及俯视。
- `front-side-comparison.png`：v10 / v11 正面及侧面。
- `v8-reference-comparison.png`：v8、v10、v11 三版参考对比。
- `comparison-renders/`：同尺度、同相机、同灯光的实际打印零件渲染，未做图像修形。

Blender 中两个 `PRINT_` 对象是当前交付零件，隐藏的 `EDITABLE_Outer_Surface_Before_Hollowing` 是本轮实际母面。请使用同包的头壳与后盖。

## 数字检查说明

`candidate-profile-review.json/png` 记录额头截线变化：主要眉上过渡区的局部曲率峰值下降，两侧未出现更强的曲率峰。上方收尾带仍存在很浅的曲率反转，不能称整个额头处处严格凸；侧面与俯视检查未见新的尖锐台阶。

`mother-intersection-check.json` 检查完整母面的非邻接三角自交。实际 STL 的闭合网格、装配与后盖拆卸、眼珠路径、自交、壁厚采样和源面保护分别见 `validation.json`、`eye-insertion-check.json`、`print-intersection-check.json`、`side-shell-review.json`、`source-surface-review.json`；汇总见 `local-quality-review.json`。报告保留各自方法、哈希与检测限制，壁厚采样不等于全表面最小厚度证明。

本版上述数字检查通过。实际打印件五官和耳部相对 v10 的采样表面偏差均小于 0.001 mm，允许调整的眉上区域最大约 0.099 mm。眼洞在 0.05 mm 网格上与 v10 逐像素一致，16 mm 装眼连续路径通过。按原同一测量高度，压合后头围约 180.581 mm（18.06 cm）。Blender 工程与两份 STL 的三角几何一致。

沿用 16 mm 眼珠、2.6 mm 普通壳厚和原颈部打样设计；尚未实物打印或与 UFdoll 囡囡体试装。尺寸与接口假设见 `parameters.json`。

源角色模型使用约束见 `source-usage-rules.txt`；包内不含原角色 PMX。脚本保留本机源模型与历史依赖路径，作为过程记录。`checksums.json` 可核对交付包内文件。
