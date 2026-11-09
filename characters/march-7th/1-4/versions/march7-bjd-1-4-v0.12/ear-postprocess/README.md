# v12 耳背打印表面修顺记录

本步骤在 v12 空心化、体素重建和开孔完成后，只修整实际打印对象 `PRINT_01_Head_Shell` 的耳背、附着沟和窄轮缘。母面仍是空心化前的参考，不包含这次打印表面微修。后盖与其他对象均不修改。

保留自然的耳根窄凹，减轻原有中下段串状波纹和上端小针状高光；不宣称微观完全平整。耳甲、耳垂和支撑范围以外的耳前表面保持。本次允许窄轮缘微修，不能将全部耳点描述为零位移。

- 连续局部支撑最终有 8,860 个可动点；拓扑不变。
- 求解位移最大 0.221969 mm；窄轮缘 2,984 点中最大 0.156405 mm。
- 支撑以外点精确不动。局部检查新增非相邻自交 0、疑似接触 0、三角法线翻转 0。
- 同基线方向的局部对壁射线采样：修后有效 8,118 个，采样最小值 1.168878 mm；没有新增低于 0.4 mm 的成对样本。自然薄缘或复杂沟内有射线未命中，这不是全头最小壁厚证明。少数射线切换到不同对壁，不能把最大射程减少解释为同位置真实壁厚减少。

`ear-before-*` 与 `ear-after-*` 为相同灯光、相同相机的实际几何渲染，未经图像修改。最终保存后的实际浮点位移和模型 SHA 见 `ear-finish-provenance.json`；全模型独立审查由本版其他审核报告负责。

## 数组与复验

`print-protection.npz` 是完整实际打印基线坐标、三角索引与初始权重。`print-solution.npz` 含 `before`、`after`、`triangles`、`free`、`locked`、`weights`、`region_class`、`rim_weight`；不需读取临时目录即可核对范围、精确锁定及位移。`semantic-ear-protection.npz` 保存母面上的上游语义选区；打印选区通过最近母面距离不超过 0.65 mm 映射，避免释放深层内壁。可动区再以沿实际网格的 0.25 mm C2 带收尾。

在副本目录中运行，避免覆盖这份获选结果：

```sh
python3 solve_print_fairing.py /absolute/path/to/review-copy
python3 check_print_local_intersections.py /absolute/path/to/review-copy
blender -b --python check_print_thickness.py -- /absolute/path/to/review-copy
```

Python 求解依赖 NumPy 和 SciPy；厚度核查需 Blender Python。求解采用三维余切最小弯曲能量、位置先验和少量退化窄三角的投影面积约束，没有位移硬裁。窄轮缘位置先验最高为主体的 8 倍，阈值为 0.17 mm，整体阈值为 0.30 mm；获选 alpha 为 30。

要重新将获选数组应用到模型，先通过本版 `build_head.py` 得到相同的未修耳打印基线，再在本版根目录用 Blender 执行 `apply_ear_finish.py`。脚本严格核对坐标和拓扑后只写可动点，导出头壳并保存 Blend，更新 `build-report.json` 和本目录出处记录。如果基线不完全相同会停止，不做猜测映射。`baseline_blend` 中的临时目录只记录当时出处，不是求解或数组复验的依赖；临时基线模型未收入交付包。
