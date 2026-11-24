# 删除早期版本后保留的 v12 构建输入

四分 v1–v11 版本目录已按用户要求删除。本目录仅保留 v12 历史曲面求解用到的两个数值文件，共约 10.6 MiB；没有另行复制旧版 Blender、STL、ZIP 或截图。

| 历史输入（相对四分 versions） | 当前文件 |
| --- | --- |
| `march7-bjd-1-4-v0.10/mother-surface.npz` | [v10-mother-surface.npz](v10-mother-surface.npz) |
| `march7-bjd-1-4-v0.11/mother-surface.npz` | [v11-mother-surface.npz](v11-mother-surface.npz) |

以下旧输入已有相同字节副本，无需重复保存：

- v3/v5 的 `parse_pmx.py` → `1-4/versions/march7-bjd-1-4-v0.14/parse_pmx.py`。
- v8 的 `triangle_intersection_helpers.py` → `1-4/versions/march7-bjd-1-4-v0.14/triangle_intersection_helpers.py`。
- v11 的 `v11-forehead-protection.npz` → `1-4/versions/march7-bjd-1-4-v0.12/source-feature-reference.npz`。

上面的目标路径相对 `characters/march-7th/`。保留版本的历史脚本原字节不动；如需重跑，请在临时工作副本中按上述映射改输入路径，输出新目录。早期脚本另有历史绝对路径和临时输入，本清理不声称已验证全链路可从零重建。

v12 内原有的 `baseline-v0.11.blend` 属于保留版本的构建输入，未修改或搬动。已保存的 v12 及之后模型、妆面、三分和特六模型均保持原字节，可按原方式打开。

旧版对照模型已删除，依赖它们的历史对比脚本不能再原路径重跑；既有截图仍作为历史记录保留。文件 SHA 和完整删除列表见仓库 `docs/retired-versions-2026-11-11.json`。
