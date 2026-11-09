# v13 局部皮肤修顺记录

以已交付 v12 的实际打印头为唯一几何基线，在双侧眼外角外围、太阳穴、耳前和耳上根连接皮肤上减轻短沟与局部褶痕。只移动实际打印网格顶点，不重建母面，不重新体素化、挖空或切盖。耳上根的自然凹和眼角自身的自然折线仍保留。

本次 17,623 个皮肤点发生微移，实际保存最大位移 0.320165 mm。全头 XYZ 尺寸完全相同；对 1,368 个球面方向的凸包支撑测量，最大变化 0.242767 mm，因此不宣称每一条局部投影轮廓逐像素相同。最终多视角外轮廓由本版独立审核另外核查。

眼缘保护圈、耳廓和 v12 耳背已修点、内壁、主五官保护点、局部支撑以外顶点均保持基线坐标。所有其他网格对象不动，后盖 STL 字节相同。母面为继承的空心化前参考；最终可编辑和打印表面是 `PRINT_01_Head_Shell`。

局部检查中新增非相邻自交为 0、疑似接触为 0、三角法线翻转为 0。局部对壁射线采样共 17,623 个有效点，修前最小 0.706197 mm，修后最小 0.725134 mm，没有新增低于 0.4 mm 的成对样本。这是局部回归筛查，不是全模型最低壁厚证明。

## 文件与复验

- `print-protection.npz`：完整实际打印基线坐标/三角索引、初始皮肤权重与保护标记。
- `print-solution.npz`：`before`、`after`、`triangles`、`free`、`locked`、`weights`、`outer_skin_support`、`inner_wall_locked`、`major_features_locked`、`ear_locked`、`eye_guard` 等。锁定标记可包括支撑外的保守区域；内壁之外也有大量固定外表面。
- `print-solution-report.json`：求解位移、全向支撑变化及保护结果。
- `print-local-intersections.json` 和 `print-local-thickness.json`：绑定获选数组 SHA 的局部检查。
- `surface-finish-provenance.json`：最终实际模型 SHA、浮点写入位移和其他对象不变的记录。
- `temple-after-*.png`：获选数组在基线场景中同相机同灯光的真实几何近景。最终保存模型的对照渲染见上级 `comparison-renders`。

选择外表面时使用 v12 母面最近距离 ≤0.65 mm，并排除语义耳廓、已有耳背修整和真实眼边 1 mm 保护圈；外围采用连续空间权重及实际网格边界的 0.7 mm C2 过渡。求解为位置先验约束下的局部三维余切最小弯曲能量。获选 alpha 0.1，未用位移硬裁，也未改变拓扑。

在副本目录复算，以免覆盖获选记录：

```sh
python3 solve.py /absolute/path/to/review-copy
python3 check_print_local_intersections.py /absolute/path/to/review-copy
blender -b --python check_print_thickness.py -- /absolute/path/to/review-copy
```

求解需要 NumPy 和 SciPy；壁厚检查需要 Blender Python。输入坐标和选区均随 NPZ 保存，无需临时目录。求解会生成新的结果文件，压缩容器 SHA 可能因写入时间不同而变化，应比较数组与实际几何。

在本版根目录运行 `apply_surface_finish.py` 可从原 v12 Blend 重现最终 v13：它先严格核对基线哈希、坐标和拓扑，缓存数组后只写可动点，再另存 v13、导出头壳并复制原后盖。v12 保持只读，版本元数据更新为 v0.13。此操作需要同目录的完整 v12 基线；单独复验 NPZ 与局部求解不需要该 Blend。
