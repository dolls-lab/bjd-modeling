# 三月七 v14 局部妆面预览 v3：原角色浅肤色

使用 Blender 打开 `march7-v14-local-makeup-v3-skin.blend`，选择「材质预览」或「渲染」查看。

本版在 v2 局部妆面模型上，只把头壳和后盖的统一材质底色调为原三月七脸部贴图的浅肤色。取样来自无妆额头区域，中位色为 sRGB **#F2D5CA**。材质输入已正确转换为线性 RGB；原角色脸材质的 diffuse 乘色为白色。

眉眼、嘴线仍是直接贴在原头壳上的局部妆面，没有增加整脸覆盖层。四个网格（主壳、后盖、两个预览眼杯）、UV、所有打包贴图及灯光保持 v2 原样；v14 素头和 v2 文件均未覆盖。眼杯继续只作观感模拟，打印件仍使用原 v14 主壳和后盖 STL。

`skin-before-after.png` 是同相机、同灯光的前后对比；`skin-multiview.png` 是新版四个角度。图片直接从模型渲染，仅缩放排版。

`skin-color-reference.json` 记录原图取样与色彩空间换算；`skin-change-report.json` 记录保存并重新打开后的网格、UV、贴图及灯光核对结果。`apply_march7_skin.py` 可从相邻 v2 模型复现修改和渲染。
