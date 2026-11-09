# v6 侧面截图

本文件夹只新增同一 v6 娃头的真实 Blender 几何渲染截图，未修改 v6 Blender、STL 或尺寸。

- all-side-views.png：六视图，上排左侧、下排右侧；每排依次为前斜、正侧、后斜。
- ear-closeups.png：四张耳部近景，上排左耳、下排右耳；每排依次为前侧、后侧。
- 十张 v6-*.png：各方向独立原图，均为 1200×1200。
- march7-v6-side-views.zip：独立原图、两张拼图、本说明及校验文件。

拼图只做等比例缩放、排版和中文标注，不裁切、不镜像、不修形，也没有 AI 补画。近景与全头视图的画幅不同，不应跨图直接测量尺寸。

side-view-checksums.json 和 SHA256SUMS.txt 记录包内文件校验值；ZIP 的校验值另存于 march7-v6-side-views.zip.sha256。JSON 还记录组图前后保持不变的 v6 模型文件 SHA256。模型文件本身不放入截图 ZIP。

待全部十张原图渲染完成后，可用 `python3 assemble_sides.py` 重新生成拼图与截图包；需要 Pillow 和中文字体。脚本不会写入父目录的模型或原 manifest。
