# BJD 建模工作区

按**角色 → 尺寸 → 版本**管理 BJD 头壳、妆面预览、建模脚本和验证记录。目前包含三月七四分 v0.1–v0.14 完整系列，以及以 v14 为基础制作的三分版。

## 三月七入口

| 尺寸／用途 | 文件 |
| --- | --- |
| 四分已确认素头 v14 | [Blender 模型](characters/march-7th/1-4/versions/march7-bjd-1-4-v0.14/march7-bjd-head-v0.14-draft.blend) |
| 四分浅肤色、局部妆面、半球眼杯及原发型预览 | [妆面 v5 Blender 模型](characters/march-7th/1-4/versions/march7-bjd-1-4-v0.14-makeup/v5-fair-skin/march7-v14-fair-skin-original-hair.blend) |
| 四分打印导出件 | [主头壳 STL](characters/march-7th/1-4/versions/march7-bjd-1-4-v0.14/march7-head-shell-v0.14-draft.stl) · [后盖 STL](characters/march-7th/1-4/versions/march7-bjd-1-4-v0.14/march7-head-cap-v0.14-draft.stl) |
| 四分肤色和原模型对照 | [正面、斜侧近景](characters/march-7th/1-4/versions/march7-bjd-1-4-v0.14-makeup/v5-fair-skin/skin-tone-comparison.png) |
| 三分 v1 | [版本说明与模型入口](characters/march-7th/1-3/versions/v1/README.md) |

角色总览见 [三月七目录](characters/march-7th/README.md)。四分与三分是独立版本文件；三分的尺寸、颈部接口、验证结果及实物适配状态以该版本说明为准。

用 Blender 的「文件 → 打开」选择 `.blend`。四分妆面 v5 的 5 张贴图已经打包，可独立打开；隐藏 `04_Original_March7_Hair_PREVIEW_ONLY` 集合可查看无发型头壳。眼杯和发型用于外观预览，四分实体结构和验证记录见 [v14 说明](characters/march-7th/1-4/versions/march7-bjd-1-4-v0.14/README.md)。

## 目录约定

```text
characters/
  <character-id>/              每个角色独立归档
    README.md                  角色、尺寸与当前版本入口
    references/local/          该角色的本地源模型与参考资料
    1-4/versions/<version>/     四分版本
    1-3/versions/<version>/     三分版本
docs/                          仓库级迁移与布局记录
tools/                         仓库级校验工具
```

增加其他角色时新建独立 `<character-id>`，不混用三月七目录。每个尺寸的版本独立保存模型、参数、脚本、截图、说明和验证结果；保留此前已确认的模型。目录中的分数是尺寸分类，实际毫米尺寸和娃体接口以版本参数为准。

三月七四分旧版的 16 个目录完整保留在 `characters/march-7th/1-4/versions/`，其原文件名与内部关系不变。重复交付 ZIP、缓存和备份仍保留在磁盘，按 `.gitignore` 排除；模型、脚本和核验记录继续由 Git 管理。

## 来源、同步与校验

当前仓库已配置 `origin`：`https://github.com/dolls-lab/bjd-modeling.git`。本次尺寸制作和目录整理仅修改本地，不改动远端配置，也不自动提交或推送。

本仓库包含原角色模型、贴图及衍生文件，原使用说明有“请勿二次配布”和“请勿用于商业用途”；见 [原使用说明](characters/march-7th/1-4/versions/march7-bjd-1-4-v0.14/source-usage-rules.txt)。目录整理不改变来源限制，后续发布范围按用户指示及素材说明处理。

历史迁入记录见 [原迁移说明](docs/migration.md)，本次按角色与尺寸整理见 [目录重整说明](docs/layout-reorganization.md)。执行 `python3 tools/verify_migration.py` 可按新路径复核原迁移文件的字节数与 SHA-256；该操作不会重新建模、渲染或覆盖模型。
