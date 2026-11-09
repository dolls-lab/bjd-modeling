# 球面眼预览组件

在 Blender 中导入 `build_hemisphere_eyes.py` 并调用：

```python
objects, report = build_eyes(collection)
```

返回两个真正的开背半球杯：外半径 8 mm、内半径 7.4 mm、名义杯壁 0.6 mm，前方为 −Y。杯口只有环形边缘，没有遮住背部空腔的平圆盘。中心沿用 v14 已有 16 mm 眼座：X=±13.663962920147602、Y=−13.289332231246028、Z=27.67311677124019 mm。

原三月七虹膜、瞳孔和白色高光仅用于离线颜色烘焙，保存为两张 PNG。实际场景只有球面上的贴图，不创建或显示原游戏眼白、虹膜、阴影平片。球面外侧是普通 Principled 光泽材质，默认 emission=0；内面白色。函数自动将 PNG 打包到 Blender 图像数据。

原始虹膜正面投影尺寸、位置和颜色被保留；斜视时随真实球面自然缩短。此材质不复刻官方游戏着色器。

`hemisphere-eye-geometry.npz` 是组件几何；`eye-assets-report.json` 记录源哈希和烘焙参数；`hemisphere-eye-fit-review.json` 检查与实际 v14 壳体的交集及眼洞前视覆盖。

本组件仅供妆面/相似度预览，不属于头壳 STL，不是经过制作验证的实体眼珠设计。所有 v14 头壳和头盖保持原样。
