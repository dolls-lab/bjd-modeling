# BJD 建模工作区

三月七四分 BJD 头壳的独立建模仓库，包含 v0.1–v0.14、原角色核对、妆面、浅肤色及原发型预览。2026-11-09 从 `hksr_database/outputs/` 完整迁入，保留原版本目录结构。

**目前仅在本地使用和提交，未创建 GitHub 仓库，也未配置远端。** 本仓库包含原角色模型、贴图以及衍生文件，来源说明有“请勿二次配布”和“请勿用于商业用途”；详情见 [原使用说明](outputs/march7-bjd-1-4-v0.14/source-usage-rules.txt)。

## 最新已确认版本

| 用途 | 文件 |
| --- | --- |
| 浅肤色、局部妆面、半球眼杯、原发型预览 | [打开 v5 Blender 文件](outputs/march7-bjd-1-4-v0.14-makeup/v5-fair-skin/march7-v14-fair-skin-original-hair.blend) |
| 素头壳与可拆后盖 | [打开 v14 Blender 文件](outputs/march7-bjd-1-4-v0.14/march7-bjd-head-v0.14-draft.blend) |
| 头壳 STL | [主壳](outputs/march7-bjd-1-4-v0.14/march7-head-shell-v0.14-draft.stl) |
| 后盖 STL | [可拆后盖](outputs/march7-bjd-1-4-v0.14/march7-head-cap-v0.14-draft.stl) |
| 肤色与原模型对照 | [正面、斜侧近景](outputs/march7-bjd-1-4-v0.14-makeup/v5-fair-skin/skin-tone-comparison.png) |

用 Blender 的「文件 → 打开」选择 `.blend`。最新妆面模型的 5 张贴图已经打包，可独立打开；隐藏 `04_Original_March7_Hair_PREVIEW_ONLY` 集合即可查看无发型头壳。眼杯和发型用于外观预览，实体头壳的结构与验证记录见 [v14 说明](outputs/march7-bjd-1-4-v0.14/README.md)。

## 文件组织

- `outputs/march7-bjd-1-4/`：v0.1。
- `outputs/march7-bjd-1-4-v0.2/` 至 `v0.14/`：完整头壳系列。
- `outputs/march7-bjd-1-4-v0.13-original-review/`：原角色对照与核对。
- `outputs/march7-bjd-1-4-v0.14-makeup/`：最初妆面及 v2–v5 预览。
- `references/local/official-models/`：独立复制的原始 PMX、贴图、来源及使用规则，原娃衣项目的共享素材仍在原处。
- `docs/`：迁移清单、逐文件校验结果与路径说明。

模型、脚本、截图、核验报告与本地参考素材纳入本地版本管理。重复交付 ZIP、缓存和备份仍保存在磁盘，按 `.gitignore` 排除。无需 Git LFS 即可使用本地仓库。

迁移范围和旧脚本注意事项见 [迁移说明](docs/migration.md)。执行 `python3 tools/verify_migration.py` 可复核迁移文件哈希；这不会重新建模、渲染或覆盖模型。
